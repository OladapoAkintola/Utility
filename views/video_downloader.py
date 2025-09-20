import streamlit as st
import os
import yt_dlp as ytdlp
import logging
from datetime import datetime
import io

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/58.0.3029.110 Safari/537.36'
    )
}

BASE_FILE_NAME = "Max utility"

def make_output_template(platform, ext="mp4"):
    safe_name = BASE_FILE_NAME.replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe_name}-{platform}-{timestamp}.{ext}"

def fetch_video_info(url):
    """Fetch video info including available formats."""
    try:
        ydl_opts = {'quiet': True, 'http_headers': HEADERS}
        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return {"success": True, "formats": info.get('formats', [])}
    except Exception as e:
        logger.error(f"Exception in fetch_video_info: {e}")
        return {"error": str(e)}

def download_video(url, platform, itag=None, audio_only=False):
    """Download video/audio, load into BytesIO, and delete temp file."""
    try:
        logger.debug(f"Downloading {platform} from URL: {url} with itag: {itag}, audio_only: {audio_only}")
        
        ext = "mp3" if audio_only else "mp4"
        filename = make_output_template(platform, ext)
        buffer = io.BytesIO()

        if audio_only:
            ydl_opts = {
                'outtmpl': filename,
                'quiet': False,
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
                'quiet': False,
                'http_headers': HEADERS,
                'format': format_str
            }

        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=True)
            temp_file = ydl.prepare_filename(result)
            if audio_only:
                temp_file = os.path.splitext(temp_file)[0] + ".mp3"

        with open(temp_file, "rb") as f:
            buffer.write(f.read())
        buffer.seek(0)

        # cleanup temp file
        os.remove(temp_file)

        return {"success": True, "filename": filename, "buffer": buffer}

    except Exception as e:
        logger.error(f"Exception in download_video: {e}")
        return {"error": f"{e}"}

def main():
    st.title("Multi-Platform Video Downloader")
    st.write("Download videos from YouTube, YouTube Shorts, X, Facebook, Instagram, and TikTok.")

    platform = st.selectbox("Select Platform:", options=[
        "YouTube", "YouTube Shorts", "X", "Facebook", "Instagram", "TikTok"
    ])
    url = st.text_input("Video URL:")

    itag = None
    audio_only = False

    if platform in ["YouTube", "YouTube Shorts"] and url.strip():
        st.info("Fetching available formats for YouTube...")
        with st.spinner("Fetching video info..."):
            info = fetch_video_info(url.strip())
        if "error" in info:
            st.error(f"Error: {info['error']}")
        else:
            video_itags = {}
            audio_itags = {}
            seen_video_labels = set()
            seen_audio_labels = set()

            for fmt in info["formats"]:
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

    if st.button("Download"):
        if not url.strip():
            st.error("Please enter a valid URL.")
        else:
            st.info(f"Downloading {platform}...")
            with st.spinner("Downloading..."):
                result = download_video(url.strip(), platform, itag, audio_only)
            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                st.success("Download Successful!")
                st.balloons()
                st.download_button(
                    label="⬇️ Save File",
                    data=result["buffer"],
                    file_name=result["filename"],
                    mime="audio/mpeg" if audio_only else "video/mp4"
                )

if __name__ == "__main__":
    main()