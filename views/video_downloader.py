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

# Platform configuration
PLATFORMS = {
    "YouTube": {"icon": "🎥", "color": "#FF0000"},
    "YouTube Shorts": {"icon": "📱", "color": "#FF0000"},
    "X (Twitter)": {"icon": "🐦", "color": "#1DA1F2"},
    "Facebook": {"icon": "👥", "color": "#4267B2"},
    "Instagram": {"icon": "📷", "color": "#E4405F"},
    "TikTok": {"icon": "🎵", "color": "#000000"},
}


def sanitize_filename(s: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", s)


def make_output_template(platform: str, ext: str = "mp4") -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{BASE_FILE_NAME}-{platform}-{timestamp}.{ext}"


def get_file_size(path: str) -> str:
    """Get human-readable file size."""
    if not os.path.exists(path):
        return "Unknown"
    size = os.path.getsize(path)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def get_video_duration(path: str) -> str:
    """Get video duration using ffprobe."""
    try:
        if not os.path.exists(path):
            return "Unknown"
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
        duration = float(result.stdout.strip())
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return f"{minutes}:{seconds:02d}"
    except:
        return "Unknown"


def fetch_youtube_formats(url: str):
    """Fetch available video/audio formats for YouTube."""
    ydl_opts = {'quiet': True, 'http_headers': HEADERS, 'no_warnings': True}
    with ytdlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    valid_formats = [f for f in info.get("formats", []) if f.get("url")]
    info["formats"] = valid_formats
    return info


def format_preview_label(fmt: dict) -> str:
    """Generate a readable label for formats."""
    if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
        res = fmt.get('resolution') or fmt.get('format_note') or "unknown"
        fps = fmt.get('fps', '')
        fps_str = f" {fps}fps" if fps else ""
        return f"📹 {res}{fps_str} - {fmt.get('ext').upper()}"
    elif fmt.get('vcodec') == 'none':
        abr = fmt.get('abr', 'unknown')
        return f"🎵 Audio {abr} kbps - {fmt.get('ext').upper()}"
    else:
        return f"📹 {fmt.get('ext').upper()}"


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


def download_video_to_cache(url: str, platform: str, itag: str = None, progress_placeholder=None):
    """Download video into cache and return (cache_path, info)."""
    try:
        with ytdlp.YoutubeDL({'quiet': True, 'http_headers': HEADERS, 'no_warnings': True}) as ydl:
            meta = ydl.extract_info(url, download=False)
            media_id = meta.get('id') or sanitize_filename(url.split("/")[-1])
    except Exception:
        media_id = sanitize_filename(url.split("/")[-1])

    cached = _find_cached_video(platform, media_id)
    if cached:
        if progress_placeholder:
            progress_placeholder.success("✅ Using cached video file!")
        try:
            with ytdlp.YoutubeDL({'quiet': True, 'http_headers': HEADERS, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception:
            info = {"id": media_id, "title": os.path.basename(cached)}
        return cached, info

    if progress_placeholder:
        progress_placeholder.info("📥 Downloading video...")

    temp_dir = tempfile.mkdtemp(prefix="ydl_")
    outtmpl = os.path.join(temp_dir, "%(id)s.%(ext)s")
    ydl_opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'http_headers': HEADERS,
        'noplaylist': True,
        'no_warnings': True
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
        
        if progress_placeholder:
            progress_placeholder.success("✅ Video downloaded successfully!")
        
        return cache_path, info

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.error("Video download failed: %s", e)
        if progress_placeholder:
            progress_placeholder.error(f"❌ Download failed: {str(e)[:150]}")
        raise


def extract_audio_from_video(cache_video_path: str, platform: str, media_id: str, progress_placeholder=None):
    """Extract mp3 audio from a cached video file."""
    existing = _find_cached_audio(platform, media_id)
    if existing:
        if progress_placeholder:
            progress_placeholder.success("✅ Using cached audio file!")
        return existing

    if not ffmpeg_available():
        raise EnvironmentError("❌ FFmpeg is not installed or not in PATH.")

    if progress_placeholder:
        progress_placeholder.info("🎵 Extracting audio from video...")

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
                raise RuntimeError("FFmpeg failed to extract audio.")

        audio_cache_path = os.path.join(CACHE_DIR, f"{platform}_{sanitize_filename(media_id)}.mp3")
        shutil.move(audio_temp, audio_cache_path)
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        if progress_placeholder:
            progress_placeholder.success("✅ Audio extracted successfully!")
        
        return audio_cache_path

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if progress_placeholder:
            progress_placeholder.error(f"❌ Audio extraction failed: {str(e)[:150]}")
        raise


def get_cache_stats():
    """Get cache directory statistics."""
    if not os.path.exists(CACHE_DIR):
        return 0, 0, "0 B"
    
    files = [f for f in os.listdir(CACHE_DIR) if os.path.isfile(os.path.join(CACHE_DIR, f))]
    total_size = sum(os.path.getsize(os.path.join(CACHE_DIR, f)) for f in files)
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if total_size < 1024.0:
            size_str = f"{total_size:.1f} {unit}"
            break
        total_size /= 1024.0
    else:
        size_str = f"{total_size:.1f} TB"
    
    return len(files), total_size, size_str


# --- Session management ---
def clear_video_session():
    st.session_state['video_cached'] = None
    st.session_state['audio_cached'] = None
    st.session_state['video_bytes'] = None
    st.session_state['audio_bytes'] = None

def clear_audio_session():
    st.session_state['audio_cached'] = None
    st.session_state['audio_bytes'] = None

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
    #st.set_page_config(
    #    page_title="Multi-Platform Video #Downloader",
        #page_icon="🌐",
        #layout="wide"
    #)

    # Header
    st.title("🌐 Max Utility — Multi-Platform Downloader")
    st.markdown("Download videos from YouTube, X, TikTok, Instagram, Facebook and more!")

    # Initialize session state
    if 'video_cached' not in st.session_state:
        st.session_state['video_cached'] = None
    if 'audio_cached' not in st.session_state:
        st.session_state['audio_cached'] = None
    if 'video_bytes' not in st.session_state:
        st.session_state['video_bytes'] = None
    if 'audio_bytes' not in st.session_state:
        st.session_state['audio_bytes'] = None

    ensure_cache_validity()

    # Sidebar
    with st.sidebar:
        st.header("⚙️ System Status")
        
        # FFmpeg status
        if ffmpeg_available():
            st.success("✅ FFmpeg: Available")
        else:
            st.error("❌ FFmpeg: Not Found")
            
        
        st.divider()
        
        # Cache statistics
        st.header("💾 Cache Statistics")
        file_count, _, size_str = get_cache_stats()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Files", file_count)
        with col2:
            st.metric("Size", size_str)
        
        st.divider()
        
        # Platform info
        st.header("🌍 Supported Platforms")
        for platform, config in PLATFORMS.items():
            st.markdown(f"{config['icon']} {platform}")
        
        st.caption("⚠️ Threads is not supported")
        
        st.divider()
        
        # Cache management
        st.header("🧹 Cache Management")
        st.caption("⚠️ Use with caution")
        
        if st.button("🗑️ Clear All Cache", use_container_width=True):
            removed = 0
            for fn in os.listdir(CACHE_DIR):
                fp = os.path.join(CACHE_DIR, fn)
                try:
                    if os.path.isfile(fp):
                        os.remove(fp)
                        removed += 1
                except Exception:
                    pass
            clear_video_session()
            st.success(f"✅ Removed {removed} files")
            st.rerun()
        
        if st.button("⏰ Clear Old Cache (24h+)", use_container_width=True):
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
            st.success(f"✅ Removed {removed} old files")
            st.rerun()

    # Main content
    st.divider()
    
    # Step 1: Platform and URL
    st.subheader("📍 Step 1: Select Platform & Enter URL")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        platform_options = list(PLATFORMS.keys())
        platform = st.selectbox(
            "Platform",
            platform_options,
            format_func=lambda x: f"{PLATFORMS[x]['icon']} {x}",
            label_visibility="collapsed"
        )
    
    with col2:
        url = st.text_input(
            "Video URL",
            placeholder=f"Paste your {platform} video URL here...",
            label_visibility="collapsed"
        )

    # Format selection for YouTube
    itag = None
    youtube_info = None
    if platform in ["YouTube", "YouTube Shorts"] and url.strip() and not st.session_state.get('video_cached'):
        with st.spinner("🔍 Fetching available formats..."):
            try:
                youtube_info = fetch_youtube_formats(url.strip())
                
                # Show video preview
                if youtube_info.get("thumbnail"):
                    st.subheader("📺 Video Preview")
                    col_img, col_info = st.columns([1, 1])
                    
                    with col_img:
                        try:
                            thumb_resp = requests.get(youtube_info["thumbnail"], timeout=10)
                            st.image(thumb_resp.content, use_container_width=True)
                        except:
                            st.info("Thumbnail unavailable")
                    
                    with col_info:
                        st.write(f"**Title:** {youtube_info.get('title', 'Unknown')}")
                        st.write(f"**Uploader:** {youtube_info.get('uploader', 'Unknown')}")
                        duration = youtube_info.get('duration', 0)
                        if duration:
                            mins = duration // 60
                            secs = duration % 60
                            st.write(f"**Duration:** {mins}:{secs:02d}")
                
                # Format selection
                st.subheader("🎬 Select Video Quality (Optional)")
                
                video_formats = {}
                for fmt in youtube_info.get('formats', []):
                    if 'format_id' not in fmt:
                        continue
                    if fmt.get('vcodec') != 'none':
                        label = format_preview_label(fmt)
                        if label not in video_formats.values():
                            video_formats[fmt['format_id']] = label
                
                if video_formats:
                    # Group by quality
                    st.info("💡 Higher quality = larger file size. Leave default for best quality.")
                    itag = st.radio(
                        "Available formats:",
                        list(video_formats.keys()),
                        format_func=lambda x: video_formats[x],
                        horizontal=False
                    )
            except Exception as e:
                st.error(f"❌ Failed to fetch formats: {str(e)[:150]}")

    # Download button
    st.divider()
    st.subheader("⬇️ Step 2: Download")
    
    progress_placeholder = st.empty()
    
    col_download, col_clear = st.columns([3, 1])
    
    with col_download:
        if st.button("📥 Download Video", use_container_width=True, type="primary"):
            if not url.strip():
                st.error("❌ Please enter a valid URL.")
            else:
                try:
                    cache_path, info = download_video_to_cache(url.strip(), platform, itag, progress_placeholder)
                    media_id = info.get('id') or sanitize_filename(url.split("/")[-1])
                    
                    # Load video bytes
                    with open(cache_path, "rb") as vf:
                        video_bytes = vf.read()
                    
                    st.session_state['video_cached'] = {
                        'platform': platform,
                        'id': media_id,
                        'path': cache_path,
                        'info': info
                    }
                    st.session_state['video_bytes'] = video_bytes
                    st.rerun()
                except Exception as e:
                    progress_placeholder.error(f"❌ Download failed: {str(e)[:150]}")
                    clear_video_session()
    
    with col_clear:
        if st.button("🔄 Reset", use_container_width=True):
            clear_video_session()
            st.rerun()

    # Video preview and download
    if st.session_state.get('video_cached') and st.session_state.get('video_bytes'):
        vc = st.session_state['video_cached']
        video_bytes = st.session_state['video_bytes']
        
        st.divider()
        st.subheader("🎬 Step 3: Preview & Download")
        
        # Video info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Platform", f"{PLATFORMS.get(vc['platform'], {}).get('icon', '📹')} {vc['platform']}")
        with col2:
            st.metric("Duration", get_video_duration(vc['path']))
        with col3:
            st.metric("Size", get_file_size(vc['path']))
        
        # Video title
        st.write(f"**Title:** {vc['info'].get('title', os.path.basename(vc['path']))}")
        
        # Video player
        try:
            st.video(video_bytes)
        except Exception as e:
            st.error(f"❌ Could not show preview: {e}")

        # Download and extract buttons
        col_vid, col_aud = st.columns(2)
        
        with col_vid:
            st.download_button(
                label="💾 Download Video",
                data=video_bytes,
                file_name=os.path.basename(vc['path']),
                mime="video/mp4",
                use_container_width=True,
                type="primary"
            )
        
        with col_aud:
            if st.button("🎵 Extract Audio (MP3)", use_container_width=True):
                try:
                    audio_progress = st.empty()
                    audio_path = extract_audio_from_video(vc['path'], vc['platform'], vc['id'], audio_progress)
                    
                    # Load audio bytes
                    with open(audio_path, "rb") as af:
                        audio_bytes = af.read()
                    
                    st.session_state['audio_cached'] = {
                        'platform': vc['platform'],
                        'id': vc['id'],
                        'path': audio_path
                    }
                    st.session_state['audio_bytes'] = audio_bytes
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Audio extraction failed: {str(e)[:150]}")

    # Audio preview and download
    if st.session_state.get('audio_cached') and st.session_state.get('audio_bytes'):
        ac = st.session_state['audio_cached']
        audio_bytes = st.session_state['audio_bytes']
        
        st.divider()
        st.subheader("🎧 Audio Ready")
        
        # Audio info
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Format", "MP3")
        with col2:
            st.metric("Size", get_file_size(ac['path']))
        
        # Audio player
        try:
            st.audio(audio_bytes, format="audio/mp3")
        except Exception as e:
            st.error(f"❌ Could not play audio: {e}")
        
        # Download button
        st.download_button(
            label="💾 Download Audio (MP3)",
            data=audio_bytes,
            file_name=os.path.basename(ac['path']),
            mime="audio/mpeg",
            use_container_width=True,
            type="primary"
        )

    # Help section
    if not st.session_state.get('video_cached'):
        st.divider()
        with st.expander("💡 How to Use"):
            st.markdown("""
            **Quick Start:**
            1. Select your platform from the dropdown
            2. Paste the video URL
            3. (Optional) For YouTube, select video quality
            4. Click "Download Video"
            5. Preview and download your video
            6. (Optional) Extract audio as MP3
            
            **Tips:**
            - Videos are cached to speed up re-downloads
            - Higher quality = larger file size
            - Audio extraction requires FFmpeg
            - Use cache management to free up space
            
            **Supported:**
            - ✅ YouTube (including Shorts)
            - ✅ X (Twitter)
            - ✅ TikTok
            - ✅ Instagram
            - ✅ Facebook
            - ❌ Threads (not supported)
            """)


if __name__ == "__main__":
    main()