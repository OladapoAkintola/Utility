import streamlit as st
import os
import yt_dlp as ytdlp
import logging
from datetime import datetime

# Configure logging for debug messages
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/58.0.3029.110 Safari/537.36'
    )
}
DOWNLOAD_FOLDERS = {
    "YouTube": "youtube_video",
    "YouTube Shorts": "youtube_shorts",
    "X": "x_video",
    "Facebook": "facebook_video",
    "Instagram": "instagram_video",
    "TikTok": "tiktok_video"
}
BASE_FILE_NAME = "Max utility"

def ensure_folder_exists(folder):
    if not os.path.exists(folder):
        logger.debug(f"Folder '{folder}' does not exist. Creating folder.")
        os.makedirs(folder)
    else:
        logger.debug(f"Folder '{folder}' already exists.")

def make_output_template(platform):
    safe_name = BASE_FILE_NAME.replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe_name}-{platform}-{timestamp}.mp4"

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

def download_video(url, platform, itag=None):
    """Download video using exact format_id or fallback to best available."""
    try:
        logger.debug(f"Downloading {platform} video from URL: {url} with itag: {itag}")
        download_folder = DOWNLOAD_FOLDERS.get(platform, "downloads")
        ensure_folder_exists(download_folder)

        filename = make_output_template(platform)
        file_path = os.path.join(download_folder, filename)

        # Use selected format_id or fallback to best
        format_str = itag if itag else 'bestvideo+bestaudio/best'

        ydl_opts = {
            'outtmpl': file_path,
            'quiet': False,
            'http_headers': HEADERS,
            'format': format_str
        }

        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        logger.debug(f"{platform} video downloaded successfully to {file_path}")
        return {"success": True, "file_path": file_path}

    except ytdlp.utils.DownloadError as e:
        logger.error(f"Download error: {e}")
        return {"error": f"Download error: {e}"}
    except Exception as e:
        logger.error(f"Exception in download_video: {e}")
        return {"error": f"Exception in download_video: {e}"}

def main():
    st.title("Multi-Platform Video Downloader")
    st.write("Download videos from YouTube, YouTube Shorts, X, Facebook, Instagram, and TikTok.")

    platform = st.selectbox("Select Platform:", options=list(DOWNLOAD_FOLDERS.keys()))
    url = st.text_input("Video URL:")

    itag = None

    if platform in ["YouTube", "YouTube Shorts"] and url.strip():
        st.info("Fetching available resolutions for YouTube...")
        with st.spinner("Fetching video info..."):
            info = fetch_video_info(url.strip())
        if "error" in info:
            st.error(f"Error: {info['error']}")
        else:
            # Build a map of unique resolutions to format_ids
            available_itags = {}
            seen_labels = set()
            for fmt in info["formats"]:
                if 'format_id' in fmt:
                    res = fmt.get('resolution') or fmt.get('format_note') or "unknown"
                    ext = fmt.get('ext', 'mp4')
                    label = f"{res} ({ext})"
                    # Skip duplicates
                    if label not in seen_labels:
                        available_itags[fmt['format_id']] = label
                        seen_labels.add(label)

            if available_itags:
                itag = st.radio(
                    "Select format for YouTube:",
                    options=list(available_itags.keys()),
                    format_func=lambda x: available_itags[x]
                )
            else:
                st.warning("No selectable formats found; defaulting to best quality.")

    if st.button("Download Video"):
        if not url.strip():
            st.error("Please enter a valid URL.")
        else:
            st.info(f"Downloading {platform} video...")
            with st.spinner("Downloading..."):
                result = download_video(url.strip(), platform, itag)
            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                st.success("Video Downloaded Successfully!")
                st.balloons()
                file_path = result["file_path"]
                st.video(file_path)
                try:
                    with open(file_path, "rb") as f:
                        video_bytes = f.read()
                    st.download_button(
                        label="⬇️ Save Video",
                        data=video_bytes,
                        file_name=os.path.basename(file_path),
                        mime="video/mp4"
                    )
                    logger.debug("Rendered download button successfully.")
                except Exception as e:
                    st.error(f"File error: {e}")
                    logger.error(f"Error reading video file: {e}")

if __name__ == "__main__":
    main()