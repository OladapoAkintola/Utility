import streamlit as st
import os
import yt_dlp as ytdlp
import logging
from datetime import datetime
import io
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/115.0.0.0 Safari/537.36'
    )
}

BASE_FILE_NAME = "Max_Utility"
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def sanitize_filename(s):
    """Sanitize filename for filesystem."""
    return re.sub(r'[\\/*?:"<>|]', "", s)


def make_output_template(platform, ext="mp4"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = BASE_FILE_NAME
    return f"{safe_name}-{platform}-{timestamp}.{ext}"


def fetch_video_info(url):
    """Fetch video info including available formats."""
    try:
        ydl_opts = {'quiet': True, 'http_headers': HEADERS}
        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return {"success": True, "formats": info.get('formats', []), "info": info}
    except Exception as e:
        logger.error(f"Exception in fetch_video_info: {e}")
        return {"error": str(e)}


def download_video(url, platform, itag=None, audio_only=False):
    """Download video/audio to BytesIO buffer."""
    try:
        ext = "mp3" if audio_only else "mp4"
        filename = make_output_template(platform, ext)
        buffer = io.BytesIO()

        # Cache path
        video_id = sanitize_filename(url.split("/")[-1])
        cache_file = os.path.join(CACHE_DIR, f"{video_id}.{ext}")
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                buffer.write(f.read())
            buffer.seek(0)
            return {"success": True, "filename": os.path.basename(cache_file),
                    "buffer": buffer, "audio_only": audio_only}

        if audio_only:
            ydl_opts = {
                'outtmpl': filename,
                'quiet': True,
                'http_headers': HEADERS,
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            }
        else:
            format_str = itag if itag else 'bestvideo+bestaudio/best'
            ydl_opts = {
                'outtmpl': filename,
                'quiet': True,
                'http_headers': HEADERS,
                'format': format_str
            }

        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=True)
            temp_file = ydl.prepare_filename(result)
            if audio_only:
                temp_file = os.path.splitext(temp_file)[0] + ".mp3"

        # Copy into BytesIO
        with open(temp_file, "rb") as f:
            buffer.write(f.read())
        buffer.seek(0)

        # Save to cache
        with open(cache_file, "wb") as f:
            f.write(buffer.getbuffer())

        # Cleanup temp file
        os.remove(temp_file)

        return {"success": True, "filename": os.path.basename(cache_file),
                "buffer": buffer, "audio_only": audio_only}

    except Exception as e:
        logger.error(f"Exception in download_video: {e}")
        return {"error": str(e)}


def main():
    st.title("🌐 Multi-Platform Video Downloader")
    st.write("Supports YouTube, YouTube Shorts, X, Facebook, Instagram, TikTok, Threads.")

    platform = st.selectbox("Select Platform:", options=[
        "YouTube", "YouTube Shorts", "X", "Facebook", "Instagram", "TikTok", "Threads"
    ])
    url = st.text_input("Video URL:")

    itag = None
    audio_only = False

    if platform in ["YouTube", "YouTube Shorts"] and url.strip():
        st.info("Fetching available formats for YouTube...")
        with st.spinner("Fetching video info..."):
            info_res = fetch_video_info(url.strip())
        if "error" in info_res:
            st.error(f"Error: {info_res['error']}")
            return

        formats = info_res["formats"]
        video_itags = {}
        audio_itags = {}
        seen_video_labels = set()
        seen_audio_labels = set()

        for fmt in formats:
            if 'format_id' not in fmt:
                continue
            res = fmt.get('resolution') or fmt.get('format_note') or "unknown"
            ext = fmt.get('ext', 'mp4')
            label = f"{res} ({ext})"

            if fmt.get('vcodec') != 'none':  # Video
                if label not in seen_video_labels:
                    video_itags[fmt['format_id']] = label
                    seen_video_labels.add(label)
            elif fmt.get('acodec') != 'none':  # Audio
                audio_label = f"{fmt.get('abr', 'unknown')}kbps ({ext})"
                if audio_label not in seen_audio_labels:
                    audio_itags[fmt['format_id']] = audio_label
                    seen_audio_labels.add(audio_label)

        audio_only = st.checkbox("Audio Only (MP3)")

        if audio_only and audio_itags:
            itag = st.radio(
                "Select audio quality:",
                options=list(audio_itags.keys()),
                format_func=lambda x: audio_itags[x]
            )
        elif not audio_only and video_itags:
            itag = st.radio(
                "Select video format:",
                options=list(video_itags.keys()),
                format_func=lambda x: video_itags[x]
            )

    elif platform in ["X", "Facebook", "Instagram", "TikTok", "Threads"]:
        audio_only = st.checkbox("Audio Only (MP3)")

    if st.button("Download"):
        if not url.strip():
            st.error("Please enter a valid URL.")
            return

        st.info(f"Downloading {platform}...")
        with st.spinner("Downloading..."):
            result = download_video(url.strip(), platform, itag, audio_only)

        if "error" in result:
            st.error(f"Error: {result['error']}")
        else:
            st.success("Download Successful! 🎉")
            st.balloons()

            if result["audio_only"]:
                st.audio(result["buffer"], format="audio/mp3")
            else:
                st.video(result["buffer"])

            st.download_button(
                label="⬇️ Save File",
                data=result["buffer"],
                file_name=result["filename"],
                mime="audio/mpeg" if result["audio_only"] else "video/mp4"
            )


if __name__ == "__main__":
    main()