import os
import re
import streamlit as st
import yt_dlp
import requests
import time
from PIL import Image
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TPE2, TRCK, TCON, TDRC
from mutagen.mp4 import MP4, MP4Cover

# Setup folders
SAVE_PATH = "downloads"
CACHE_PATH = "cache"
os.makedirs(SAVE_PATH, exist_ok=True)
os.makedirs(CACHE_PATH, exist_ok=True)


def sanitize_filename(s: str) -> str:
    """Sanitize filename to be filesystem-safe."""
    return re.sub(r'[\/*?:"<>|]', "", s)


def search_youtube(query, max_results=5):
    """Search YouTube and return metadata for videos."""
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        return result.get("entries", []), None
    except Exception as e:
        return [], str(e)


def search_soundcloud(query, max_results=5):
    """Search SoundCloud and return metadata."""
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"scsearch{max_results}:{query}", download=False)
        entries = result.get("entries", [])
        # Mark entries as SoundCloud
        for entry in entries:
            entry['source'] = 'SoundCloud'
        return entries, None
    except Exception as e:
        return [], str(e)


def search_all_sources(query, max_results=5):
    """Search all available sources and combine results."""
    all_results = []
    errors = []
    
    # Search YouTube
    with st.spinner("🔍 Searching YouTube..."):
        yt_results, yt_error = search_youtube(query, max_results)
        if yt_results:
            for entry in yt_results:
                entry['source'] = 'YouTube'
            all_results.extend(yt_results)
        if yt_error:
            errors.append(f"YouTube: {yt_error}")
    
    # Search SoundCloud
    with st.spinner("🔍 Searching SoundCloud..."):
        sc_results, sc_error = search_soundcloud(query, max_results)
        if sc_results:
            all_results.extend(sc_results)
        if sc_error:
            errors.append(f"SoundCloud: {sc_error}")
    
    return all_results, errors


def download_audio(video_url, video_id, save_path=SAVE_PATH, progress_callback=None):
    """
    Download audio with multiple format fallbacks and progress tracking.
    """
    file_name_mp3 = sanitize_filename(f"{video_id}.mp3")
    file_name_m4a = sanitize_filename(f"{video_id}.m4a")
    file_name_webm = sanitize_filename(f"{video_id}.webm")
    file_path_mp3 = os.path.join(save_path, file_name_mp3)
    file_path_m4a = os.path.join(save_path, file_name_m4a)
    file_path_webm = os.path.join(save_path, file_name_webm)

    def progress_hook(d):
        if progress_callback and d['status'] == 'downloading':
            try:
                percent = d.get('_percent_str', '0%').strip().replace('%', '')
                progress_callback(float(percent) / 100)
            except:
                pass

    # Strategy 1: Try MP3 conversion
    try:
        if progress_callback:
            progress_callback(0.1, "Converting to MP3...")
        
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "outtmpl": os.path.join(save_path, f"{video_id}.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0"
            }],
            "progress_hooks": [progress_hook],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
        
        if os.path.exists(file_path_mp3):
            return file_path_mp3, info, "mp3", None
    except Exception as e:
        error_msg = str(e)
        if "ffmpeg" in error_msg.lower() or "avconv" in error_msg.lower():
            if progress_callback:
                progress_callback(0.3, "FFmpeg not available, trying M4A...")
        else:
            if progress_callback:
                progress_callback(0.3, f"MP3 failed, trying M4A...")

    # Strategy 2: Try M4A conversion
    try:
        if progress_callback:
            progress_callback(0.4, "Converting to M4A...")
        
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio",
            "quiet": True,
            "no_warnings": True,
            "outtmpl": os.path.join(save_path, f"{video_id}.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
            }],
            "progress_hooks": [progress_hook],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
        
        if os.path.exists(file_path_m4a):
            return file_path_m4a, info, "m4a", None
    except Exception as e:
        if progress_callback:
            progress_callback(0.6, "M4A failed, downloading original format...")

    # Strategy 3: Download original format (no conversion)
    try:
        if progress_callback:
            progress_callback(0.7, "Downloading original format...")
        
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "outtmpl": os.path.join(save_path, f"{video_id}.%(ext)s"),
            "progress_hooks": [progress_hook],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
        
        # Find the actual downloaded file
        for ext in ['webm', 'opus', 'm4a', 'mp4', 'mp3']:
            potential_path = os.path.join(save_path, f"{video_id}.{ext}")
            if os.path.exists(potential_path):
                return potential_path, info, ext, None
                
        raise Exception("Could not find downloaded file")
    except Exception as e:
        error_msg = str(e)
        return None, None, None, error_msg


def get_error_message(error_str):
    """Convert technical errors to user-friendly messages."""
    error_lower = error_str.lower()
    
    if "unavailable" in error_lower or "video unavailable" in error_lower:
        return "❌ This video is unavailable or has been removed."
    elif "private" in error_lower:
        return "❌ This video is private and cannot be downloaded."
    elif "copyright" in error_lower or "blocked" in error_lower:
        return "❌ This video is blocked due to copyright restrictions."
    elif "age" in error_lower and "restricted" in error_lower:
        return "❌ This video is age-restricted and cannot be downloaded."
    elif "live" in error_lower:
        return "❌ Live streams cannot be downloaded."
    elif "geographic" in error_lower or "not available in your country" in error_lower:
        return "❌ This video is not available in your region."
    elif "network" in error_lower or "connection" in error_lower:
        return "⚠️ Network error. Please check your connection and try again."
    elif "timeout" in error_lower:
        return "⚠️ Request timed out. Please try again."
    elif "ffmpeg" in error_lower or "avconv" in error_lower:
        return "⚠️ Audio conversion tools not found. Downloading original format instead."
    elif "429" in error_str or "rate limit" in error_lower:
        return "⚠️ Too many requests. Please wait a moment and try again."
    else:
        return f"❌ Download failed: {error_str[:150]}"


def embed_metadata_mp3(file_path, info, metadata_inputs):
    """Embed ID3 tags and cover art for MP3 files."""
    try:
        try:
            audio = ID3(file_path)
        except Exception:
            audio = ID3()

        audio.add(TIT2(encoding=3, text=metadata_inputs.get("title", info.get("title", "Unknown"))))
        audio.add(TPE1(encoding=3, text=metadata_inputs.get("artist", info.get("uploader", "Unknown"))))

        if metadata_inputs.get("album"):
            audio.add(TALB(encoding=3, text=metadata_inputs["album"]))
        if metadata_inputs.get("album_artist"):
            audio.add(TPE2(encoding=3, text=metadata_inputs["album_artist"]))
        if metadata_inputs.get("track_number"):
            audio.add(TRCK(encoding=3, text=str(metadata_inputs["track_number"])))
        if metadata_inputs.get("genre"):
            audio.add(TCON(encoding=3, text=metadata_inputs["genre"]))
        if metadata_inputs.get("year"):
            audio.add(TDRC(encoding=3, text=str(metadata_inputs["year"])))

        thumbnail_url = info.get("thumbnail")
        if thumbnail_url:
            try:
                resp = requests.get(thumbnail_url, timeout=10)
                if resp.status_code == 200:
                    audio.add(APIC(
                        encoding=3,
                        mime=resp.headers.get("Content-Type", "image/jpeg"),
                        type=3,
                        desc="Cover",
                        data=resp.content
                    ))
            except:
                pass
        
        audio.save(file_path)
        return True, None
    except Exception as e:
        return False, str(e)


def embed_metadata_m4a(file_path, info, metadata_inputs):
    """Embed metadata for M4A files."""
    try:
        audio = MP4(file_path)
        
        audio["\xa9nam"] = metadata_inputs.get("title", info.get("title", "Unknown"))
        audio["\xa9ART"] = metadata_inputs.get("artist", info.get("uploader", "Unknown"))
        
        if metadata_inputs.get("album"):
            audio["\xa9alb"] = metadata_inputs["album"]
        if metadata_inputs.get("album_artist"):
            audio["aART"] = metadata_inputs["album_artist"]
        if metadata_inputs.get("genre"):
            audio["\xa9gen"] = metadata_inputs["genre"]
        if metadata_inputs.get("year"):
            audio["\xa9day"] = str(metadata_inputs["year"])
        if metadata_inputs.get("track_number"):
            audio["trkn"] = [(int(metadata_inputs["track_number"]), 0)]

        thumbnail_url = info.get("thumbnail")
        if thumbnail_url:
            try:
                resp = requests.get(thumbnail_url, timeout=10)
                if resp.status_code == 200:
                    audio["covr"] = [MP4Cover(resp.content, imageformat=MP4Cover.FORMAT_JPEG)]
            except:
                pass
        
        audio.save()
        return True, None
    except Exception as e:
        return False, str(e)


def embed_metadata(file_path, info, metadata_inputs, fmt):
    """Embed metadata based on file format."""
    if fmt == "mp3":
        return embed_metadata_mp3(file_path, info, metadata_inputs)
    elif fmt == "m4a":
        return embed_metadata_m4a(file_path, info, metadata_inputs)
    else:
        return False, f"{fmt.upper()} format does not support metadata embedding"


def download_with_retry_and_progress(vid, metadata_inputs, max_retries=3):
    """Download with retry logic, progress tracking, and graceful degradation."""
    video_id = vid.get("id")
    source = vid.get("source", "YouTube")
    
    # Check cache first
    cached_files = {
        'mp3': os.path.join(CACHE_PATH, sanitize_filename(f"{video_id}.mp3")),
        'm4a': os.path.join(CACHE_PATH, sanitize_filename(f"{video_id}.m4a")),
        'webm': os.path.join(CACHE_PATH, sanitize_filename(f"{video_id}.webm")),
        'opus': os.path.join(CACHE_PATH, sanitize_filename(f"{video_id}.opus")),
    }
    
    for fmt, path in cached_files.items():
        if os.path.exists(path):
            st.success(f"✅ Using cached {fmt.upper()} file from {source}")
            
            # Try to fetch full info for metadata update
            try:
                ydl_opts = {"quiet": True, "skip_download": True, "no_warnings": True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(vid["url"], download=False)
            except:
                info = vid
            
            # Update metadata on cached file
            if fmt in ["mp3", "m4a"]:
                with st.spinner("Updating metadata..."):
                    success, error = embed_metadata(path, info, metadata_inputs, fmt)
                    if not success:
                        st.warning(f"⚠️ Could not update metadata: {error}")
            
            return path, fmt, info, None
    
    # Create progress indicators
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Try downloading with retry
    for attempt in range(max_retries):
        try:
            status_text.info(f"📥 Attempt {attempt + 1}/{max_retries}: Starting download from {source}...")
            
            def update_progress(value, message=None):
                progress_bar.progress(min(value, 1.0))
                if message:
                    status_text.info(f"📥 {message}")
            
            file_path, info, fmt, error = download_audio(
                vid["url"], 
                video_id, 
                save_path=CACHE_PATH,
                progress_callback=update_progress
            )
            
            if file_path:
                progress_bar.progress(1.0)
                status_text.success(f"✅ Downloaded as {fmt.upper()}")
                time.sleep(0.5)  # Brief pause to show completion
                progress_bar.empty()
                status_text.empty()
                return file_path, fmt, info, None
            else:
                # Handle error
                user_error = get_error_message(error)
                
                # Check if error is retryable
                if any(keyword in error.lower() for keyword in ["network", "timeout", "connection", "429"]):
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        status_text.warning(f"{user_error} Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                
                # Non-retryable error
                progress_bar.empty()
                status_text.empty()
                return None, None, None, user_error
                
        except Exception as e:
            error_str = str(e)
            user_error = get_error_message(error_str)
            
            # Check if retryable
            if attempt < max_retries - 1 and any(keyword in error_str.lower() for keyword in ["network", "timeout", "connection"]):
                wait_time = 2 ** attempt
                status_text.warning(f"{user_error} Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                progress_bar.empty()
                status_text.empty()
                return None, None, None, user_error
    
    progress_bar.empty()
    status_text.empty()
    return None, None, None, "❌ All download attempts failed"


def display_thumbnail(thumbnail_url, title):
    try:
        resp = requests.get(thumbnail_url, timeout=10, stream=True)
        img = Image.open(resp.raw)
        st.image(img, caption=title, use_container_width=True)
    except Exception:
        st.info("🖼️ Thumbnail not available")


def main():
    st.title("🎶 Max Utility - Audio Downloader")
    st.caption("Search and download from YouTube & SoundCloud")

    # Initialize session state
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'metadata' not in st.session_state:
        st.session_state.metadata = {}
    if 'search_errors' not in st.session_state:
        st.session_state.search_errors = []

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

    # Store metadata in session state
    st.session_state.metadata = {
        "title": title,
        "artist": artist,
        "album": album or None,
        "album_artist": album_artist or None,
        "track_number": track_number or None,
        "genre": genre or None,
        "year": year or None
    }

    if st.button("🔍 Search All Sources"):
        if not title or not artist:
            st.error("Please enter both song title and artist name.")
            return

        query = f"{title} {artist}"
        results, errors = search_all_sources(query, max_results=5)
        
        st.session_state.search_errors = errors
        
        if not results:
            st.error("❌ No results found from any source.")
            if errors:
                with st.expander("View Error Details"):
                    for error in errors:
                        st.text(error)
            return
        
        st.session_state.search_results = results
        st.success(f"✅ Found {len(results)} results from multiple sources")
        
        if errors:
            with st.expander("⚠️ Some sources had issues"):
                for error in errors:
                    st.warning(error)

    # Display results if they exist
    if st.session_state.search_results:
        st.divider()
        
        for idx, vid in enumerate(st.session_state.search_results, start=1):
            source = vid.get('source', 'Unknown')
            source_emoji = "🎥" if source == "YouTube" else "🎵"
            
            col_left, col_right = st.columns([3, 1])
            
            with col_left:
                st.subheader(f"{idx}. {vid.get('title')}")
                st.caption(f"{source_emoji} {source} • {vid.get('uploader', 'Unknown uploader')}")
            
            with col_right:
                video_id = vid.get("id")
                if st.button("⬇️ Download", key=f"download_{video_id}"):
                    st.session_state[f"download_triggered_{video_id}"] = True
            
            # Show thumbnail
            if vid.get("thumbnail"):
                display_thumbnail(vid["thumbnail"], vid["title"])
            
            # Show video preview (only for YouTube)
            if source == "YouTube":
                try:
                    st.video(vid["url"])
                except:
                    st.caption("Video preview unavailable")
            
            # Handle download if triggered
            if st.session_state.get(f"download_triggered_{video_id}", False):
                with st.container():
                    file_path, fmt, info, error = download_with_retry_and_progress(
                        vid, 
                        st.session_state.metadata
                    )
                    
                    if error:
                        st.error(error)
                        st.info("💡 Try selecting a different result from the search.")
                    elif file_path:
                        # Embed metadata
                        if fmt in ["mp3", "m4a"]:
                            with st.spinner("Adding metadata..."):
                                success, meta_error = embed_metadata(
                                    file_path, 
                                    info, 
                                    st.session_state.metadata,
                                    fmt
                                )
                                if success:
                                    st.success(f"✅ Successfully downloaded & tagged as {fmt.upper()}")
                                else:
                                    st.warning(f"⚠️ Downloaded as {fmt.upper()} but metadata failed: {meta_error}")
                        else:
                            st.info(f"ℹ️ Downloaded as {fmt.upper()} (metadata not supported for this format)")
                        
                        # Provide download button
                        mime_types = {
                            "mp3": "audio/mpeg",
                            "m4a": "audio/mp4",
                            "webm": "audio/webm",
                            "opus": "audio/opus"
                        }
                        
                        with open(file_path, "rb") as f:
                            st.download_button(
                                f"💾 Save {fmt.upper()} File",
                                f,
                                file_name=os.path.basename(file_path),
                                mime=mime_types.get(fmt, "audio/mpeg"),
                                key=f"save_{video_id}"
                            )
                    
                    # Reset trigger
                    st.session_state[f"download_triggered_{video_id}"] = False
            
            st.divider()

    # Sidebar info
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown("""
        **Features:**
        - 🔍 Multi-source search (YouTube & SoundCloud)
        - 🎵 Multiple format support (MP3, M4A, WebM)
        - 🏷️ Automatic metadata tagging
        - 💾 Smart caching
        - 🔄 Automatic retry on failure
        - 📊 Progress tracking
        
        **Tips:**
        - If YouTube fails, try SoundCloud results
        - MP3/M4A support full metadata
        - WebM is used as fallback format
        """)
        
        st.header("⚙️ System Status")
        try:
            import subprocess
            result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True, timeout=5)
            st.success(f"✅ yt-dlp: {result.stdout.strip()}")
        except:
            st.warning("⚠️ yt-dlp version check failed")
        
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            st.success("✅ FFmpeg: Available")
        except:
            st.warning("⚠️ FFmpeg not found (conversions may fail)")


if __name__ == "__main__":
    main()