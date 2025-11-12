# YouTube Downloader & Transcript Extractor

A complete toolkit for downloading YouTube videos, extracting transcripts, and transcribing podcasts - built with Python, yt-dlp, and Whisper AI.

## Features

### 🎥 Video Downloader
- Download YouTube videos in various quality options (best, 1080p, 720p, 480p, 360p)
- Extract audio only as MP3
- Progress tracking with speed and ETA
- Custom output directory

### 📝 Transcript Downloader
- Extract existing YouTube transcripts/captions
- **Automatic fallback to local Whisper** when no transcript is available
- Multiple output formats (text, JSON, WebVTT)
- Multi-language support
- Local transcription using OpenAI Whisper (no API needed!)

### 🎙️ Podcast Transcriber (NEW!)
- Download and transcribe podcasts from Acast
- Automatic audio extraction from podcast URLs
- Local Whisper transcription (works offline)
- Multiple Whisper model sizes (tiny to large)
- Save audio files optionally

All built with modern Python and uv package manager.

## Prerequisites

- Python 3.12
- uv (for package management)

## Installation

The project is already set up with uv. Just activate the environment:

```bash
# Install dependencies (already done)
uv sync
```

## Usage

### Basic Usage

Download a video in best quality:

```bash
uv run youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Or use python directly:

```bash
python youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Download with Specific Quality

```bash
uv run youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -q 720p
```

Available quality options:
- `best` (default) - Best available quality
- `1080p` - Full HD
- `720p` - HD
- `480p` - SD
- `360p` - Low quality

### Download Audio Only (MP3)

```bash
uv run youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -a
```

### Specify Output Directory

```bash
uv run youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -o ~/Videos
```

### All Options

```bash
uv run youtube_downloader.py [-h] [-o OUTPUT] [-q {best,1080p,720p,480p,360p}] [-a] url

Arguments:
  url                   YouTube video URL

Options:
  -h, --help           Show help message
  -o, --output OUTPUT  Output directory (default: downloads)
  -q, --quality        Video quality (default: best)
  -a, --audio-only     Download audio only (MP3 format)
```

## Examples

1. Download best quality video to default downloads folder:
   ```bash
   uv run youtube_downloader.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
   ```

2. Download 720p video to a specific folder:
   ```bash
   uv run youtube_downloader.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -q 720p -o ~/Videos
   ```

3. Download audio only:
   ```bash
   uv run youtube_downloader.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -a
   ```

---

## Transcript Downloader

Extract transcripts from YouTube videos with automatic fallback to local Whisper transcription.

### Basic Transcript Usage

```bash
# Extract existing transcript (auto-fallback to local Whisper if none available)
uv run transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Force audio transcription with local Whisper (skip transcript check)
uv run transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" --audio-only

# Specify output file
uv run transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -o my_transcript.txt

# Specify language (e.g., French)
uv run transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -l fr
```

### Transcript Options

```bash
uv run transcript_downloader.py [-h] [-f {text,json,vtt}] [-o OUTPUT]
                                [-l LANGUAGES] [--audio-only] [--keep-audio]
                                [--use-local-whisper] [--whisper-model MODEL]
                                [--list-transcripts] url

Arguments:
  url                       YouTube video URL

Options:
  -f, --format             Output format: text, json, or vtt (default: text)
  -o, --output             Output file path (default: transcripts/<video_id>.txt)
  -l, --languages          Preferred languages, comma-separated (default: en)
  --audio-only             Skip transcript check, use local Whisper directly
  --use-local-whisper      Force use of local Whisper (default if installed)
  --whisper-model MODEL    Whisper model size: tiny, base, small, medium, large (default: base)
  --keep-audio             Keep downloaded audio file after transcription
  --list-transcripts       List available transcript languages
```

### Transcript Examples

```bash
# Get transcript in French with English fallback
uv run transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -l fr,en

# Export as JSON format
uv run transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -f json

# Export as WebVTT (subtitle format)
uv run transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -f vtt

# Keep audio file after transcription
uv run transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" --keep-audio

# Use larger Whisper model for better accuracy
uv run transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" --whisper-model medium

# List available transcript languages
uv run transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" --list-transcripts
```

### How It Works

1. **Try Existing Transcript**: First attempts to fetch existing YouTube captions/transcripts
2. **Fallback to Local Whisper**: If no transcript exists:
   - Downloads audio from YouTube as MP3
   - Transcribes locally using OpenAI Whisper
   - Returns transcribed text
3. **Cleanup**: Automatically removes temporary audio files (unless `--keep-audio` is specified)

---

## Podcast Transcriber

Download and transcribe podcasts from Acast, Apple Podcasts, and other platforms.

### Basic Podcast Usage

```bash
# Transcribe an Acast podcast episode
uv run podcast_transcriber.py "https://shows.acast.com/SHOW_ID/EPISODE_ID"

# Transcribe an Apple Podcasts episode
uv run podcast_transcriber.py "https://podcasts.apple.com/podcast/NAME/idXXXXXX?i=EPISODE_ID"

# Specify language and model size
uv run podcast_transcriber.py "PODCAST_URL" -l fr --model small

# Keep the audio file after transcription
uv run podcast_transcriber.py "PODCAST_URL" --keep-audio

# Custom output location
uv run podcast_transcriber.py "PODCAST_URL" -o my_podcast_transcript.txt
```

### Podcast Options

```bash
uv run podcast_transcriber.py [-h] [-o OUTPUT] [-l LANGUAGE]
                              [--model {tiny,base,small,medium,large}]
                              [--keep-audio] [--audio-dir DIR] url

Arguments:
  url                      Podcast episode URL (Acast and Apple Podcasts supported)

Options:
  -o, --output            Output transcript file path
  -l, --language          Language code (default: auto-detect)
  --model                 Whisper model size (default: base)
  --keep-audio            Keep downloaded audio file
  --audio-dir             Directory to save audio files
```

### Podcast Examples

```bash
# Transcribe French podcast from Apple Podcasts
uv run podcast_transcriber.py "https://podcasts.apple.com/..." -l fr

# Transcribe Acast podcast with larger model for better accuracy
uv run podcast_transcriber.py "https://shows.acast.com/..." --model medium

# Keep audio and save to specific location
uv run podcast_transcriber.py "PODCAST_URL" \
  --keep-audio --audio-dir ~/Podcasts -o transcript.txt
```

### Whisper Model Sizes

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| tiny | ~39MB | Fastest | Lower | Quick drafts |
| base | ~142MB | Fast | Good | **Default - balanced** |
| small | ~466MB | Medium | Better | More accuracy |
| medium | ~1.5GB | Slow | High | Professional work |
| large | ~2.9GB | Slowest | Best | Maximum accuracy |

### Supported Platforms

- ✅ **Acast** - Full support
- ✅ **Apple Podcasts** - Full support
- 🔜 More platforms coming soon

---

## Project Structure

```
youtube_downloader/
  youtube_downloader.py   # Main downloader script
  pyproject.toml          # Project configuration
  uv.lock                 # Dependency lock file
  README.md               # This file
  downloads/              # Default download directory (created automatically)
```

## Dependencies

- **yt-dlp**: Modern YouTube downloader with extensive format support

## Notes

- Downloaded files are saved with their original titles
- The default download folder is `downloads/` in the current directory
- Progress is displayed during download with percentage, speed, and estimated time
- MP3 audio files are extracted at 192kbps quality

## Troubleshooting

If you encounter any issues:

1. Make sure you have the latest version of yt-dlp:
   ```bash
   uv add yt-dlp --upgrade
   ```

2. Check your internet connection

3. Verify the YouTube URL is correct and the video is accessible

## License

This is a simple utility script for personal use.
