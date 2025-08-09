import re
import os
import logging
from datetime import datetime

import streamlit as st
import yt_dlp as ytdlp

try:
    from pytubefix import YouTube as PyTubeFixYouTube
except Exception:
    PyTubeFixYouTube = None

# Logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/117.0.0.0 Safari/537.36'
    ),
    'Referer': 'https://www.youtube.com/',
    'Accept-Language': 'en-US,en;q=0.9'
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

BASE_FILE_NAME = "Max_utility"

# ---------- Utilities ----------

def ensure_folder_exists(folder: str):
    if not os.path.exists(folder):
        logger.debug(f"Creating folder: {folder}")
        os.makedirs(folder, exist_ok=True)

def make_output_template_noext(platform: str):
    """Return a safe filename base (no extension)."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_platform = platform.replace(" ", "_")
    return f"{BASE_FILE_NAME}-{safe_platform}-{timestamp}"

def normalize_youtube_url(url: str) -> str:
    """Normalize various YouTube URL forms to the canonical watch?v=ID format.

    Matches:
      - https://youtu.be/<id>
      - https://www.youtube.com/shorts/<id>
      - https://www.youtube.com/watch?v=<id>
    """
    if not url:
        return url
    url = url.strip()
    # Look for 11-char youtube ID in common patterns
    m = re.search(r"(?:v=|\/shorts\/|youtu\.be\/)([A-Za-z0-9_-]{11})", url)
    if m:
        return f"https://www.youtube.com/watch?v={m.group(1)}"
    return url

def get_format_string(itag):
    """Map common itags to a simple format string for yt-dlp; fallback to 'best'."""
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

# ---------- Fetch / Download with yt-dlp ----------

def fetch_video_info(url: str):
    """Use yt-dlp to fetch available formats (used for UI selection)."""
    try:
        ydl_opts = {'quiet': True, 'http_headers': HEADERS}
        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return {"success": True, "formats": info.get('formats', [])}
    except Exception as e:
        logger.exception("fetch_video_info failed")
        return {"error": str(e)}

def download_video(url: str, platform: str, itag=None):
    """Download using yt-dlp. Outtmpl uses dynamic extension handling via %(ext)s."""
    try:
        logger.debug("yt-dlp download: %s (itag=%s)", url, itag)
        download_folder = DOWNLOAD_FOLDERS.get(platform, "downloads")
        ensure_folder_exists(download_folder)

        filename_base = make_output_template_noext(platform)
        outtmpl = os.path.join(download_folder, filename_base + ".%(ext)s")

        ydl_opts = {
            'outtmpl': outtmpl,
            'quiet': False,
            'http_headers': HEADERS,
            'format': get_format_string(itag) if platform.startswith("YouTube") and itag else 'best',
        }

        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # After download, try to find the actual file (pick newest file with that base)
        files = sorted(
            (f for f in os.listdir(download_folder) if f.startswith(filename_base)),
            key=lambda x: os.path.getmtime(os.path.join(download_folder, x)),
            reverse=True
        )
        file_path = os.path.join(download_folder, files[0]) if files else None

        if not file_path or not os.path.exists(file_path):
            return {"error": "yt-dlp finished but output file not found."}

        logger.debug("Downloaded (yt-dlp) to %s", file_path)
        return {"success": True, "file_path": file_path}

    except ytdlp.utils.DownloadError as e:
        logger.exception("yt-dlp download error")
        return {"error": f"Download error: {str(e)}"}
    except Exception as e:
        logger.exception("yt-dlp unexpected error")
        return {"error": f"Exception in download_video: {str(e)}"}

# ---------- Fetch / Download with pytubefix (progressive only) ----------

def fetch_video_info_pytubefix(url: str):
    if PyTubeFixYouTube is None:
        return {"error": "pytubefix not installed (pip install pytubefix)"}
    try:
        yt = PyTubeFixYouTube(url)
        streams_query = yt.streams.filter(progressive=True).order_by('resolution').desc()
        stream_list = list(streams_query)
        formats = []
        for s in stream_list:
            formats.append({
                'format_id': str(getattr(s, 'itag', '')),
                'resolution': getattr(s, 'resolution', None) or getattr(s, 'abr', None) or "unknown",
                'mime_type': getattr(s, 'mime_type', None),
                'filesize': getattr(s, 'filesize', None)
            })
        return {"success": True, "formats": formats}
    except Exception as e:
        logger.exception("pytubefix fetch failed")
        return {"error": str(e)}

def download_video_pytubefix(url: str, platform: str, itag=None):
    if PyTubeFixYouTube is None:
        return {"error": "pytubefix not available. Install with `pip install pytubefix`."}
    try:
        logger.debug("pytubefix download: %s (itag=%s)", url, itag)
        download_folder = DOWNLOAD_FOLDERS.get(platform, "downloads")
        ensure_folder_exists(download_folder)

        filename_base = make_output_template_noext(platform)

        yt = PyTubeFixYouTube(url)

        selected_stream = None
        if itag:
            try:
                itag_int = int(itag)
                selected_stream = yt.streams.get_by_itag(itag_int)
            except Exception:
                selected_stream = None

        if not selected_stream:
            progressive_streams = list(yt.streams.filter(progressive=True).order_by('resolution').desc())
            selected_stream = progressive_streams[0] if progressive_streams else None

        if not selected_stream:
            return {"error": "No progressive streams available via pytubefix."}

        # pytube/pytubefix download returns the actual file path
        downloaded_path = selected_stream.download(output_path=download_folder, filename=filename_base)
        logger.debug("pytubefix downloaded to %s", downloaded_path)
        return {"success": True, "file_path": downloaded_path}
    except Exception as e:
        logger.exception("pytubefix download failed")
        return {"error": f"Exception in download_video_pytubefix: {str(e)}"}

# ---------- Streamlit UI ----------

def main():
    st.title("Multi-Platform Video Downloader")
    st.write("Download videos from multiple platforms. Shorts URLs are normalized automatically.")

    platform = st.selectbox("Select Platform:", options=list(DOWNLOAD_FOLDERS.keys()))
    raw_url = st.text_input("Video URL:")

    # Normalize YouTube / Shorts URLs before any fetch or download
    url = raw_url.strip()
    if url and ("youtube" in url or "youtu.be" in url):
        url = normalize_youtube_url(url)
        st.caption(f"Normalized URL: {url}")

    itag = None

    # For YouTube options (yt-dlp-based), fetch formats using yt-dlp
    if platform in ["YouTube", "YouTube Shorts"] and url:
        st.info("Fetching available resolutions (yt-dlp)...")
        with st.spinner("Fetching..."):
            info = fetch_video_info(url)
        if "error" in info:
            st.error(f"Error: {info['error']}")
        else:
            # Build mapping of format_id -> label (resolution or note)
            available_itags = {}
            for fmt in info.get("formats", []):
                fid = fmt.get('format_id')
                label = fmt.get('resolution') or fmt.get('format_note') or fmt.get('ext') or "unknown"
                if fid:
                    available_itags[str(fid)] = label
            if available_itags:
                itag = st.radio(
                    "Select Resolution for YouTube:",
                    options=list(available_itags.keys()),
                    format_func=lambda x: available_itags[x]
                )
            else:
                st.warning("No selectable formats found; defaulting to best quality.")

    # For the YouTube Alternative option (pytubefix), fetch progressive streams
    if platform == "YouTube Alternative" and url:
        st.info("Fetching available progressive streams for YouTube Alternative (pytubefix)...")
        with st.spinner("Fetching (pytubefix)..."):
            info = fetch_video_info_pytubefix(url)
        if "error" in info:
            st.error(f"Error: {info['error']}")
            if PyTubeFixYouTube is None:
                st.info("Install pytubefix: pip install pytubefix")
        else:
            available_itags = {}
            for fmt in info.get("formats", []):
                fid = fmt.get('format_id')
                label = fmt.get('resolution') or "unknown"
                if fid:
                    available_itags[str(fid)] = label
            if available_itags:
                itag = st.radio(
                    "Select Resolution for YouTube Alternative:",
                    options=list(available_itags.keys()),
                    format_func=lambda x: available_itags[x]
                )
            else:
                st.warning("No progressive formats found via pytubefix; will attempt best progressive stream.")

    if st.button("Download Video"):
        if not url:
            st.error("Please enter a valid URL.")
            return

        st.info(f"Downloading {platform} video...")
        with st.spinner("Downloading..."):
            if platform == "YouTube Alternative":
                result = download_video_pytubefix(url, platform, itag)
                # optional: fallback to yt-dlp if pytubefix fails
                if "error" in result:
                    logger.debug("pytubefix failed; attempting yt-dlp fallback: %s", result.get("error"))
                    result = download_video(url, platform + "_yt-dlp_fallback", itag)
            else:
                result = download_video(url, platform, itag)

        if "error" in result:
            st.error(f"Error: {result['error']}")
        else:
            st.success("Video Downloaded Successfully!")
            st.balloons()
            file_path = result["file_path"]
            try:
                st.video(file_path)
                with open(file_path, "rb") as f:
                    video_bytes = f.read()
                st.download_button(
                    label="⬇️ Save Video",
                    data=video_bytes,
                    file_name=os.path.basename(file_path),
                    mime="video/mp4"
                )
            except Exception as e:
                st.error(f"File error: {e}")
                logger.exception("Error reading/serving downloaded file")

if __name__ == "__main__":
    main()