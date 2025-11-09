# Audio/Video Transcription Tool

A Python-based command-line tool that transcribes audio and video files to text using OpenAI's Whisper API. Handles large files automatically by extracting audio from videos and splitting files into manageable chunks.

## Features

- Transcribes both audio and video files to text
- Automatic audio extraction from video files using ffmpeg
- Intelligent file splitting for files larger than 20MB
- Batch processing of multiple files
- Progress tracking with detailed logging
- Automatic cleanup of temporary files
- UTF-8 encoding support for international characters

## Supported Formats

- Audio: `.mp3`, `.m4a`, `.wav`, `.mpga`
- Video: `.mp4`, `.mpeg`, `.webm`

## Requirements

- Python 3.7 or higher
- ffmpeg (for video processing)
- OpenAI API key

## Installation

### 1. Install ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

### 2. Clone the repository

```bash
git clone https://github.com/Axelj00/transcribe-video-and-audio.git
cd transcribe-video-and-audio
```

### 3. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 5. Set up your OpenAI API key

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=your_api_key_here
```

You can get an API key from [platform.openai.com](https://platform.openai.com/api-keys).

## Usage

1. Place your audio or video files in the `input/` folder
2. Run the transcription script:

```bash
python main.py
```

3. Find your transcriptions in the `results/` folder as `.txt` files

The script will automatically:
- Detect all supported media files in the input folder
- Extract audio from video files
- Split large files into chunks
- Transcribe each file using OpenAI's Whisper API
- Save transcriptions with the same filename as the original (with `.txt` extension)

## Example Output

```
======================================================================
Audio/Video Transcription Tool - Starting...
======================================================================
[19:03:40] Scanning 'input' folder for media files...
[19:03:40]   Found 1 .mp4 file(s)
[19:03:40] Total files found: 1
[19:03:40] [1/1] Starting transcription: video.mp4
[19:03:40]   Original file size: 3673.84 MB
[19:03:40]   This is a video file, extracting audio track...
[19:04:04]   Audio extracted successfully in 24.6 seconds
[19:04:04]   Audio file is 74.60 MB (over 20MB limit)
[19:04:04]   Splitting into 4 chunks of ~20m 20s each
[19:07:29]   Successfully saved!
======================================================================
[19:07:29] ALL TRANSCRIPTIONS COMPLETE!
======================================================================
```

## How It Works

1. **File Detection**: Scans the `input/` folder for supported audio/video files
2. **Audio Extraction**: If the file is a video, extracts the audio track using ffmpeg
3. **File Splitting**: If the audio is larger than 20MB, splits it into smaller chunks
4. **Transcription**: Sends each chunk to OpenAI's Whisper API (gpt-4o-transcribe model)
5. **Merging**: Combines transcriptions from multiple chunks if applicable
6. **Output**: Saves the final transcription as a text file in `results/`
7. **Cleanup**: Removes all temporary files

## Cost Considerations

This tool uses OpenAI's Whisper API. Pricing is based on audio duration:
- $0.006 per minute (as of 2024)
- Example: A 1-hour video costs approximately $0.36 to transcribe

Check current pricing at [openai.com/pricing](https://openai.com/pricing).

## Project Structure

```
transcribeFromVideo/
├── main.py              # Main transcription script
├── requirements.txt     # Python dependencies
├── .env                 # API key (not committed to git)
├── .env.example         # Template for .env file
├── .gitignore          # Git ignore rules
├── input/              # Place your media files here
├── results/            # Transcriptions output here
└── README.md           # This file
```

## Troubleshooting

**"ffmpeg not found" error:**
- Make sure ffmpeg is installed and accessible in your PATH
- Test by running `ffmpeg -version` in your terminal

**"No API key found" error:**
- Ensure you've created a `.env` file in the project root
- Verify your API key is correctly formatted in the `.env` file

**Large file processing is slow:**
- This is normal. Large files are split into chunks and processed sequentially
- A 1-hour video typically takes 3-5 minutes to transcribe

**API errors:**
- Check that your OpenAI API key is valid and has sufficient credits
- Verify your internet connection is stable

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Uses OpenAI's Whisper API for transcription
- Uses ffmpeg for audio/video processing
