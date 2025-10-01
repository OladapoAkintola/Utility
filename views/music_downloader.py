
import os
import re
import tempfile
import shutil
import subprocess
from datetime import datetime
import logging
import io

import streamlit as st
import yt_dlp as ytdlp
import requests
from PIL import Image
from io import BytesIO
from mutagen.id3 import (
    ID3, APIC, TIT2, TPE1, TALB, TPE2, TRCK, TCON, TDRC, ID3NoHeaderError
)

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

# -------------------- Utilities --------------------
def sanitize_filename(s: str) -> str:
    if not s:
        return ""
    return re.sub(r'[\\/*?:"<>|]', "", s)


def make_output_template(platform: str, ext: str = "mp4") -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{BASE_FILE_NAME}-{platform}-{timestamp}.{ext}"


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


# -------------------- YT Search / Fetch --------------------
def search_youtube(query: str, max_results: int = 5):
    """Search YouTube and return flat results (id, title, thumbnail, webpage_url)."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'http_headers': HEADERS,
        'extract_flat': True,
        'skip_download': True,
    }
    with ytdlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            return info.get('entries', []) if info else []
        except Exception as e:
            logger.error("YouTube search failed: %s", e)
            raise


# -------------------- Download video to cache --------------------
def download_video_to_cache(url: str, platform: str, itag: str = None):
    """Download video into cache and return (cache_path, info)."""
    # Attempt to fetch metadata first to determine id
    media_id = None
    try:
        with ytdlp.YoutubeDL({'quiet': True, 'http_headers': HEADERS}) as ydl:
            meta = ydl.extract_info(url, download=False)
            media_id = meta.get('id') or sanitize_filename(url.split("/")[-1])
    except Exception:
        media_id = sanitize_filename(url.split("/")[-1])

    # Check cached copies
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
            candidates = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
                          if os.path.isfile(os.path.join(temp_dir, f))]
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


# -------------------- Extract audio with ffmpeg --------------------
def extract_audio_from_video(cache_video_path: str, platform: str, media_id: str):
    """Extract mp3 audio from a cached video file into the cache and return path."""
    existing = _find_cached_audio(platform, media_id)
    if existing:
        # Overwrite existing to avoid stale tags
        try:
            os.remove(existing)
        except Exception:
            pass

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
            # Fallback command style
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


# -------------------- ID3 tagging --------------------
def embed_metadata(file_path: str, info: dict, metadata_inputs: dict):
    """Embed ID3 tags and cover art using mutagen."""
    try:
        audio = ID3(file_path)
    except ID3NoHeaderError:
        audio = ID3()

    title_text = metadata_inputs.get('title') or info.get('title') or ""
    artist_text = metadata_inputs.get('artist') or info.get('uploader') or ""

    audio.delall("TIT2")
    audio.delall("TPE1")
    audio.add(TIT2(encoding=3, text=title_text))
    audio.add(TPE1(encoding=3, text=artist_text))

    if metadata_inputs.get('album'):
        audio.delall("TALB")
        audio.add(TALB(encoding=3, text=metadata_inputs['album']))
    if metadata_inputs.get('album_artist'):
        audio.delall("TPE2")
        audio.add(TPE2(encoding=3, text=metadata_inputs['album_artist']))
    if metadata_inputs.get('track_number'):
        audio.delall("TRCK")
        audio.add(TRCK(encoding=3, text=str(metadata_inputs['track_number'])))
    if metadata_inputs.get('genre'):
        audio.delall("TCON")
        audio.add(TCON(encoding=3, text=metadata_inputs['genre']))
    if metadata_inputs.get('year'):
        audio.delall("TDRC")
        audio.add(TDRC(encoding=3, text=str(metadata_inputs['year'])))

    # Cover art
    thumbnail_url = info.get('thumbnail')
    if thumbnail_url:
        try:
            resp = requests.get(thumbnail_url, timeout=10, headers=HEADERS)
            if resp.status_code == 200:
                # remove existing APIC frames before adding
                audio.delall("APIC")
                audio.add(APIC(
                    encoding=3,
                    mime=resp.headers.get('Content-Type', 'image/jpeg'),
                    type=3,
                    desc='Cover',
                    data=resp.content
                ))
        except Exception as e:
            logger.warning("Could not fetch cover art: %s", e)
            # continue without cover art

    audio.save(file_path)


# -------------------- Session / validity --------------------
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


# -------------------- UI --------------------
def display_thumbnail(thumbnail_url, title):
    try:
        resp = requests.get(thumbnail_url, timeout=10, headers=HEADERS)
        img = Image.open(BytesIO(resp.content))
        st.image(img, caption=title, use_container_width=True)
    except Exception:
        st.warning("Thumbnail not available.")


def main():
    st.title("🎶 Max Utility — Search → Download MP3 (Cloud-safe)")

    if not ffmpeg_available():
        st.warning("⚠️ ffmpeg not found. Audio extraction will fail until ffmpeg is installed and in PATH.")

    if 'video_cached' not in st.session_state:
        st.session_state['video_cached'] = None
    if 'audio_cached' not in st.session_state:
        st.session_state['audio_cached'] = None

    ensure_cache_validity()

    # Metadata inputs
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("Song Title", placeholder="Required")
        artist = st.text_input("Artist Name", placeholder="Required")
    with col2:
        album = st.text_input("Album")
        album_artist = st.text_input("Album Artist")
        track_number = st.text_input("Track Number")
        genre = st.text_input("Genre")
        year = st.text_input("Year")

    # Search box
    query = st.text_input("Search YouTube (Title + Artist or keywords)")

    if st.button("🔍 Search"):
        if not query.strip():
            st.error("Enter a search query.")
        else:
            try:
                with st.spinner("Searching YouTube..."):
                    results = search_youtube(query.strip(), max_results=6)
                if not results:
                    st.warning("No results found.")
                else:
                    st.session_state['search_results'] = results
            except Exception as e:
                st.error(f"Search failed: {e}")
                st.session_state['search_results'] = None

    results = st.session_state.get('search_results') or []
    for idx, vid in enumerate(results, start=1):
        st.markdown(f"**{idx}. {vid.get('title')}**")
        if vid.get('thumbnail'):
            try:
                display_thumbnail(vid.get('thumbnail'), vid.get('title'))
            except Exception:
                pass

        video_url = vid.get('url') or vid.get('webpage_url') or vid.get('id')
        st.video(video_url)

        video_id = vid.get('id') or sanitize_filename(video_url.split("/")[-1])
        st.write("")  # spacing

        cols = st.columns([1, 1, 2])
        if cols[0].button("⬇️ Download video (cache)", key=f"vdl_{video_id}"):
            # download video into cache (same behavior as reference app)
            try:
                with st.spinner("Downloading video to cache..."):
                    cache_path, info = download_video_to_cache(video_url, "YouTube")
                media_id = info.get('id') or video_id
                st.session_state['video_cached'] = {'platform': "YouTube", 'id': media_id, 'path': cache_path, 'info': info}
                st.success("Video cached.")
            except Exception as e:
                st.error(f"Video download failed: {e}")
                clear_video_session()

        if cols[1].button("🎵 Download MP3 (extract & tag)", key=f"aud_{video_id}"):
            # download video (if needed) then extract audio and tag
            try:
                # ensure video exists in cache
                vc = st.session_state.get('video_cached')
                if not vc or vc.get('id') != video_id or not os.path.exists(vc.get('path', '')):
                    with st.spinner("Downloading video to cache..."):
                        cache_path, info = download_video_to_cache(video_url, "YouTube")
                        media_id = info.get('id') or video_id
                        st.session_state['video_cached'] = {'platform': "YouTube", 'id': media_id, 'path': cache_path, 'info': info}
                        vc = st.session_state['video_cached']

                with st.spinner("Extracting audio (ffmpeg)..."):
                    audio_cache_path = extract_audio_from_video(vc['path'], vc['platform'], vc['id'])
                # embed metadata
                metadata_inputs = {
                    'title': title or None,
                    'artist': artist or None,
                    'album': album or None,
                    'album_artist': album_artist or None,
                    'track_number': track_number or None,
                    'genre': genre or None,
                    'year': year or None
                }
                embed_metadata(audio_cache_path, vc.get('info') or vid, metadata_inputs)
                st.session_state['audio_cached'] = {'platform': vc['platform'], 'id': vc['id'], 'path': audio_cache_path}
                st.success("Audio extracted, tagged and cached.")
            except Exception as e:
                st.error(f"Audio extraction/tagging failed: {e}")
                clear_audio_session()

        # Provide direct download if audio is cached for this id
        ac = st.session_state.get('audio_cached')
        if ac and ac.get('id') == video_id and os.path.exists(ac.get('path', '')):
            try:
                with open(ac['path'], "rb") as af:
                    audio_bytes = af.read()
                display_name = f"{sanitize_filename(title or vid.get('title') or ac['id'])} - {sanitize_filename(artist or 'unknown')}.mp3"
                cols[2].download_button(
                    label="💾 Save MP3",
                    data=audio_bytes,
                    file_name=display_name,
                    mime="audio/mpeg",
                    key=f"save_{video_id}"
                )
            except Exception as e:
                st.error(f"Could not prepare download: {e}")

        st.markdown("---")

    # If a video is cached, show preview + video download
    if st.session_state.get('video_cached'):
        vc = st.session_state['video_cached']
        st.subheader("Cached Video Preview")
        try:
            with open(vc['path'], "rb") as vf:
                video_bytes = vf.read()
            st.video(video_bytes)
            st.download_button(
                label="💾 Save Video",
                data=video_bytes,
                file_name=os.path.basename(vc['path']),
                mime="video/mp4"
            )
        except Exception as e:
            st.error(f"Could not render cached video preview: {e}")

    # Audio preview/download if available
    if st.session_state.get('audio_cached'):
        ac = st.session_state['audio_cached']
        st.subheader("Cached Audio Preview")
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
            st.error(f"Could not render cached audio preview: {e}")

    st.markdown("---")
    st.warning("Cache is temporary. Use the Save buttons to download files you want to keep.")

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