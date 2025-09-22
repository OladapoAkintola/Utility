import streamlit as st
import yt_dlp as ytdlp
import io
import os
import re
import requests
import tempfile
import shutil
from datetime import datetime
import logging

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/115.0.0.0 Safari/537.36'
}

BASE_FILE_NAME = "Max_Utility"


def sanitize_filename(s):
    return re.sub(r'[\\/*?:"<>|]', "", s)


def make_output_template(platform, ext="mp4"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{BASE_FILE_NAME}-{platform}-{timestamp}.{ext}"


def fetch_youtube_formats(url):
    """Fetch available video/audio formats for YouTube (only formats with url)."""
    ydl_opts = {'quiet': True, 'http_headers': HEADERS}
    with ytdlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    valid_formats = [f for f in info.get("formats", []) if f.get("url")]
    info["formats"] = valid_formats
    return info


def format_preview_label(fmt):
    """Generate a readable label for formats."""
    if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
        res = fmt.get('resolution') or fmt.get('format_note') or "unknown"
        return f"{res} ({fmt.get('ext')})"
    elif fmt.get('vcodec') == 'none':
        return f"{fmt.get('abr', 'unknown')} kbps ({fmt.get('ext')})"
    else:
        return f"{fmt.get('ext')}"


def download_media(url, platform, itag=None, audio_only=False):
    """
    Reliable download flow:
      1) try to extract metadata to get a stable id (for caching)
      2) if cached -> return cache
      3) download into a temp dir with outtmpl '%(id)s.%(ext)s'
      4) after yt-dlp finishes, resolve final filename (handle mp3 postproc)
      5) copy into BytesIO, cache, cleanup temp dir
    """
    ext = "mp3" if audio_only else "mp4"
    buffer = io.BytesIO()

    # --- 1) metadata step to get a stable id for caching ---
    meta_id = None
    try:
        with ytdlp.YoutubeDL({'quiet': True, 'http_headers': HEADERS}) as ydl:
            meta = ydl.extract_info(url, download=False)
            meta_id = meta.get('id') or sanitize_filename(url.split("/")[-1])
    except Exception:
        # couldn't get metadata (some platforms). fallback to URL-based id
        meta_id = sanitize_filename(url.split("/")[-1])

    cache_file = os.path.join(CACHE_DIR, f"{platform}_{meta_id}.{ext}")
    if os.path.exists(cache_file):
        # --- cached: return immediately ---
        with open(cache_file, "rb") as f:
            buffer.write(f.read())
        buffer.seek(0)
        return {"success": True, "buffer": buffer, "filename": os.path.basename(cache_file), "audio_only": audio_only}

    # --- 2) create temp dir and predictable template ---
    temp_dir = tempfile.mkdtemp(prefix="ydl_")
    outtmpl = os.path.join(temp_dir, "%(id)s.%(ext)s")
    ydl_opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'http_headers': HEADERS,
        'noplaylist': True
    }

    # immediate audio-only behaviour: force best audio and postprocess
    if audio_only:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        })
    elif itag:
        ydl_opts['format'] = itag
    else:
        ydl_opts['format'] = 'bestvideo+bestaudio/best'

    final_path = None
    info = None

    try:
        # primary attempt
        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
            except Exception as err:
                # fallback attempt with generic 'best'
                logger.warning("Primary download failed (%s). Retrying with 'best'.", err)
                ydl_opts['format'] = 'best'
                with ytdlp.YoutubeDL(ydl_opts) as ydl2:
                    info = ydl2.extract_info(url, download=True)
                    # prepare filename using ydl2
                    prepared = ydl2.prepare_filename(info)
                    # if audio_only, postprocessor should have created .mp3
                    base = os.path.splitext(prepared)[0]
                    # try candidate extensions
                    candidates = [base + e for e in (".mp3", ".m4a", ".webm", ".mp4", ".opus")]
                    final_path = next((p for p in candidates if os.path.exists(p)), None)
            else:
                # got info from first attempt; compute prepared filename and final path
                prepared = ydl.prepare_filename(info)
                base = os.path.splitext(prepared)[0]
                if audio_only:
                    # postprocessor creates .mp3
                    candidates = [base + e for e in (".mp3", ".m4a", ".webm", ".opus")]
                    final_path = next((p for p in candidates if os.path.exists(p)), None)
                else:
                    # non-audio: prepared file should exist (mp4/mkv/webm)
                    if os.path.exists(prepared):
                        final_path = prepared
                    else:
                        candidates = [base + e for e in (".mp4", ".mkv", ".webm", ".mp4")]
                        final_path = next((p for p in candidates if os.path.exists(p)), None)

        # if we still don't have final_path, search temp_dir for largest file (last resort)
        if not final_path:
            all_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir)]
            all_files = [p for p in all_files if os.path.isfile(p)]
            if all_files:
                # pick largest file (likely the media file)
                final_path = max(all_files, key=os.path.getsize)

        if not final_path or not os.path.exists(final_path):
            raise FileNotFoundError(f"Could not locate downloaded media in temp dir: {temp_dir}")

        # --- copy into BytesIO ---
        with open(final_path, "rb") as fh:
            buffer.write(fh.read())
        buffer.seek(0)

        # --- cache using info['id'] if available, else meta_id ---
        actual_id = (info.get('id') if info and info.get('id') else meta_id)
        cache_file = os.path.join(CACHE_DIR, f"{platform}_{sanitize_filename(actual_id)}.{ext}")
        with open(cache_file, "wb") as cf:
            cf.write(buffer.getbuffer())

        # cleanup temp dir
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            logger.debug("Failed to remove temp dir %s", temp_dir)

        return {"success": True, "buffer": buffer, "filename": os.path.basename(cache_file), "audio_only": audio_only}

    except