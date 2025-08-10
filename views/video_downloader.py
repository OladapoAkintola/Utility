
import re
import os
import logging
import shutil
import socket
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Tuple

import streamlit as st
import yt_dlp as ytdlp

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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_platform = platform.replace(" ", "_")
    return f"{BASE_FILE_NAME}-{safe_platform}-{timestamp}"

def normalize_youtube_url(url: str) -> str:
    if not url:
        return url
    url = url.strip()
    m = re.search(r"(?:v=|\/shorts\/|youtu\.be\/)([A-Za-z0-9_-]{11})", url)
    if m:
        return f"https://www.youtube.com/watch?v={m.group(1)}"
    return url

def get_format_string(itag):
    format_map = {18: '18', 22: '22', 37: '37'}
    try:
        itag_int = int(itag)
    except (ValueError, TypeError):
        return 'best'
    return format_map.get(itag_int, 'best')

# ---------- yt-dlp helpers ----------

def fetch_video_info(url: str):
    try:
        ydl_opts = {'quiet': True, 'http_headers': HEADERS}
        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return {"success": True, "formats": info.get('formats', []), "info": info}
    except Exception as e:
        logger.exception("fetch_video_info failed")
        return {"error": str(e)}

def download_video_to_path(url: str, platform: str, itag=None) -> dict:
    """
    Download via yt-dlp to a uniquely named file in download_folder.
    Returns {"success": True, "file_path": ...} or {"error": ...}
    """
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
            # Prevent post-processing prompts and ensure merged output if necessary
            'merge_output_format': 'mp4',
        }

        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Identify newest file matching base
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
        return {"error": f"Exception in download_video_to_path: {str(e)}"}

# ---------- Local single-file HTTP server ----------

def _find_free_port(host='127.0.0.1') -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, 0))
    port = s.getsockname()[1]
    s.close()
    return port

def start_single_file_server(file_path: str, ttl_seconds: int = 300) -> Tuple[str, threading.Thread, HTTPServer]:
    """
    Start a lightweight HTTP server on localhost that serves only `file_path`.
    Returns (url, server_thread, httpd). It will automatically shutdown after ttl_seconds.
    """
    file_dir, filename = os.path.split(file_path)
    port = _find_free_port()
    host = '127.0.0.1'

    class SingleFileHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            # only serve exact filename at root: /filename
            if self.path != f'/{filename}':
                self.send_response(404)
                self.end_headers()
                return
            try:
                fs = os.path.getsize(file_path)
                self.send_response(200)
                # basic mime detection
                ext = os.path.splitext(filename)[1].lower()
                if ext in ['.mp4', '.m4v']:
                    ctype = 'video/mp4'
                elif ext in ['.webm']:
                    ctype = 'video/webm'
                else:
                    ctype = 'application/octet-stream'
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(fs))
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.end_headers()
                with open(file_path, 'rb') as fh:
                    shutil.copyfileobj(fh, self.wfile)
            except Exception as e:
                logger.exception("Error serving file")
                try:
                    self.send_response(500)
                    self.end_headers()
                except Exception:
                    pass

        # silence HTTP server logs
        def log_message(self, format, *args):
            logger.debug("HTTP: " + format % args)

    server = HTTPServer((host, port), SingleFileHandler)
    server.allow_reuse_address = True

    def run_server():
        try:
            logger.debug("Starting HTTP server for %s on %s:%s", filename, host, port)
            server.serve_forever()
        except Exception:
            logger.exception("HTTP server stopped")

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    # schedule server shutdown and optional file cleanup
    def shutdown_and_cleanup():
        try:
            logger.debug("Shutting down single-file server for %s", filename)
            server.shutdown()
            server.server_close()
        except Exception:
            logger.exception("Error shutting down server")
        # optional: remove file after TTL (comment out if you want to keep files)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug("Removed served file %s after TTL", file_path)
        except Exception:
            logger.exception("Error removing file after TTL")

    timer = threading.Timer(ttl_seconds, shutdown_and_cleanup)
    timer.daemon = True
    timer.start()

    url = f"http://{host}:{port}/{filename}"
    return url, thread, server

# ---------- Streamlit UI ----------

def main():
    st.set_page_config(page_title="Private YT Downloader (local-serve)", layout="centered")
    st.title("Private YouTube Downloader — local serve to avoid 403s")
    st.write("This app downloads via yt-dlp locally and serves the file over `localhost` with a short TTL so browser downloads never hit expired YouTube URLs.")

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

    if st.button("Download Video"):
        if not url:
            st.error("Please enter a valid URL.")
            return

        st.info(f"Downloading {platform} video with yt-dlp...")
        with st.spinner("Downloading..."):
            result = download_video_to_path(url, platform, itag)

        if "error" in result:
            st.error(f"Error: {result['error']}")
            return

        file_path = result["file_path"]
        st.success("Video downloaded to server disk.")
        logger.debug("File available at: %s", file_path)

        # Display preview and then start local server to serve the file
        try:
            st.video(file_path)
        except Exception:
            st.warning("Unable to preview video in Streamlit UI (depends on video format).")

        st.info("Starting short-lived local HTTP server to serve this file to your browser.")
        url, thread, server = start_single_file_server(file_path, ttl_seconds=300)  # 5 minutes TTL
        st.write("Download link (valid for ~5 minutes):")
        st.markdown(f"[⬇️ Download from local server]({url})", unsafe_allow_html=True)
        st.write("If the link does not start the download automatically, right-click → Save link as...")

        st.warning("Server runs on localhost only. The file will be removed after the TTL (default 5 min).")

        # Optionally give a manual stop button
        if st.button("Stop local server and remove file now"):
            try:
                server.shutdown()
                server.server_close()
            except Exception:
                logger.exception("Failed to shut down server manually")
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                logger.exception("Failed to remove file manually")
            st.success("Server stopped and file removed.")

if __name__ == "__main__":
    main()