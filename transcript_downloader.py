#!/usr/bin/env python3
"""
YouTube Transcript Downloader
A simple command-line tool to download transcripts/subtitles from YouTube videos.
Falls back to downloading audio and transcribing with local Whisper or Whishper if no transcript available.
"""

import argparse
import sys
import os
import subprocess
import tempfile
import time
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter, JSONFormatter, WebVTTFormatter
import re
import requests

# Try to import whisper - it's optional
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


def extract_video_id(url):
    """
    Extract video ID from YouTube URL.

    Args:
        url (str): YouTube video URL or video ID

    Returns:
        str: Video ID
    """
    # If it's already a video ID (11 characters), return it
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url

    # Extract from various YouTube URL formats
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError(f"Could not extract video ID from: {url}")


def get_transcript(video_id, languages=None):
    """
    Get transcript for a video.

    Args:
        video_id (str): YouTube video ID
        languages (list): Preferred languages (default: ['en'])

    Returns:
        tuple: (transcript data, language used)
    """
    if languages is None:
        languages = ['en']

    try:
        # Try each language in order
        for lang in languages:
            try:
                transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                return transcript_data, lang
            except:
                continue

        # If no preferred language works, try without language specification
        try:
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
            return transcript_data, 'unknown'
        except:
            pass

        raise Exception("No transcripts available for this video")

    except Exception as e:
        raise Exception(f"Error fetching transcript: {e}")


def format_transcript(transcript_data, format_type='text'):
    """
    Format transcript data.

    Args:
        transcript_data (list): Raw transcript data
        format_type (str): Output format (text, json, vtt)

    Returns:
        str: Formatted transcript
    """
    if format_type == 'text':
        formatter = TextFormatter()
        return formatter.format_transcript(transcript_data)
    elif format_type == 'json':
        formatter = JSONFormatter()
        return formatter.format_transcript(transcript_data)
    elif format_type == 'vtt':
        formatter = WebVTTFormatter()
        return formatter.format_transcript(transcript_data)
    else:
        raise ValueError(f"Unknown format type: {format_type}")


def save_transcript(transcript_text, output_path):
    """
    Save transcript to file.

    Args:
        transcript_text (str): Formatted transcript
        output_path (Path): Output file path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(transcript_text)


def download_audio(url, output_dir):
    """
    Download audio from YouTube video using yt-dlp.

    Args:
        url (str): YouTube video URL
        output_dir (Path): Directory to save audio file

    Returns:
        Path: Path to downloaded audio file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create a temporary filename
    output_template = str(output_dir / "%(id)s.%(ext)s")

    print("Downloading audio from YouTube...")

    # Use yt-dlp to download audio only
    cmd = [
        'yt-dlp',
        '--extract-audio',
        '--audio-format', 'mp3',
        '--audio-quality', '0',  # Best quality
        '--output', output_template,
        '--no-playlist',
        url
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Find the downloaded file
        video_id = extract_video_id(url)
        audio_file = output_dir / f"{video_id}.mp3"

        if audio_file.exists():
            print(f"Audio downloaded: {audio_file}")
            return audio_file
        else:
            raise Exception("Audio file not found after download")

    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to download audio: {e.stderr}")


def transcribe_with_whishper(audio_file, whishper_url, language='en'):
    """
    Transcribe audio file using Whishper API.

    Args:
        audio_file (Path): Path to audio file
        whishper_url (str): Whishper server URL
        language (str): Language code for transcription

    Returns:
        str: Transcribed text
    """
    print(f"Transcribing with Whishper at {whishper_url}...")

    # Prepare the API endpoint
    api_endpoint = f"{whishper_url.rstrip('/')}/api/transcriptions"

    try:
        # Open and send the audio file
        with open(audio_file, 'rb') as f:
            files = {'file': (audio_file.name, f, 'audio/mpeg')}
            data = {
                'language': language,
                'task': 'transcribe'
            }

            print("Uploading audio to Whishper (this may take a while)...")
            response = requests.post(api_endpoint, files=files, data=data, timeout=600)

            if response.status_code == 200:
                result = response.json()

                # Extract text from the response
                if 'text' in result:
                    return result['text']
                elif 'segments' in result:
                    # Combine all segments
                    return ' '.join(segment.get('text', '') for segment in result['segments'])
                else:
                    raise Exception(f"Unexpected response format: {result}")
            else:
                raise Exception(f"Whishper API error: {response.status_code} - {response.text}")

    except requests.exceptions.Timeout:
        raise Exception("Transcription timed out. The audio file may be too large.")
    except requests.exceptions.ConnectionError:
        raise Exception(f"Could not connect to Whishper server at {whishper_url}. Make sure it's running.")
    except Exception as e:
        raise Exception(f"Transcription failed: {e}")


def transcribe_with_local_whisper(audio_file, language='en', model_size='base'):
    """
    Transcribe audio file using local Whisper model.

    Args:
        audio_file (Path): Path to audio file
        language (str): Language code for transcription
        model_size (str): Whisper model size (tiny, base, small, medium, large)

    Returns:
        str: Transcribed text
    """
    if not WHISPER_AVAILABLE:
        raise Exception("OpenAI Whisper is not installed. Install with: uv add openai-whisper")

    print(f"Transcribing with local Whisper (model: {model_size})...")
    print("Note: First run will download the model (~140MB for base model)")

    try:
        # Load the model
        print(f"Loading Whisper model...")
        model = whisper.load_model(model_size)

        # Transcribe
        print(f"Transcribing audio (this may take a few minutes)...")
        result = model.transcribe(
            str(audio_file),
            language=language if language != 'en' else None,  # Auto-detect if not specified
            fp16=False  # Use FP32 for better compatibility
        )

        return result['text']

    except Exception as e:
        raise Exception(f"Local Whisper transcription failed: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Download YouTube video transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download transcript in text format (auto-fallback to Whishper if no transcript)
  python transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"

  # Download transcript in JSON format
  python transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -f json

  # Force audio transcription with Whishper (skip transcript check)
  python transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" --audio-only

  # Use custom Whishper server
  python transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" --whishper-url http://192.168.1.100:8082

  # Specify output file and keep audio file
  python transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -o transcript.txt --keep-audio

  # Specify language preference (works for both transcript and Whishper)
  python transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -l fr,en
        """
    )

    parser.add_argument(
        'url',
        help='YouTube video URL or video ID'
    )

    parser.add_argument(
        '-f', '--format',
        choices=['text', 'json', 'vtt'],
        default='text',
        help='Output format (default: text)'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output file path (default: transcripts/<video_id>.<format>)'
    )

    parser.add_argument(
        '-l', '--languages',
        default='en',
        help='Comma-separated list of preferred languages (default: en). Example: en,fr,es'
    )

    parser.add_argument(
        '--list-transcripts',
        action='store_true',
        help='List available transcripts for the video'
    )

    parser.add_argument(
        '--whishper-url',
        default='http://localhost:8082',
        help='Whishper server URL (default: http://localhost:8082). Used for transcription fallback when no transcript available.'
    )

    parser.add_argument(
        '--keep-audio',
        action='store_true',
        help='Keep downloaded audio file after transcription'
    )

    parser.add_argument(
        '--audio-only',
        action='store_true',
        help='Skip transcript fetching and use Whishper directly'
    )

    parser.add_argument(
        '--use-local-whisper',
        action='store_true',
        help='Use local Whisper instead of Whishper server (no server required)'
    )

    parser.add_argument(
        '--whisper-model',
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='Whisper model size for local transcription (default: base)'
    )

    args = parser.parse_args()

    try:
        # Extract video ID
        video_id = extract_video_id(args.url)
        print(f"Video ID: {video_id}")

        # List transcripts if requested
        if args.list_transcripts:
            print("\nListing available transcripts...")
            try:
                # Try common languages to see what's available
                common_langs = ['en', 'fr', 'es', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh-Hans', 'ar']
                available = []
                for lang in common_langs:
                    try:
                        YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                        available.append(lang)
                    except:
                        pass

                if available:
                    print("\nAvailable transcript languages:")
                    for lang in available:
                        print(f"  - {lang}")
                else:
                    print("\nNo transcripts found in common languages. Try without --list-transcripts to get any available transcript.")
            except Exception as e:
                print(f"Error listing transcripts: {e}")

            return

        # Parse languages
        languages = [lang.strip() for lang in args.languages.split(',')]
        transcript_text = None
        audio_file = None

        # Try to get existing transcript first (unless --audio-only)
        if not args.audio_only:
            try:
                print(f"Fetching transcript (preferred languages: {', '.join(languages)})...")
                transcript_data, language_used = get_transcript(video_id, languages)
                print(f"Found transcript in: {language_used}")
                print(f"Transcript entries: {len(transcript_data)}")

                # Format transcript
                transcript_text = format_transcript(transcript_data, args.format)
            except Exception as e:
                print(f"No transcript available: {e}")
                if args.use_local_whisper or WHISPER_AVAILABLE:
                    print("Falling back to audio transcription with local Whisper...")
                else:
                    print("Falling back to audio transcription with Whishper...")

        # If no transcript, use transcription
        if transcript_text is None:
            try:
                # Download audio
                temp_dir = Path(tempfile.gettempdir()) / 'youtube_transcripts'
                audio_file = download_audio(args.url, temp_dir)

                primary_language = languages[0] if languages else 'en'

                # Try local Whisper first if available or requested
                if args.use_local_whisper or WHISPER_AVAILABLE:
                    try:
                        transcript_text = transcribe_with_local_whisper(
                            audio_file,
                            primary_language,
                            args.whisper_model
                        )
                        print(f"\nTranscription completed successfully with local Whisper!")
                    except Exception as whisper_error:
                        if args.use_local_whisper:
                            # User explicitly requested local whisper, don't fallback
                            raise whisper_error
                        print(f"\nLocal Whisper failed: {whisper_error}")
                        print("Falling back to Whishper server...")
                        # Try Whishper as fallback
                        transcript_text = transcribe_with_whishper(audio_file, args.whishper_url, primary_language)
                        print(f"\nTranscription completed successfully with Whishper!")
                else:
                    # Use Whishper directly
                    transcript_text = transcribe_with_whishper(audio_file, args.whishper_url, primary_language)
                    print(f"\nTranscription completed successfully!")

            except Exception as e:
                print(f"\nError during audio transcription: {e}", file=sys.stderr)
                # Cleanup audio file if exists
                if audio_file and audio_file.exists() and not args.keep_audio:
                    audio_file.unlink()
                sys.exit(1)

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            extension = args.format if args.format != 'text' else 'txt'
            output_path = Path('transcripts') / f"{video_id}.{extension}"

        # Save transcript
        save_transcript(transcript_text, output_path)
        print(f"\nTranscript saved to: {output_path.absolute()}")

        # Cleanup audio file if downloaded and not keeping it
        if audio_file and audio_file.exists() and not args.keep_audio:
            print(f"Cleaning up audio file: {audio_file}")
            audio_file.unlink()

    except ValueError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
