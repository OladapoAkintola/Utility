import streamlit as st
import os
import yt_dlp as youtube_dl
import logging

# Configure logging for debug messages
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

def download_youtube_video(url, itag):
    try:
        logger.debug(f"Downloading YouTube video from URL: {url} with itag {itag}")
        download_folder = "youtube_video"
        ensure_folder_exists(download_folder)
        file_name = "Untitled.mp4"
        file_path = os.path.join(download_folder, file_name)
        
        # Convert the itag to the format string expected by yt-dlp
        format_str = get_format_string(itag)
        
        # Set the User-Agent header
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        
        ydl_opts = {
            'format': format_str,
            'outtmpl': os.path.join(download_folder, file_name),
            'quiet': False,
            'headers': headers  # Include the headers with the User-Agent
        }
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        logger.debug(f"YouTube video downloaded successfully to {file_path}")
        return {"success": True, "file_path": file_path}
    except Exception as e:
        logger.error(f"Exception in download_youtube_video: {str(e)}")
        return {"error": str(e)}

# Similarly, you can modify other download functions (download_x_video, download_facebook_video, etc.)
# to include the 'headers' parameter in their ydl_opts.

def download_x_video(url):
    try:
        logger.debug(f"Downloading X video from URL: {url}")
        download_folder = "x_video"
        ensure_folder_exists(download_folder)
        file_name = "Untitled.mp4"
        file_path = os.path.join(download_folder, file_name)

        # Set the User-Agent header
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }

        ydl_opts = {
            'format': 'mp4',
            'outtmpl': os.path.join(download_folder, file_name),
            'quiet': False,
            'headers': headers  # Include the headers with the User-Agent
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        logger.debug(f"X video downloaded successfully to {file_path}")
        return {"success": True, "file_path": file_path}

    except Exception as e:
        logger.error(f"Exception in download_x_video: {str(e)}")
        return {"error": str(e)}

# The rest of the functions (Facebook, Instagram, TikTok) should follow the same structure, adding 'headers' with the User-Agent.
# For example, in download_facebook_video:
def download_facebook_video(url):
    try:
        logger.debug(f"Downloading Facebook video from URL: {url}")
        download_folder = "facebook_video"
        ensure_folder_exists(download_folder)
        file_name = "Untitled.mp4"
        file_path = os.path.join(download_folder, file_name)

        # Set the User-Agent header
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }

        ydl_opts = {
            'format': 'mp4',
            'outtmpl': os.path.join(download_folder, file_name),
            'quiet': False,
            'headers': headers  # Include the headers with the User-Agent
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        logger.debug(f"Facebook video downloaded successfully to {file_path}")
        return {"success": True, "file_path": file_path}

    except Exception as e:
        logger.error(f"Exception in download_facebook_video: {str(e)}")
        return {"error": str(e)}

# Continue in the same way for Instagram, TikTok, etc.

# Streamlit UI
st.title("Multi-Platform Video Downloader")
st.write("Download videos from YouTube, X (formerly Twitter), or Facebook.")

platform = st.selectbox("Select Platform:", options=["YouTube", "X", "Facebook"])
url = st.text_input("Video URL:")

itag = None
if platform == "YouTube":
    itag = st.radio(
        "Select Resolution for YouTube:",
        options=[18, 22, 37],
        format_func=lambda x: {18: "360p", 22: "720p", 37: "1080p"}[x]
    )

if st.button("Download Video"):
    if not url.strip():
        st.error("Please enter a valid URL.")
    else:
        if platform == "YouTube":
            st.info("Downloading YouTube video...")
            with st.spinner("Downloading..."):
                result = download_youtube_video(url.strip(), itag)
        elif platform == "X":
            st.info("Downloading X video...")
            with st.spinner("Downloading..."):
                result = download_x_video(url.strip())
        elif platform == "Facebook":
            st.info("Downloading Facebook video...")
            with st.spinner("Downloading..."):
                result = download_facebook_video(url.strip())
        else:
            result = {"error": "Invalid platform selected."}
        
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
                    file_name="Untitled.mp4",
                    mime="video/mp4"
                )
                logger.debug("Rendered download button successfully.")
            except Exception as e:
                st.error(f"File error: {str(e)}")
                logger.error(f"Error reading video file: {str(e)}")
