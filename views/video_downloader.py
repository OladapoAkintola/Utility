import streamlit as st
import yt_dlp as ytdlp
import io
import os
import re
import requests
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
    """Fetch available video/audio formats for YouTube."""
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
    """Download media into BytesIO buffer with safe fallbacks."""
    ext = "mp3" if audio_only else "mp4"
    buffer = io.BytesIO()
    temp_filename = make_output_template(platform, ext)

    # Cache path
    video_id = sanitize_filename(url.split("/")[-1])
    cache_file = os.path.join(CACHE_DIR, f"{video_id}.{ext}")
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            buffer.write(f.read())
        buffer.seek(0)
        return {"success": True, "buffer": buffer, "filename": os.path.basename(cache_file), "audio_only": audio_only}

    ydl_opts = {
        'outtmpl': temp_filename,
        'quiet': True,
        'http_headers': HEADERS,
        'noplaylist': True
    }

    if audio_only:
        # Always force best audio
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

    try:
        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            if audio_only:
                if "requested_downloads" in info and info["requested_downloads"]:
                    temp_filename = info["requested_downloads"][0]["_filename"]
                else:
                    temp_filename = os.path.splitext(temp_filename)[0] + ".mp3"

        with open(temp_filename, "rb") as f:
            buffer.write(f.read())
        buffer.seek(0)

        # Save to cache
        with open(cache_file, "wb") as f:
            f.write(buffer.getbuffer())

        os.remove(temp_filename)
        return {"success": True, "buffer": buffer, "filename": os.path.basename(cache_file), "audio_only": audio_only}

    except Exception as e:
        logger.error(f"Download failed: {e}")
        return {"error": str(e)}


def main():
    st.title("🌐 Multi-Platform Video Downloader 2025")
    st.write("Supports YouTube, Shorts, X, TikTok, Instagram, Facebook.")

    platform = st.selectbox("Platform", ["YouTube", "YouTube Shorts", "X", "Facebook", "Instagram", "TikTok"])
    url = st.text_input("Video URL")

    itag = None

    if platform in ["YouTube", "YouTube Shorts"] and url.strip():
        st.info("Fetching YouTube formats...")
        try:
            info = fetch_youtube_formats(url.strip())
        except Exception as e:
            st.error(f"Failed to fetch formats: {e}")
            return

        video_itags = {}
        for fmt in info.get('formats', []):
            if 'format_id' not in fmt:
                continue
            label = format_preview_label(fmt)
            if fmt.get('vcodec') != 'none':
                if label not in video_itags.values():
                    video_itags[fmt['format_id']] = label

        st.subheader("Video Preview")
        if info.get("thumbnail"):
            try:
                thumb_resp = requests.get(info["thumbnail"], timeout=10)
                st.image(thumb_resp.content, caption=info.get("title"), use_container_width=True)
            except:
                pass

        if video_itags:
            itag = st.radio("Select Video Format", list(video_itags.keys()), format_func=lambda x: video_itags[x])

    # Two separate buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬇️ Download Video"):
            if not url.strip():
                st.error("Please enter a valid URL.")
                return
            st.info("Downloading video...")
            result = download_media(url.strip(), platform, itag, audio_only=False)
            if "error" in result:
                st.error(f"Error: {result['error']}")
                return
            st.success("Download Successful! 🎉")
            st.video(result["buffer"])
            st.download_button(
                label="Save Video",
                data=result["buffer"],
                file_name=result["filename"],
                mime="video/mp4"
            )

    with col2:
        if st.button("🎵 Download Audio"):
            if not url.strip():
                st.error("Please enter a valid URL.")
                return
            st.info("Extracting audio...")
            result = download_media(url.strip(), platform, None, audio_only=True)
            if "error" in result:
                st.error(f"Error: {result['error']}")
                return
            st.success("Audio Extracted! 🎉")
            st.audio(result["buffer"], format="audio/mp3")
            st.download_button(
                label="Save Audio",
                data=result["buffer"],
                file_name=result["filename"],
                mime="audio/mpeg"
            )


if __name__ == "__main__":
    main()