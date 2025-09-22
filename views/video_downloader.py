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
    """Download video into cache and return (cache_path, info)."""
    try:
        with ytdlp.YoutubeDL({'quiet': True, 'http_headers': HEADERS}) as ydl:
            meta = ydl.extract_info(url, download=False)
            media_id = meta.get('id') or sanitize_filename(url.split("/")[-1])
    except Exception:
        media_id = sanitize_filename(url.split("/")[-1])

    cached = _find_cached_video(platform, media_id)
    if cached:
        try:
            with ytdlp.YoutubeDL({'quiet': True, 'http_headers': HEADERS}) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception:
            info = {"id": media_id, "title": os.path.basename(cached)}
        return cached, info

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

        expected = os.path.join(temp_dir, f"{info.get('id')}.{info.get('ext', 'mp4')}")
        final_path = expected if os.path.exists(expected) else None

        if not final_path:
            candidates = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
            if not candidates:
                raise FileNotFoundError("No downloaded file found in temp dir.")
            final_path = max(candidates, key=os.path.getsize)

        ext = os.path.splitext(final_path)[1].lstrip('.') or 'mp4'
        cache_path = os.path.join(CACHE_DIR, f"{platform}_{sanitize_filename(info.get('id') or media_id)}.{ext}")
        shutil.move(final_path, cache_path)

        shutil.rmtree(temp_dir, ignore_errors=True)
        return cache_path, info

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.error("Video download failed: %s", e)
        raise


def extract_audio_from_video(cache_video_path: str, platform: str, media_id: str):
    """Extract mp3 audio from a cached video file."""
    existing = _find_cached_audio(platform, media_id)
    if existing:
        os.remove(existing)  # overwrite to avoid stale cache

    if not ffmpeg_available():
        raise EnvironmentError("ffmpeg is not installed or not in PATH.")

    temp_dir = tempfile.mkdtemp(prefix="extract_")
    try:
        audio_temp = os.path.join(temp_dir, f"{media_id}.mp3")

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
            cmd2 = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", cache_video_path, "-vn", "-q:a", "2", audio_temp]
            proc2 = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc2.returncode != 0 or not os.path.exists(audio_temp):
                raise RuntimeError("ffmpeg failed to extract audio.")

        audio_cache_path = os.path.join(CACHE_DIR, f"{platform}_{sanitize_filename(media_id)}.mp3")
        shutil.move(audio_temp, audio_cache_path)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return audio_cache_path

    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


# --- Session management ---
def clear_video_session():
    st.session_state['video_cached'] = None
    st.session_state['audio_cached'] = None

def clear_audio_session():
    st.session_state['audio_cached'] = None

def ensure_cache_validity():
    if st.session_state.get('video_cached'):
        vc = st.session_state['video_cached']
        if not os.path.exists(vc['path']):
            clear_video_session()
    if st.session_state.get('audio_cached'):
        ac = st.session_state['audio_cached']
        if not os.path.exists(ac['path']):
            clear_audio_session()


# ---------- Streamlit UI ----------
def main():
    
    st.title("🌐 Max Utility — Multi-Platform Downloader")
    st.write("Supports YouTube, Shorts, X, TikTok, Instagram, Facebook. Threads excluded.")

    if not ffmpeg_available():
        st.warning("⚠️ ffmpeg not found. Audio extraction will fail until ffmpeg is installed and in PATH.")

    if 'video_cached' not in st.session_state:
        st.session_state['video_cached'] = None
    if 'audio_cached' not in st.session_state:
        st.session_state['audio_cached'] = None

    ensure_cache_validity()

    platform = st.selectbox("Platform", ["YouTube", "YouTube Shorts", "X", "Facebook", "Instagram", "TikTok"])
    url = st.text_input("Video URL")

    itag = None
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

            st.subheader("Video Preview (after download)")
            if info.get("thumbnail"):
                try:
                    thumb_resp = requests.get(info["thumbnail"], timeout=10)
                    st.image(thumb_resp.content, caption=info.get("title"), use_container_width=True)
                except Exception:
                    pass

            if video_itags:
                itag = st.radio("Select Video Format (optional)",
                                list(video_itags.keys()),
                                format_func=lambda x: video_itags[x])

    if st.button("⬇️ Download Video"):
        if not url.strip():
            st.error("Please enter a valid URL.")
        else:
            try:
                with st.spinner("Downloading video..."):
                    cache_path, info = download_video_to_cache(url.strip(), platform, itag)
                media_id = info.get('id') or sanitize_filename(url.split("/")[-1])
                st.session_state['video_cached'] = {'platform': platform, 'id': media_id, 'path': cache_path, 'info': info}
                st.success("Video downloaded and cached.")
            except Exception as e:
                st.error(f"Download failed: {e}")
                clear_video_session()

    if st.session_state.get('video_cached'):
        vc = st.session_state['video_cached']
        st.subheader(f"Preview — {vc['info'].get('title', os.path.basename(vc['path']))}")
        try:
            with open(vc['path'], "rb") as vf:
                video_bytes = vf.read()
            st.video(video_bytes)
        except Exception as e:
            st.error(f"Could not show preview: {e}")

        st.download_button(
            label="💾 Save Video",
            data=video_bytes,
            file_name=os.path.basename(vc['path']),
            mime="video/mp4"
        )

        if st.button("🎵 Extract Audio from Video"):
            try:
                with st.spinner("Extracting audio..."):
                    audio_path = extract_audio_from_video(vc['path'], vc['platform'], vc['id'])
                st.session_state['audio_cached'] = {'platform': vc['platform'], 'id': vc['id'], 'path': audio_path}
                st.success("Audio extracted and cached.")
            except Exception as e:
                st.error(f"Audio extraction failed: {e}")

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

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 Clear session (video + audio)"):
            clear_video_session()
            st.success("Session cleared.")
    with col2:
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
            ensure_cache_validity()
            st.success(f"Removed {removed} cached files older than 24 hours.")


if __name__ == "__main__":
    main()