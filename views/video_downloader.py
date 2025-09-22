import streamlit as st
import yt_dlp as ytdlp
import io
import os
import re
import requests
import tempfile
import shutil
import subprocess
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


def sanitize_filename(s: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", s)


def make_output_template(platform: str, ext: str = "mp4") -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{BASE_FILE_NAME}-{platform}-{timestamp}.{ext}"


def fetch_youtube_formats(url: str):
    """Fetch available video/audio formats for YouTube."""
    ydl_opts = {'quiet': True, 'http_headers': HEADERS}
    with ytdlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    # Keep only formats with actual URL
    valid_formats = [f for f in info.get("formats", []) if f.get("url")]
    info["formats"] = valid_formats
    return info


def format_preview_label(fmt: dict) -> str:
    """Generate a readable label for formats."""
    if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
        res = fmt.get('resolution') or fmt.get('format_note') or "unknown"
        return f"{res} ({fmt.get('ext')})"
    elif fmt.get('vcodec') == 'none':
        return f"{fmt.get('abr', 'unknown')} kbps ({fmt.get('ext')})"
    else:
        return f"{fmt.get('ext')}"


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _find_cached_video(platform: str, media_id: str):
    """Return cached video path if exists (any common video extension)."""
    for ext in ("mp4", "mkv", "webm", "mov", "avi"):
        candidate = os.path.join(CACHE_DIR, f"{platform}_{media_id}.{ext}")
        if os.path.exists(candidate):
            return candidate
    return None


def _find_cached_audio(platform: str, media_id: str):
    candidate = os.path.join(CACHE_DIR, f"{platform}_{media_id}.mp3")
    if os.path.exists(candidate):
        return candidate
    return None


def download_video_to_cache(url: str, platform: str, itag: str = None):
    """
    Download a video into cache (if not cached) and return tuple (cache_path, info).
    Uses stable outtmpl '%(id)s.%(ext)s' inside a temp dir, then moves file into cache.
    """
    # --- try to get metadata id for stable caching ---
    try:
        with ytdlp.YoutubeDL({'quiet': True, 'http_headers': HEADERS}) as ydl:
            meta = ydl.extract_info(url, download=False)
            media_id = meta.get('id') or sanitize_filename(url.split("/")[-1])
    except Exception:
        media_id = sanitize_filename(url.split("/")[-1])

    # check cache
    cached = _find_cached_video(platform, media_id)
    if cached:
        try:
            # try to get info from yt-dlp for title etc (non-blocking)
            with ytdlp.YoutubeDL({'quiet': True, 'http_headers': HEADERS}) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception:
            info = {"id": media_id, "title": os.path.basename(cached)}
        return cached, info

    # not cached -> download into temp dir
    temp_dir = tempfile.mkdtemp(prefix="ydl_")
    outtmpl = os.path.join(temp_dir, "%(id)s.%(ext)s")
    ydl_opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'http_headers': HEADERS,
        'noplaylist': True
    }
    if itag:
        ydl_opts['format'] = itag
    else:
        ydl_opts['format'] = 'bestvideo+bestaudio/best'

    try:
        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        # expected filename in temp_dir: {id}.{ext}
        expected = os.path.join(temp_dir, f"{info.get('id')}.{info.get('ext', 'mp4')}")
        final_path = expected if os.path.exists(expected) else None

        # If not found, pick the largest file in temp_dir
        if not final_path:
            candidates = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir)]
            candidates = [p for p in candidates if os.path.isfile(p)]
            if not candidates:
                raise FileNotFoundError("No downloaded file found in temp dir.")
            final_path = max(candidates, key=os.path.getsize)

        # move to cache with stable name
        ext = os.path.splitext(final_path)[1].lstrip('.') or 'mp4'
        cache_path = os.path.join(CACHE_DIR, f"{platform}_{sanitize_filename(info.get('id') or media_id)}.{ext}")
        shutil.move(final_path, cache_path)

        # cleanup temp dir
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            logger.debug("Failed to remove temp dir %s", temp_dir)

        return cache_path, info

    except Exception as e:
        # cleanup on error
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
        logger.error("Video download failed: %s", e)
        raise


def extract_audio_from_video(cache_video_path: str, platform: str, media_id: str):
    """
    Extracts audio (mp3) from a cached video file into cache and returns audio_cache_path.
    Requires ffmpeg. Attempts mp3 encoding; if it fails, raises.
    """
    # check existing audio cache
    existing = _find_cached_audio(platform, media_id)
    if existing:
        return existing

    if not ffmpeg_available():
        raise EnvironmentError("ffmpeg is not installed or not in PATH. Install ffmpeg to enable audio extraction.")

    temp_dir = tempfile.mkdtemp(prefix="extract_")
    try:
        audio_temp = os.path.join(temp_dir, f"{media_id}.mp3")

        # run ffmpeg to extract best audio -> mp3
        cmd = [
            "ffmpeg", "-y",
            "-hide_banner", "-loglevel", "error",
            "-i", cache_video_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-q:a", "2",
            audio_temp
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0 or not os.path.exists(audio_temp):
            # try fallback (ffmpeg default encoder)
            cmd2 = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", cache_video_path, "-vn", "-q:a", "2", audio_temp]
            proc2 = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc2.returncode != 0 or not os.path.exists(audio_temp):
                raise RuntimeError(f"ffmpeg failed to extract audio. stderr: {proc.stderr.decode()}\n{proc2.stderr.decode()}")

        # move to cache
        audio_cache_path = os.path.join(CACHE_DIR, f"{platform}_{sanitize_filename(media_id)}.mp3")
        shutil.move(audio_temp, audio_cache_path)
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
        return audio_cache_path

    except Exception:
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
        raise


# ---------- Streamlit UI ----------
def main():
    st.set_page_config(page_title="Max Utility Downloader", layout="wide")
    st.title("🌐 Max Utility — Multi-Platform Downloader")
    st.write("Supports YouTube, Shorts, X, TikTok, Instagram, Facebook. Threads excluded.")

    if not ffmpeg_available():
        st.warning("⚠️ ffmpeg not found. Audio extraction will fail until ffmpeg is installed and in PATH.")

    platform = st.selectbox("Platform", ["YouTube", "YouTube Shorts", "X", "Facebook", "Instagram", "TikTok"])
    url = st.text_input("Video URL")

    itag = None
    # session keys
    if 'video_cached' not in st.session_state:
        st.session_state['video_cached'] = None  # dict: {'platform','id','path','info'}
    if 'audio_cached' not in st.session_state:
        st.session_state['audio_cached'] = None  # dict: {'platform','id','path'}

    # Fetch and show video format options only when user hasn't downloaded the video yet
    if platform in ["YouTube", "YouTube Shorts"] and url.strip() and not st.session_state['video_cached']:
        st.info("Fetching YouTube formats...")
        try:
            info = fetch_youtube_formats(url.strip())
        except Exception as e:
            st.error(f"Failed to fetch formats: {e}")
            info = None

        if info:
            video_itags = {}
            for fmt in info.get('formats', []):
                if 'format_id' not in fmt:
                    continue
                if fmt.get('vcodec') != 'none':
                    label = format_preview_label(fmt)
                    if label not in video_itags.values():
                        video_itags[fmt['format_id']] = label

            st.subheader("Video Preview (will appear after download)")
            if info.get("thumbnail"):
                try:
                    thumb_resp = requests.get(info["thumbnail"], timeout=10)
                    st.image(thumb_resp.content, caption=info.get("title"), use_container_width=True)
                except Exception:
                    pass

            if video_itags:
                itag = st.radio("Select Video Format (optional)", list(video_itags.keys()), format_func=lambda x: video_itags[x])

    # Download Video button (always shown)
    if st.button("⬇️ Download Video"):
        if not url.strip():
            st.error("Please enter a valid URL.")
        else:
            try:
                with st.spinner("Downloading video — this may take a moment..."):
                    cache_path, info = download_video_to_cache(url.strip(), platform, itag)
                media_id = info.get('id') or sanitize_filename(url.split("/")[-1])
                st.session_state['video_cached'] = {'platform': platform, 'id': media_id, 'path': cache_path, 'info': info}
                st.success("Video downloaded and cached.")
            except Exception as e:
                st.error(f"Download failed: {e}")
                st.session_state['video_cached'] = None

    # If we have a downloaded video in session, show preview and options
    if st.session_state.get('video_cached'):
        vc = st.session_state['video_cached']
        st.subheader(f"Preview — {vc['info'].get('title', os.path.basename(vc['path']))}")
        try:
            # read bytes and show video preview
            with open(vc['path'], "rb") as vf:
                video_bytes = vf.read()
            st.video(video_bytes)
        except Exception as e:
            st.error(f"Could not show preview: {e}")

        # Show Save Video download button
        st.download_button(
            label="💾 Save Video",
            data=video_bytes,
            file_name=os.path.basename(vc['path']),
            mime="video/mp4"
        )

        # Extract Audio button
        if st.button("🎵 Extract Audio from Video"):
            try:
                with st.spinner("Extracting audio (mp3)..."):
                    audio_path = extract_audio_from_video(vc['path'], vc['platform'], vc['id'])
                # store in session
                st.session_state['audio_cached'] = {'platform': vc['platform'], 'id': vc['id'], 'path': audio_path}
                st.success("Audio extracted and cached.")
            except EnvironmentError as env_e:
                st.error(str(env_e))
            except Exception as e:
                st.error(f"Audio extraction failed: {e}")

    # If audio has been extracted/cached, show preview and save button
    if st.session_state.get('audio_cached'):
        ac = st.session_state['audio_cached']
        st.subheader("Audio Preview")
        try:
            with open(ac['path'], "rb") as af:
                audio_bytes = af.read()
            st.audio(audio_bytes, format="audio/mp3")
            st.download_button(
                label="💾 Save Audio",
                data=audio_bytes,
                file_name=os.path.basename(ac['path']),
                mime="audio/mpeg"
            )
        except Exception as e:
            st.error(f"Could not show audio: {e}")

    # Optional: Clear session / cache controls
    st.markdown("---")
    colc1, colc2 = st.columns(2)
    with colc1:
        if st.button("🧹 Clear session (video + audio)"):
            st.session_state['video_cached'] = None
            st.session_state['audio_cached'] = None
            st.success("Session cleared.")
    with colc2:
        if st.button("🗑️ Purge cache older than 24 hours"):
            removed = 0
            now = datetime.now().timestamp()
            for fn in os.listdir(CACHE_DIR):
                fp = os.path.join(CACHE_DIR, fn)
                try:
                    if os.path.isfile(fp):
                        age = now - os.path.getmtime(fp)
                        if age > 24 * 3600:
                            os.remove(fp)
                            removed += 1
                except Exception:
                    pass
            st.success(f"Removed {removed} cached files older than 24 hours.")

if __name__ == "__main__":
    main()