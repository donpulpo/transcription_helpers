#!/usr/bin/env python3
"""
Podcast Transcriber
Download and transcribe podcasts from various platforms (Acast, etc.)
"""

import argparse
import sys
import json
import re
from pathlib import Path
import requests
from urllib.parse import urlparse
import tempfile

# Try to import whisper - it's optional
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


def extract_apple_podcasts_audio_url(episode_url):
    """
    Extract audio URL from an Apple Podcasts episode page.

    Args:
        episode_url (str): Apple Podcasts episode URL

    Returns:
        tuple: (audio_url, episode_title, show_title)
    """
    print(f"Fetching Apple Podcasts episode page...")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(episode_url, headers=headers, timeout=30)
        response.raise_for_status()

        # Look for JSON-LD structured data
        json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
        json_ld_matches = re.findall(json_ld_pattern, response.text, re.DOTALL)

        audio_url = None
        episode_title = "Unknown Episode"
        show_title = "Unknown Show"

        for json_str in json_ld_matches:
            try:
                data = json.loads(json_str)

                # Check if it's a PodcastEpisode
                if isinstance(data, dict) and data.get('@type') == 'PodcastEpisode':
                    # Get episode title
                    episode_title = data.get('name', episode_title)

                    # Get audio URL - Apple Podcasts uses 'url' field for audio
                    if 'url' in data:
                        audio_url = data.get('url')

                    # Also check associatedMedia
                    if not audio_url and 'associatedMedia' in data:
                        media = data['associatedMedia']
                        if isinstance(media, dict):
                            audio_url = media.get('contentUrl') or media.get('url')

                    # Get show title
                    if 'partOfSeries' in data:
                        series = data['partOfSeries']
                        if isinstance(series, dict):
                            show_title = series.get('name', show_title)

                    if audio_url:
                        break

            except json.JSONDecodeError:
                continue

        # Alternative: look for audio tags or media URLs in the HTML
        if not audio_url:
            # Try to find audio/MP3 URLs in the page
            audio_pattern = r'https?://[^\s<>"]+\.(?:mp3|m4a)'
            audio_matches = re.findall(audio_pattern, response.text)

            if audio_matches:
                # Filter for podcast hosting CDN URLs
                for url in audio_matches:
                    if any(host in url.lower() for host in ['ausha', 'acast', 'libsyn', 'buzzsprout', 'simplecast', 'megaphone']):
                        audio_url = url
                        break

                if not audio_url and audio_matches:
                    audio_url = audio_matches[0]

        if audio_url:
            print(f"Found audio: {episode_title}")
            print(f"Show: {show_title}")
            return audio_url, episode_title, show_title
        else:
            raise Exception("Could not extract audio URL from Apple Podcasts page")

    except requests.RequestException as e:
        raise Exception(f"Failed to fetch Apple Podcasts page: {e}")


def extract_acast_audio_url(episode_url):
    """
    Extract audio URL from an Acast episode page.

    Args:
        episode_url (str): Acast episode URL

    Returns:
        tuple: (audio_url, episode_title, show_title)
    """
    print(f"Fetching Acast episode page...")

    # Extract show and episode IDs from URL
    # URL format: https://shows.acast.com/{show_id}/{episode_id}
    url_pattern = r'shows\.acast\.com/([a-f0-9]+)/([a-f0-9]+)'
    url_match = re.search(url_pattern, episode_url)

    if url_match:
        show_id = url_match.group(1)
        episode_id = url_match.group(2)
        # Construct direct audio URL
        direct_audio_url = f"https://play.acast.com/s/{show_id}/{episode_id}.mp3"
        print(f"Constructed direct audio URL from IDs")
    else:
        direct_audio_url = None

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(episode_url, headers=headers, timeout=30)
        response.raise_for_status()

        # Look for JSON-LD structured data
        json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
        json_ld_matches = re.findall(json_ld_pattern, response.text, re.DOTALL)

        audio_url = None
        episode_title = "Unknown Episode"
        show_title = "Unknown Show"

        for json_str in json_ld_matches:
            try:
                data = json.loads(json_str)

                # Check if it's a PodcastEpisode
                if isinstance(data, dict) and data.get('@type') == 'PodcastEpisode':
                    # Get episode title
                    episode_title = data.get('name', episode_title)

                    # Get audio URL from associatedMedia
                    if 'associatedMedia' in data:
                        media = data['associatedMedia']
                        if isinstance(media, dict):
                            audio_url = media.get('contentUrl')

                    # Get show title
                    if 'partOfSeries' in data:
                        series = data['partOfSeries']
                        if isinstance(series, dict):
                            show_title = series.get('name', show_title)

                    if audio_url:
                        break

            except json.JSONDecodeError:
                continue

        # Alternative: look for audio tags or media URLs in the HTML
        if not audio_url:
            # Try to find audio/MP3 URLs in the page
            audio_pattern = r'https?://[^\s<>"]+\.(?:mp3|m4a)'
            audio_matches = re.findall(audio_pattern, response.text)

            if audio_matches:
                # Filter for Acast CDN URLs
                for url in audio_matches:
                    if 'acast' in url.lower() or 'media' in url.lower():
                        audio_url = url
                        break

                if not audio_url and audio_matches:
                    audio_url = audio_matches[0]

        # Use constructed direct URL as last resort
        if not audio_url and direct_audio_url:
            audio_url = direct_audio_url
            print("Using constructed audio URL")

        if audio_url:
            print(f"Found audio: {episode_title}")
            print(f"Show: {show_title}")
            return audio_url, episode_title, show_title
        else:
            raise Exception("Could not extract audio URL from Acast page")

    except requests.RequestException as e:
        raise Exception(f"Failed to fetch Acast page: {e}")


def download_audio(audio_url, output_dir, filename=None):
    """
    Download audio file from URL.

    Args:
        audio_url (str): Direct audio file URL
        output_dir (Path): Directory to save audio
        filename (str): Optional filename (will be derived from URL if not provided)

    Returns:
        Path: Path to downloaded audio file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        # Extract filename from URL
        parsed = urlparse(audio_url)
        filename = Path(parsed.path).name
        if not filename or '.' not in filename:
            filename = "podcast.mp3"

    output_file = output_dir / filename

    print(f"Downloading audio...")
    print(f"URL: {audio_url}")

    try:
        # Determine referer based on audio URL domain
        referer = None
        if 'acast' in audio_url.lower():
            referer = 'https://shows.acast.com/'
        elif 'ausha' in audio_url.lower():
            referer = 'https://podcasts.apple.com/'

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'audio/webm,audio/ogg,audio/wav,audio/*;q=0.9,application/ogg;q=0.7,video/*;q=0.6,*/*;q=0.5',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        # Add referer if we detected one
        if referer:
            headers['Referer'] = referer

        response = requests.get(audio_url, stream=True, timeout=60, headers=headers, allow_redirects=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))

        with open(output_file, 'wb') as f:
            if total_size:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    percent = (downloaded / total_size) * 100
                    print(f"\rProgress: {percent:.1f}% ({downloaded / 1024 / 1024:.1f}MB / {total_size / 1024 / 1024:.1f}MB)", end='', flush=True)
                print()
            else:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

        print(f"Audio downloaded: {output_file}")
        return output_file

    except requests.RequestException as e:
        raise Exception(f"Failed to download audio: {e}")


def transcribe_audio(audio_file, language='en', model_size='base'):
    """
    Transcribe audio file using local Whisper.

    Args:
        audio_file (Path): Path to audio file
        language (str): Language code
        model_size (str): Whisper model size

    Returns:
        str: Transcribed text
    """
    if not WHISPER_AVAILABLE:
        raise Exception("OpenAI Whisper is not installed. Install with: uv add openai-whisper")

    print(f"\nTranscribing with Whisper (model: {model_size})...")
    print("Note: First run will download the model")

    try:
        print("Loading Whisper model...")
        model = whisper.load_model(model_size)

        print("Transcribing audio (this may take several minutes)...")
        result = model.transcribe(
            str(audio_file),
            language=language if language != 'auto' else None,
            fp16=False
        )

        return result['text']

    except Exception as e:
        raise Exception(f"Transcription failed: {e}")


def save_transcript(text, output_path, metadata=None):
    """Save transcript to file with optional metadata."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        if metadata:
            f.write("=" * 60 + "\n")
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")
            f.write("=" * 60 + "\n\n")

        f.write(text)

    print(f"\nTranscript saved to: {output_path.absolute()}")


def main():
    parser = argparse.ArgumentParser(
        description="Download and transcribe podcasts from various platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Transcribe Acast podcast
  python podcast_transcriber.py "https://shows.acast.com/show-id/episode-id"

  # Transcribe Apple Podcasts episode
  python podcast_transcriber.py "https://podcasts.apple.com/es/podcast/..."

  # Transcribe with specific language and model
  python podcast_transcriber.py "PODCAST_URL" -l fr --model small

  # Keep audio file after transcription
  python podcast_transcriber.py "PODCAST_URL" --keep-audio

  # Specify output location
  python podcast_transcriber.py "PODCAST_URL" -o my_transcript.txt
        """
    )

    parser.add_argument(
        'url',
        help='Podcast episode URL (Acast and Apple Podcasts supported)'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output transcript file path (default: transcripts/<episode-name>.txt)'
    )

    parser.add_argument(
        '-l', '--language',
        default='auto',
        help='Language code for transcription (default: auto-detect). Examples: en, fr, es'
    )

    parser.add_argument(
        '--model',
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='Whisper model size (default: base)'
    )

    parser.add_argument(
        '--keep-audio',
        action='store_true',
        help='Keep downloaded audio file after transcription'
    )

    parser.add_argument(
        '--audio-dir',
        default=None,
        help='Directory to save audio files (default: temp directory)'
    )

    args = parser.parse_args()

    try:
        # Determine platform
        if 'acast.com' in args.url:
            print("Platform: Acast")
            audio_url, episode_title, show_title = extract_acast_audio_url(args.url)
        elif 'podcasts.apple.com' in args.url:
            print("Platform: Apple Podcasts")
            audio_url, episode_title, show_title = extract_apple_podcasts_audio_url(args.url)
        else:
            print("Error: Unsupported platform. Currently only Acast and Apple Podcasts are supported.", file=sys.stderr)
            sys.exit(1)

        # Download audio
        audio_dir = Path(args.audio_dir) if args.audio_dir else Path(tempfile.gettempdir()) / 'podcast_audio'

        # Create safe filename from episode title
        safe_filename = re.sub(r'[^\w\s-]', '', episode_title)
        safe_filename = re.sub(r'[-\s]+', '-', safe_filename)[:50]
        audio_filename = f"{safe_filename}.mp3"

        audio_file = download_audio(audio_url, audio_dir, audio_filename)

        # Transcribe
        transcript_text = transcribe_audio(audio_file, args.language, args.model)

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = Path('transcripts') / f"{safe_filename}.txt"

        # Save transcript with metadata
        metadata = {
            'Show': show_title,
            'Episode': episode_title,
            'Source': args.url,
            'Language': args.language,
            'Model': args.model
        }

        save_transcript(transcript_text, output_path, metadata)

        # Cleanup audio file if not keeping it
        if not args.keep_audio and audio_file.exists():
            print(f"Cleaning up audio file: {audio_file}")
            audio_file.unlink()
        elif args.keep_audio:
            print(f"Audio file saved at: {audio_file}")

        print("\nTranscription completed successfully!")

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
