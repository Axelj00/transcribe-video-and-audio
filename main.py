#!/usr/bin/env python3
"""
Audio/Video Transcription Script
Transcribes audio and video files from the input/ folder using OpenAI's Whisper API
and saves the results to the results/ folder.
"""

import os
import time
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import subprocess
import tempfile

def log(message):
    """Print message with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

# Load environment variables
print("Loading environment variables from .env file...", flush=True)
load_dotenv()

# Check if API key is present
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"API key loaded successfully (length: {len(api_key)} characters)", flush=True)
else:
    print("WARNING: No API key found!", flush=True)

# Initialize OpenAI client
print("Initializing OpenAI client...", flush=True)
client = OpenAI(api_key=api_key)
print("OpenAI client ready!", flush=True)

# Folder paths
INPUT_FOLDER = Path("input")
RESULTS_FOLDER = Path("results")

# Supported file formats (as per OpenAI Whisper API documentation)
SUPPORTED_FORMATS = [".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"]

# Ensure folders exist
INPUT_FOLDER.mkdir(exist_ok=True)
RESULTS_FOLDER.mkdir(exist_ok=True)


def get_audio_video_files():
    """Get all supported audio/video files from the input folder."""
    log(f"Scanning '{INPUT_FOLDER}' folder for media files...")
    files = []
    for ext in SUPPORTED_FORMATS:
        found = list(INPUT_FOLDER.glob(f"*{ext}"))
        if found:
            log(f"  Found {len(found)} {ext} file(s)")
        files.extend(found)
    log(f"Total files found: {len(files)}")
    return sorted(files)  # Sort for consistent processing order


def get_file_size(file_path):
    """Get file size in MB."""
    size_bytes = file_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    return size_mb

def is_video_file(file_path):
    """Check if file is a video format."""
    video_extensions = [".mp4", ".mpeg", ".webm"]
    return file_path.suffix.lower() in video_extensions

def get_audio_duration(file_path):
    """Get duration of audio/video file in seconds using ffprobe."""
    try:
        result = subprocess.run([
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(file_path)
        ], capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except:
        return None

def extract_audio_from_video(video_path):
    """
    Extract audio from video file using ffmpeg.
    Returns path to temporary audio file.
    """
    log(f"  This is a video file, extracting audio track...")
    
    # Create temporary file for audio
    temp_audio = tempfile.NamedTemporaryFile(suffix=".m4a", delete=False)
    temp_audio_path = temp_audio.name
    temp_audio.close()
    
    try:
        # Use ffmpeg to extract audio
        log(f"  Running ffmpeg to extract audio...")
        log(f"  This will take 1-3 minutes for large videos, please wait...")
        extract_start = time.time()
        
        # Run ffmpeg with progress output visible
        result = subprocess.run([
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'aac',  # AAC codec
            '-b:a', '128k',  # 128kbps bitrate
            '-y',  # Overwrite output file
            '-progress', 'pipe:1',  # Show progress to stdout
            '-loglevel', 'warning',  # Only show warnings/errors
            temp_audio_path
        ], text=True, check=True)
        
        extract_time = time.time() - extract_start
        audio_size = get_file_size(Path(temp_audio_path))
        
        log(f"  Audio extracted successfully in {extract_time:.1f} seconds")
        log(f"  Audio file size: {audio_size:.2f} MB")
        
        return temp_audio_path
        
    except subprocess.CalledProcessError as e:
        log(f"  ERROR: ffmpeg failed!")
        if hasattr(e, 'stderr') and e.stderr:
            log(f"  Error output: {e.stderr}")
        raise Exception(f"Failed to extract audio from video")
    except FileNotFoundError:
        raise Exception("ffmpeg not found. Please install ffmpeg: brew install ffmpeg")

def split_audio_file(audio_path, max_size_mb=20):
    """
    Split audio file into chunks if it's larger than max_size_mb.
    Returns list of chunk file paths.
    """
    file_size = get_file_size(Path(audio_path))
    
    if file_size <= max_size_mb:
        log(f"  Audio file is {file_size:.2f} MB (under {max_size_mb}MB limit), no splitting needed")
        return [audio_path]
    
    log(f"  Audio file is {file_size:.2f} MB (over {max_size_mb}MB limit)")
    log(f"  Splitting audio into chunks...")
    
    # Get duration of audio
    duration = get_audio_duration(audio_path)
    if not duration:
        log(f"  WARNING: Could not determine duration, sending as-is")
        return [audio_path]
    
    log(f"  Audio duration: {format_time(duration)}")
    
    # Calculate chunk duration based on file size
    # If 50MB file needs to be split to 20MB chunks, we need 3 chunks
    num_chunks = int(file_size / max_size_mb) + 1
    chunk_duration = duration / num_chunks
    
    log(f"  Splitting into {num_chunks} chunks of ~{format_time(chunk_duration)} each")
    
    chunks = []
    for i in range(num_chunks):
        start_time = i * chunk_duration
        
        # Create temp file for chunk
        temp_chunk = tempfile.NamedTemporaryFile(suffix=f"_chunk{i+1}.m4a", delete=False)
        chunk_path = temp_chunk.name
        temp_chunk.close()
        
        log(f"  Creating chunk {i+1}/{num_chunks}...")
        
        # Extract chunk using ffmpeg
        result = subprocess.run([
            'ffmpeg',
            '-i', str(audio_path),
            '-ss', str(start_time),
            '-t', str(chunk_duration),
            '-acodec', 'copy',  # Copy without re-encoding (faster)
            '-y',
            chunk_path
        ], capture_output=True, text=True, check=True)
        
        chunk_size = get_file_size(Path(chunk_path))
        log(f"  Chunk {i+1} created: {chunk_size:.2f} MB")
        chunks.append(chunk_path)
    
    log(f"  Successfully split into {len(chunks)} chunks")
    return chunks

def transcribe_audio_chunk(chunk_path, chunk_num, total_chunks):
    """Transcribe a single audio chunk."""
    log(f"    Transcribing chunk {chunk_num}/{total_chunks}...")
    
    chunk_size = get_file_size(Path(chunk_path))
    log(f"    Chunk size: {chunk_size:.2f} MB")
    
    with open(chunk_path, "rb") as audio_file:
        log(f"    Sending chunk to OpenAI Whisper API...")
        
        api_start = time.time()
        transcription = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=audio_file,
            response_format="text"
        )
        api_time = time.time() - api_start
        
        log(f"    Chunk {chunk_num} transcribed in {api_time:.1f} seconds ({len(transcription)} characters)")
    
    return transcription

def transcribe_file(file_path):
    """
    Transcribe a single audio/video file using OpenAI's Whisper API.
    
    Args:
        file_path: Path to the audio/video file
        
    Returns:
        Transcription text
    """
    original_size = get_file_size(file_path)
    log(f"  Original file size: {original_size:.2f} MB")
    
    # Check if we need to extract audio from video
    temp_files = []
    audio_file = None
    
    try:
        if is_video_file(file_path):
            try:
                audio_file = extract_audio_from_video(file_path)
                temp_files.append(audio_file)
            except Exception as e:
                log(f"  Failed to extract audio: {str(e)}")
                log(f"  Will try using original file...")
                audio_file = str(file_path)
        else:
            log(f"  This is an audio file, using directly")
            audio_file = str(file_path)
        
        # Split audio if needed
        log(f"  Checking if audio needs to be split...")
        chunks = split_audio_file(audio_file, max_size_mb=20)
        
        # Add chunks to temp files (except if it's the original file)
        if len(chunks) > 1:
            temp_files.extend(chunks)
        elif chunks[0] != str(file_path):
            # Single chunk but it's a temp file
            if chunks[0] not in temp_files:
                temp_files.append(chunks[0])
        
        # Transcribe chunks
        if len(chunks) == 1:
            log(f"  Transcribing audio file...")
            transcription = transcribe_audio_chunk(chunks[0], 1, 1)
        else:
            log(f"  Transcribing {len(chunks)} chunks...")
            transcriptions = []
            
            for i, chunk in enumerate(chunks, 1):
                chunk_transcription = transcribe_audio_chunk(chunk, i, len(chunks))
                transcriptions.append(chunk_transcription)
            
            # Merge transcriptions
            log(f"  Merging {len(transcriptions)} transcriptions...")
            transcription = " ".join(transcriptions)
            log(f"  Final merged transcription: {len(transcription)} characters")
        
        return transcription
    
    finally:
        # Clean up all temporary files
        if temp_files:
            log(f"  Cleaning up {len(temp_files)} temporary file(s)...")
            for temp_file in temp_files:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except:
                        pass


def save_transcription(file_path, transcription_text):
    """
    Save transcription to a text file in the results folder.
    
    Args:
        file_path: Original audio/video file path
        transcription_text: The transcribed text
    """
    # Create output filename (replace extension with .txt)
    output_filename = file_path.stem + ".txt"
    output_path = RESULTS_FOLDER / output_filename
    
    log(f"  Writing transcription to: {output_path}")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcription_text)
    
    log(f"  Successfully saved!")


def format_time(seconds):
    """Format seconds into a readable time string (HH:MM:SS or MM:SS)."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"


def main():
    """Main transcription loop."""
    log("=" * 70)
    log("Audio/Video Transcription Tool - Starting...")
    log("=" * 70)
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        log("\nERROR: OPENAI_API_KEY not found in .env file")
        log("Please create a .env file with your OpenAI API key.")
        return
    
    log("API key verified")
    
    # Get all audio/video files
    media_files = get_audio_video_files()
    
    if not media_files:
        log(f"\nNo supported audio/video files found in '{INPUT_FOLDER}' folder.")
        log(f"Supported formats: {', '.join(SUPPORTED_FORMATS)}")
        log("Please add some media files and run again.")
        return
    
    total_files = len(media_files)
    log(f"\n{total_files} file(s) ready for transcription")
    log(f"Supported formats: {', '.join(SUPPORTED_FORMATS)}")
    
    # List all files
    log("\nFiles to process:")
    for i, f in enumerate(media_files, 1):
        size_mb = get_file_size(f)
        log(f"  {i}. {f.name} ({size_mb:.2f} MB)")
    
    log("-" * 70)
    
    # Track timing
    start_time = time.time()
    processing_times = []
    
    # Process each file
    for index, file_path in enumerate(media_files, 1):
        file_start_time = time.time()
        
        log(f"\n{'='*70}")
        log(f"[{index}/{total_files}] Starting transcription: {file_path.name}")
        log(f"{'='*70}")
        
        try:
            # Transcribe the file
            transcription = transcribe_file(file_path)
            
            # Save the result
            save_transcription(file_path, transcription)
            
            # Calculate timing
            file_time = time.time() - file_start_time
            processing_times.append(file_time)
            
            # Calculate statistics
            avg_time = sum(processing_times) / len(processing_times)
            remaining_files = total_files - index
            estimated_remaining = avg_time * remaining_files
            progress_pct = (index / total_files) * 100
            
            # Display timing information
            log(f"\n--- File Completed ---")
            log(f"  Time taken: {format_time(file_time)}")
            log(f"  Overall progress: {progress_pct:.1f}% ({index}/{total_files} files)")
            
            if remaining_files > 0:
                log(f"  Average time per file: {format_time(avg_time)}")
                log(f"  Estimated time remaining: {format_time(estimated_remaining)}")
                log(f"  Files remaining: {remaining_files}")
            
        except Exception as e:
            log(f"\n  ERROR: Failed to transcribe!")
            log(f"  Error message: {str(e)}")
            log(f"  Error type: {type(e).__name__}")
            import traceback
            log(f"  Traceback:\n{traceback.format_exc()}")
            continue
    
    # Summary
    total_time = time.time() - start_time
    successful = len(processing_times)
    
    log("\n" + "=" * 70)
    log("ALL TRANSCRIPTIONS COMPLETE!")
    log("=" * 70)
    log(f"Successfully transcribed: {successful}/{total_files} files")
    log(f"Total time: {format_time(total_time)}")
    if successful > 0:
        log(f"Average time per file: {format_time(total_time / successful)}")
    log(f"Results saved to: {RESULTS_FOLDER}/")
    log("=" * 70)


if __name__ == "__main__":
    main()

