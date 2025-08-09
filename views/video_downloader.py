import streamlit as st
import os
import yt_dlp as ytdlp
import logging
from datetime import datetime

try:
    from pytubefix import YouTube as PyTubeFixYouTube
except Exception:
    PyTubeFixYouTube = None

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
    "TikTok": "tiktok_video",
   
    "YouTube Alternative": "youtube_alt"
}
BASE_FILE_NAME = "Max utility"


def ensure_folder_exists(folder):
    """Ensure that the download folder exists."""
    if not os.path.exists(folder):
        logger.debug(f"Folder '{folder}' does not exist. Creating folder.")
        os.makedirs(folder)
    else:
        logger.debug(f"Folder '{folder}' already exists.")


def get_format_string(itag):
    """Convert the itag (possibly a string) to a valid format string for yt-dlp."""
    format_map = {
        18: '18',  # 360p
        22: '22',  # 720p
        37: '37',  # 1080p
    }
    try:
        itag_int = int(itag)
    except (ValueError, TypeError):
        return 'best'
    return format_map.get(itag_int, 'best')


def make_output_template(platform):
    """Generate a unique, sanitized filename with timestamp."""
    safe_name = BASE_FILE_NAME.replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe_name}-{platform}-{timestamp}.mp4"


def fetch_video_info(url):
    """Fetch video information including available formats using yt-dlp.

    This is used for the default downloaders (yt-dlp based) to present
    selectable resolutions to the user.
    """
    try:
        ydl_opts = {
            'quiet': True,
            'http_headers': HEADERS
        }
        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return {"success": True, "formats": info.get('formats', [])}
    except Exception as e:
        logger.error(f"Exception in fetch_video_info (yt-dlp): {e}")
        return {"error": str(e)}


def fetch_video_info_pytubefix(url):
    """Fetch available progressive streams using pytubefix (a pytube drop-in fix).

    Notes:
    - pytubefix/pytube provides stream objects with .itag and .resolution.
    - We'll expose only progressive streams here because pytubefix cannot
      merge separate audio/video streams without ffmpeg.
    """
    if PyTubeFixYouTube is None:
        return {"error": "pytubefix is not installed or failed to import."}

    try:
        yt = PyTubeFixYouTube(url)
        # Filter only progressive streams so the result is a single file (no merging)
        streams = yt.streams.filter(progressive=True).order_by('resolution').desc()
        formats = []
        for s in streams:
            formats.append({
                'format_id': str(s.itag),
                'resolution': getattr(s, 'resolution', None) or s.abr if hasattr(s, 'abr') else 'unknown',
                'mime_type': getattr(s, 'mime_type', None),
                'filesize': getattr(s, 'filesize', None)
            })
        return {"success": True, "formats": formats}
    except Exception as e:
        logger.error(f"Exception in fetch_video_info_pytubefix: {e}")
        return {"error": str(e)}


def download_video(url, platform, itag=None):
    """Download the video to the appropriate folder, using an optional itag (yt-dlp).

    This function is used for all platforms except the "YouTube Alternative"
    which uses pytubefix.
    """
    try:
        logger.debug(f"Downloading {platform} video from URL: {url} with itag: {itag}")
        download_folder = DOWNLOAD_FOLDERS.get(platform, "downloads")
        ensure_folder_exists(download_folder)

        filename = make_output_template(platform)
        file_path = os.path.join(download_folder, filename)

        ydl_opts = {
            'outtmpl': file_path,
            'quiet': False,
            'http_headers': HEADERS,
            'format': get_format_string(itag) if platform.startswith("YouTube") and itag else 'best'
        }

        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        logger.debug(f"{platform} video downloaded successfully to {file_path}")
        return {"success": True, "file_path": file_path}

    except ytdlp.utils.DownloadError as e:
        logger.error(f"Download error (yt-dlp): {e}")
        return {"error": f"Download error: {e}"}
    except Exception as e:
        logger.error(f"Exception in download_video (yt-dlp): {e}")
        return {"error": f"Exception in download_video: {e}"}


def download_video_pytubefix(url, platform, itag=None):
    """Download using pytubefix (pure-Python, progressive streams only).

    - If an itag is provided, try to select that stream.
    - Otherwise pick the highest-resolution progressive stream.
    - Returns same result dict shape as download_video.
    """
    if PyTubeFixYouTube is None:
        return {"error": "pytubefix is not available. Install with `pip install pytubefix`."}

    try:
        logger.debug(f"(pytubefix) Downloading {platform} from URL: {url} with itag: {itag}")
        download_folder = DOWNLOAD_FOLDERS.get(platform, "downloads")
        ensure_folder_exists(download_folder)

        filename = make_output_template(platform)
        # pytube's download API expects a filename without an extension sometimes; we'll
        # strip the .mp4 because pytube will append the appropriate extension.
        filename_no_ext = os.path.splitext(filename)[0]

        yt = PyTubeFixYouTube(url)

        selected_stream = None
        if itag:
            # pytube itag is usually an int
            try:
                itag_int = int(itag)
                selected_stream = yt.streams.get_by_itag(itag_int)
            except Exception:
                selected_stream = None

        if not selected_stream:
            # pick highest progressive stream
            streams = yt.streams.filter(progressive=True).order_by('resolution').desc()
            selected_stream = streams.first() if streams else None

        if not selected_stream:
            return {"error": "No progressive streams available via pytubefix."}

        # Perform download
        downloaded_path = selected_stream.download(output_path=download_folder, filename=filename_no_ext)
        # Ensure file path ends with .mp4 or similar (pytube will add ext)
        logger.debug(f"pytubefix downloaded file to {downloaded_path}")
        return {"success": True, "file_path": downloaded_path}

    except Exception as e:
        logger.error(f"Exception in download_video_pytubefix: {e}")
        return {"error": f"Exception in download_video_pytubefix: {e}"}


def main():
    st.title("Multi-Platform Video Downloader")
    st.write("Download videos from YouTube, YouTube Shorts, X, Facebook, Instagram, and TikTok.")

    st.write("For Other platforms, just paste the link in any option and click download")

    platform = st.selectbox("Select Platform:", options=list(DOWNLOAD_FOLDERS.keys()))
    url = st.text_input("Video URL:")

    itag = None
    # For YouTube platforms, fetch and let the user pick an itag/resolution
    if platform in ["YouTube", "YouTube Shorts"] and url.strip():
        st.info("Fetching available resolutions for YouTube (yt-dlp)...")
        with st.spinner("Fetching video info..."):
            info = fetch_video_info(url.strip())
        if "error" in info:
            st.error(f"Error: {info['error']}")
        else:
            # Map format_id → resolution/label
            available_itags = {
                fmt['format_id']: fmt.get('resolution') or fmt.get('format_note') or "unknown"
                for fmt in info["formats"]
                if 'format_id' in fmt
            }
            if available_itags:
                itag = st.radio(
                    "Select Resolution for YouTube:",
                    options=list(available_itags.keys()),
                    format_func=lambda x: available_itags[x]
                )
            else:
                st.warning("No selectable formats found; defaulting to best quality.")

    # For the "YouTube Alternative" option, use pytubefix to fetch progressive streams
    if platform == "YouTube Alternative" and url.strip():
        st.info("Fetching available progressive streams for YouTube Alternative (pytubefix)...")
        with st.spinner("Fetching video info via pytubefix..."):
            info = fetch_video_info_pytubefix(url.strip())
        if "error" in info:
            st.error(f"Error: {info['error']}")
            if PyTubeFixYouTube is None:
                st.info("Install pytubefix: pip install pytubefix")
        else:
            available_itags = {
                fmt['format_id']: fmt.get('resolution') or fmt.get('format_note') or fmt.get('resolution')
                for fmt in info["formats"]
                if 'format_id' in fmt
            }
            if available_itags:
                itag = st.radio(
                    "Select Resolution for YouTube Alternative:",
                    options=list(available_itags.keys()),
                    format_func=lambda x: available_itags[x]
                )
            else:
                st.warning("No progressive formats found via pytubefix; it will attempt to pick the best progressive stream.")

    if st.button("Download Video"):
        if not url.strip():
            st.error("Please enter a valid URL.")
        else:
            st.info(f"Downloading {platform} video...")
            with st.spinner("Downloading..."):
                if platform == "YouTube Alternative":
                    result = download_video_pytubefix(url.strip(), platform, itag)
                else:
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
