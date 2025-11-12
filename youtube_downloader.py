#!/usr/bin/env python3
"""
YouTube Downloader
A simple command-line tool to download YouTube videos using yt-dlp.
"""

import argparse
import os
import sys
from pathlib import Path
import yt_dlp


def download_video(url, output_dir="downloads", format_choice="best", audio_only=False):
    """
    Download a YouTube video.

    Args:
        url (str): YouTube video URL
        output_dir (str): Directory to save the downloaded video
        format_choice (str): Quality/format choice (best, 1080p, 720p, 480p, 360p)
        audio_only (bool): Download only audio (MP3)
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Configure yt-dlp options
    ydl_opts = {
        'outtmpl': str(output_path / '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
    }

    if audio_only:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        # Video format selection
        format_map = {
            'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            '1080p': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]',
            '720p': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]',
            '480p': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]',
            '360p': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]',
        }
        ydl_opts['format'] = format_map.get(format_choice, format_map['best'])

    try:
        print(f"Downloading from: {url}")
        print(f"Output directory: {output_path.absolute()}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info first
            info = ydl.extract_info(url, download=False)
            print(f"Title: {info.get('title', 'Unknown')}")
            print(f"Duration: {info.get('duration', 0) // 60}:{info.get('duration', 0) % 60:02d}")
            print()

            # Download the video
            ydl.download([url])

        print("\nDownload completed successfully!")

    except yt_dlp.utils.DownloadError as e:
        print(f"\nError downloading video: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def progress_hook(d):
    """Display download progress."""
    if d['status'] == 'downloading':
        # Clear line and show progress
        percent = d.get('_percent_str', 'N/A')
        speed = d.get('_speed_str', 'N/A')
        eta = d.get('_eta_str', 'N/A')
        print(f"\rProgress: {percent} | Speed: {speed} | ETA: {eta}", end='', flush=True)
    elif d['status'] == 'finished':
        print("\nDownload finished, processing...")


def main():
    parser = argparse.ArgumentParser(
        description="Download YouTube videos with ease",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download best quality video
  python youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"

  # Download 720p video
  python youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -q 720p

  # Download audio only (MP3)
  python youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -a

  # Specify output directory
  python youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -o ~/Videos
        """
    )

    parser.add_argument(
        'url',
        help='YouTube video URL'
    )

    parser.add_argument(
        '-o', '--output',
        default='downloads',
        help='Output directory (default: downloads)'
    )

    parser.add_argument(
        '-q', '--quality',
        choices=['best', '1080p', '720p', '480p', '360p'],
        default='best',
        help='Video quality (default: best)'
    )

    parser.add_argument(
        '-a', '--audio-only',
        action='store_true',
        help='Download audio only (MP3 format)'
    )

    args = parser.parse_args()

    # Download the video
    download_video(
        url=args.url,
        output_dir=args.output,
        format_choice=args.quality,
        audio_only=args.audio_only
    )


if __name__ == "__main__":
    main()
