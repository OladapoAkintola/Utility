import streamlit as st
import os
import yt_dlp as youtube_dl
import logging

# Configure logging for debug messages
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
}
DOWNLOAD_FOLDERS = {
    "YouTube": "youtube_video",
    "X": "x_video",
    "Facebook": "facebook_video"
}
DEFAULT_FILE_NAME = "Untitled.mp4"

def ensure_folder_exists(folder):
    """Ensure that the download folder exists."""
    if not os.path.exists(folder):
        logger.debug(f"Folder '{folder}' does not exist. Creating folder.")
        os.makedirs(folder)
    else:
        logger.debug(f"Folder '{folder}' already exists.")

def get_format_string(itag):
    """Convert the itag integer to a valid format string for yt-dlp."""
    format_map = {
        18: '18',  # 360p
        22: '22',  # 720p
        37: '37',  # 1080p
    }
    return format_map.get(itag, 'best')

def fetch_video_info(url):
    """Fetch video information including available resolutions."""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best',
            'headers': HEADERS
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            formats = info_dict.get('formats', [])
            return {"success": True, "formats": formats}
    except Exception as e:
        logger.error(f"Exception in fetch_video_info: {str(e)}")
        return {"error": str(e)}

def download_video(url, platform, itag=None):
    """Download video from the given URL for the specified platform."""
    try:
        logger.debug(f"Downloading {platform} video from URL: {url} with itag {itag}")
        download_folder = DOWNLOAD_FOLDERS.get(platform, "downloads")
        ensure_folder_exists(download_folder)
        file_path = os.path.join(download_folder, DEFAULT_FILE_NAME)

        ydl_opts = {
            'outtmpl': file_path,
            'quiet': False,
            'headers': HEADERS
        }

        if platform == "YouTube" and itag:
            ydl_opts['format'] = get_format_string(itag)
        else:
            ydl_opts['format'] = 'mp4'

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        logger.debug(f"{platform} video downloaded successfully to {file_path}")
        return {"success": True, "file_path": file_path}
    except youtube_dl.utils.DownloadError as e:
        logger.error(f"Download error: {str(e)}")
        return {"error": f"Download error: {str(e)}"}
    except Exception as e:
        logger.error(f"Exception in download_video: {str(e)}")
        return {"error": f"Exception in download_video: {str(e)}"}

# Streamlit UI
def main():
    st.title("Multi-Platform Video Downloader")
    st.write("Download videos from YouTube, X (formerly Twitter), or Facebook.")

    platform = st.selectbox("Select Platform:", options=["YouTube", "X", "Facebook"])
    url = st.text_input("Video URL:")

    itag = None
    if platform == "YouTube" and url.strip():
        st.info("Fetching available resolutions...")
        with st.spinner("Fetching..."):
            video_info = fetch_video_info(url.strip())
        if "error" in video_info:
            st.error(f"Error: {video_info['error']}")
        else:
            formats = video_info["formats"]
            available_itags = {f['format_id']: f['format_note'] for f in formats if 'format_id' in f}
            itag = st.radio(
                "Select Resolution for YouTube:",
                options=list(available_itags.keys()),
                format_func=lambda x: available_itags[x]
            )

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
                    with open(file_path, "rb") as file:
                        video_bytes = file.read()
                    st.download_button(
                        label="⬇️ Save Video",
                        data=video_bytes,
                        file_name=DEFAULT_FILE_NAME,
                        mime="video/mp4"
                    )
                    logger.debug("Rendered download button successfully.")
                except Exception as e:
                    st.error(f"File error: {str(e)}")
                    logger.error(f"Error reading video file: {str(e)}")
main()
