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
        for entry in entries:
            entry['source'] = 'SoundCloud'
        return entries, None
    except Exception as e:
        return [], str(e)


def search_bandcamp(query, max_results=5):
    """Search Bandcamp and return metadata."""
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"bcsearch{max_results}:{query}", download=False)
        entries = result.get("entries", [])
        for entry in entries:
            entry['source'] = 'Bandcamp'
        return entries, None
    except Exception as e:
        return [], str(e)


def search_bilibili(query, max_results=5):
    """Search Bilibili and return metadata."""
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"bilisearch{max_results}:{query}", download=False)
        entries = result.get("entries", [])
        for entry in entries:
            entry['source'] = 'Bilibili'
        return entries, None
    except Exception as e:
        return [], str(e)


def search_niconico(query, max_results=5):
    """Search Niconico and return metadata."""
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"nicosearch{max_results}:{query}", download=False)
        entries = result.get("entries", [])
        for entry in entries:
            entry['source'] = 'Niconico'
        return entries, None
    except Exception as e:
        return [], str(e)


def download_from_url(url):
    """
    Download audio from a direct URL (TikTok, Instagram, Twitter, etc.)
    Returns video info without downloading.
    """
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "skip_download": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return info, None
    except Exception as e:
        return None, str(e)


def detect_platform(url):
    """Detect the platform from URL."""
    url_lower = url.lower()
    if 'tiktok.com' in url_lower or 'vm.tiktok.com' in url_lower:
        return 'TikTok', '🎬'
    elif 'instagram.com' in url_lower:
        return 'Instagram', '📷'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        return 'Twitter/X', '🐦'
    elif 'facebook.com' in url_lower or 'fb.watch' in url_lower:
        return 'Facebook', '👥'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'YouTube', '🎥'
    elif 'soundcloud.com' in url_lower:
        return 'SoundCloud', '🎵'
    elif 'bandcamp.com' in url_lower:
        return 'Bandcamp', '🎸'
    elif 'bilibili.com' in url_lower:
        return 'Bilibili', '📺'
    elif 'nicovideo.jp' in url_lower:
        return 'Niconico', '🎌'
    elif 'twitch.tv' in url_lower:
        return 'Twitch', '🟣'
    elif 'reddit.com' in url_lower:
        return 'Reddit', '🔴'
    elif 'vimeo.com' in url_lower:
        return 'Vimeo', '🎞️'
    else:
        return 'Unknown', '🌐'


def search_all_sources(query, max_results=5, selected_sources=None):
    """Search selected sources and combine results."""
    all_results = []
    errors = []

    if selected_sources is None:
        selected_sources = ['YouTube', 'SoundCloud', 'Bandcamp']

    # Search YouTube
    if 'YouTube' in selected_sources:
        with st.spinner("🔍 Searching YouTube..."):
            yt_results, yt_error = search_youtube(query, max_results)
            if yt_results:
                for entry in yt_results:
                    entry['source'] = 'YouTube'
                all_results.extend(yt_results)
            if yt_error:
                errors.append(f"YouTube: {yt_error}")

    # Search SoundCloud
    if 'SoundCloud' in selected_sources:
        with st.spinner("🔍 Searching SoundCloud..."):
            sc_results, sc_error = search_soundcloud(query, max_results)
            if sc_results:
                all_results.extend(sc_results)
            if sc_error:
                errors.append(f"SoundCloud: {sc_error}")

    # Search Bandcamp
    if 'Bandcamp' in selected_sources:
        with st.spinner("🔍 Searching Bandcamp..."):
            bc_results, bc_error = search_bandcamp(query, max_results)
            if bc_results:
                all_results.extend(bc_results)
            if bc_error:
                errors.append(f"Bandcamp: {bc_error}")

    # Search Bilibili
    if 'Bilibili' in selected_sources:
        with st.spinner("🔍 Searching Bilibili..."):
            bili_results, bili_error = search_bilibili(query, max_results)
            if bili_results:
                all_results.extend(bili_results)
            if bili_error:
                errors.append(f"Bilibili: {bili_error}")

    # Search Niconico
    if 'Niconico' in selected_sources:
        with st.spinner("🔍 Searching Niconico..."):
            nico_results, nico_error = search_niconico(query, max_results)
            if nico_results:
                all_results.extend(nico_results)
            if nico_error:
                errors.append(f"Niconico: {nico_error}")

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
        return "❌ This content is unavailable or has been removed."
    elif "private" in error_lower:
        return "❌ This content is private and cannot be downloaded."
    elif "copyright" in error_lower or "blocked" in error_lower:
        return "❌ This content is blocked due to copyright restrictions."
    elif "age" in error_lower and "restricted" in error_lower:
        return "❌ This content is age-restricted and cannot be downloaded."
    elif "live" in error_lower:
        return "❌ Live streams cannot be downloaded."
    elif "geographic" in error_lower or "not available in your country" in error_lower:
        return "❌ This content is not available in your region."
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


def embed_metadata(file_path, video_info, user_metadata, file_format):
    """Embed metadata into audio file."""
    try:
        if file_format == "mp3":
            try:
                audio = ID3(file_path)
            except:
                audio = ID3()

            # Set metadata
            if user_metadata.get("title"):
                audio.add(TIT2(encoding=3, text=user_metadata["title"]))
            elif video_info.get("title"):
                audio.add(TIT2(encoding=3, text=video_info["title"]))

            if user_metadata.get("artist"):
                audio.add(TPE1(encoding=3, text=user_metadata["artist"]))
            elif video_info.get("uploader"):
                audio.add(TPE1(encoding=3, text=video_info["uploader"]))

            if user_metadata.get("album"):
                audio.add(TALB(encoding=3, text=user_metadata["album"]))

            if user_metadata.get("album_artist"):
                audio.add(TPE2(encoding=3, text=user_metadata["album_artist"]))

            if user_metadata.get("track_number"):
                audio.add(TRCK(encoding=3, text=str(user_metadata["track_number"])))

            if user_metadata.get("genre"):
                audio.add(TCON(encoding=3, text=user_metadata["genre"]))

            if user_metadata.get("year"):
                audio.add(TDRC(encoding=3, text=str(user_metadata["year"])))

            # Add thumbnail as cover art
            thumbnail_url = video_info.get("thumbnail")
            if thumbnail_url:
                try:
                    resp = requests.get(thumbnail_url, timeout=10)
                    audio.add(APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,
                        desc='Cover',
                        data=resp.content
                    ))
                except:
                    pass

            audio.save(file_path)
            return True, None

        elif file_format == "m4a":
            audio = MP4(file_path)

            if user_metadata.get("title"):
                audio["\xa9nam"] = user_metadata["title"]
            elif video_info.get("title"):
                audio["\xa9nam"] = video_info["title"]

            if user_metadata.get("artist"):
                audio["\xa9ART"] = user_metadata["artist"]
            elif video_info.get("uploader"):
                audio["\xa9ART"] = video_info["uploader"]

            if user_metadata.get("album"):
                audio["\xa9alb"] = user_metadata["album"]

            if user_metadata.get("album_artist"):
                audio["aART"] = user_metadata["album_artist"]

            if user_metadata.get("genre"):
                audio["\xa9gen"] = user_metadata["genre"]

            if user_metadata.get("year"):
                audio["\xa9day"] = str(user_metadata["year"])

            if user_metadata.get("track_number"):
                try:
                    track_num = int(user_metadata["track_number"])
                    audio["trkn"] = [(track_num, 0)]
                except:
                    pass

            # Add cover art
            thumbnail_url = video_info.get("thumbnail")
            if thumbnail_url:
                try:
                    resp = requests.get(thumbnail_url, timeout=10)
                    audio["covr"] = [MP4Cover(resp.content, imageformat=MP4Cover.FORMAT_JPEG)]
                except:
                    pass

            audio.save()
            return True, None

        else:
            return False, "Unsupported format for metadata embedding"

    except Exception as e:
        return False, str(e)


def download_with_retry_and_progress(video_info, user_metadata, max_retries=3):
    """Download with retry logic and progress display."""
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(percent, message="Downloading..."):
        progress_bar.progress(percent)
        status_text.info(f"📥 {message}")

    for attempt in range(max_retries):
        try:
            status_text.info(f"📥 Attempt {attempt + 1}/{max_retries}...")
            
            video_url = video_info.get("url") or video_info.get("webpage_url")
            video_id = video_info.get("id", "unknown")
            
            file_path, info, fmt, error = download_audio(
                video_url,
                video_id,
                progress_callback=update_progress
            )

            if file_path:
                progress_bar.progress(1.0)
                status_text.success("✅ Download complete!")
                time.sleep(0.5)
                progress_bar.empty()
                status_text.empty()
                return file_path, fmt, info, None
            elif error:
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


def get_source_emoji(source):
    """Get emoji for source platform."""
    emoji_map = {
        'YouTube': '🎥',
        'SoundCloud': '🎵',
        'Bandcamp': '🎸',
        'Bilibili': '📺',
        'Niconico': '🎌'
    }
    return emoji_map.get(source, '🌐')


def main():
    st.title("🎶 Max Utility - Universal Audio Downloader")
    st.caption("Search multiple platforms or download from direct URLs!")

    # Initialize session state
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'url_result' not in st.session_state:
        st.session_state.url_result = None
    if 'metadata' not in st.session_state:
        st.session_state.metadata = {}
    if 'search_errors' not in st.session_state:
        st.session_state.search_errors = []

    # Create tabs for different download methods
    tab1, tab2 = st.tabs(["🔍 Search Multiple Platforms", "🔗 Direct URL Download"])

    # Tab 1: Search
    with tab1:
        st.markdown("### Select Search Sources")
        col_sources = st.columns(3)
        
        with col_sources[0]:
            search_youtube = st.checkbox("🎥 YouTube", value=True)
            search_soundcloud = st.checkbox("🎵 SoundCloud", value=True)
        with col_sources[1]:
            search_bandcamp = st.checkbox("🎸 Bandcamp", value=True)
            search_bilibili = st.checkbox("📺 Bilibili", value=False)
        with col_sources[2]:
            search_niconico = st.checkbox("🎌 Niconico", value=False)
        
        st.divider()
        
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

        if st.button("🔍 Search Selected Sources"):
            if not title or not artist:
                st.error("Please enter both song title and artist name.")
            else:
                # Build list of selected sources
                selected_sources = []
                if search_youtube:
                    selected_sources.append('YouTube')
                if search_soundcloud:
                    selected_sources.append('SoundCloud')
                if search_bandcamp:
                    selected_sources.append('Bandcamp')
                if search_bilibili:
                    selected_sources.append('Bilibili')
                if search_niconico:
                    selected_sources.append('Niconico')
                
                if not selected_sources:
                    st.error("Please select at least one source to search.")
                else:
                    query = f"{title} {artist}"
                    results, errors = search_all_sources(query, max_results=5, selected_sources=selected_sources)

                    st.session_state.search_errors = errors

                    if not results:
                        st.error("❌ No results found from any source.")
                        if errors:
                            with st.expander("View Error Details"):
                                for error in errors:
                                    st.text(error)
                    else:
                        st.session_state.search_results = results
                        st.session_state.url_result = None  # Clear URL results
                        st.success(f"✅ Found {len(results)} results from {len(selected_sources)} source(s)")

                        if errors:
                            with st.expander("⚠️ Some sources had issues"):
                                for error in errors:
                                    st.warning(error)

        # Display search results
        if st.session_state.search_results:
            st.divider()

            for idx, vid in enumerate(st.session_state.search_results, start=1):
                source = vid.get('source', 'Unknown')
                source_emoji = get_source_emoji(source)

                col_left, col_right = st.columns([3, 1])

                with col_left:
                    st.subheader(f"{idx}. {vid.get('title')}")
                    st.caption(f"{source_emoji} {source} • {vid.get('uploader', 'Unknown uploader')}")

                with col_right:
                    video_id = vid.get("id")
                    if st.button("⬇️ Download", key=f"download_search_{video_id}"):
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
                                    key=f"save_search_{video_id}"
                                )

                        # Reset trigger
                        st.session_state[f"download_triggered_{video_id}"] = False

                st.divider()

    # Tab 2: Direct URL
    with tab2:
        st.markdown("""
        ### Supported Platforms for Direct URL:
        - 🎬 **TikTok** (videos and sounds)
        - 📷 **Instagram** (posts, reels, stories)
        - 🐦 **Twitter/X** (videos)
        - 👥 **Facebook** (videos)
        - 🟣 **Twitch** (clips and VODs)
        - 🔴 **Reddit** (videos)
        - 🎞️ **Vimeo** (videos)
        - And 1000+ more sites!
        """)

        url_input = st.text_input("Enter URL", placeholder="https://www.tiktok.com/@username/video/...")
        
        col1, col2 = st.columns(2)
        with col1:
            url_title = st.text_input("Custom Title (optional)", key="url_title")
            url_artist = st.text_input("Custom Artist (optional)", key="url_artist")
        with col2:
            url_album = st.text_input("Custom Album (optional)", key="url_album")
            url_genre = st.text_input("Custom Genre (optional)", key="url_genre")

        if st.button("🔗 Get Audio Info"):
            if not url_input:
                st.error("Please enter a URL.")
            else:
                with st.spinner("🔍 Fetching content info..."):
                    info, error = download_from_url(url_input)
                    
                    if error:
                        st.error(f"❌ Failed to fetch content: {get_error_message(error)}")
                    elif info:
                        st.session_state.url_result = info
                        st.session_state.search_results = None  # Clear search results
                        
                        platform, emoji = detect_platform(url_input)
                        st.success(f"✅ Found content from {emoji} {platform}")
                        
                        # Store custom metadata
                        st.session_state.metadata = {
                            "title": url_title or info.get("title"),
                            "artist": url_artist or info.get("uploader") or info.get("creator"),
                            "album": url_album or None,
                            "album_artist": None,
                            "track_number": None,
                            "genre": url_genre or None,
                            "year": None
                        }

        # Display URL result
        if st.session_state.url_result:
            st.divider()
            
            info = st.session_state.url_result
            platform, emoji = detect_platform(url_input)
            
            col_left, col_right = st.columns([3, 1])
            
            with col_left:
                st.subheader(info.get("title", "Unknown Title"))
                uploader = info.get("uploader") or info.get("creator") or "Unknown"
                st.caption(f"{emoji} {platform} • {uploader}")
            
            with col_right:
                if st.button("⬇️ Download Audio", key="download_url"):
                    st.session_state["download_triggered_url"] = True

            # Show thumbnail
            if info.get("thumbnail"):
                display_thumbnail(info["thumbnail"], info.get("title", ""))

            # Handle download
            if st.session_state.get("download_triggered_url", False):
                with st.container():
                    file_path, fmt, download_info, error = download_with_retry_and_progress(
                        info,
                        st.session_state.metadata
                    )

                    if error:
                        st.error(error)
                    elif file_path:
                        # Embed metadata
                        if fmt in ["mp3", "m4a"]:
                            with st.spinner("Adding metadata..."):
                                success, meta_error = embed_metadata(
                                    file_path,
                                    download_info,
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
                            "opus": "audio/opus",
                            "mp4": "audio/mp4"
                        }

                        with open(file_path, "rb") as f:
                            st.download_button(
                                f"💾 Save {fmt.upper()} File",
                                f,
                                file_name=os.path.basename(file_path),
                                mime=mime_types.get(fmt, "audio/mpeg"),
                                key="save_url"
                            )

                    # Reset trigger
                    st.session_state["download_triggered_url"] = False

    # Sidebar info
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown("""
        **Features:**
        - 🔍 Multi-platform search
        - 🔗 Direct URL download
        - 🎵 Multiple format support
        - 🏷️ Automatic metadata tagging
        - 💾 Smart caching
        - 🔄 Automatic retry on failure
        - 📊 Progress tracking
        
        **Searchable Platforms:**
        - 🎥 YouTube
        - 🎵 SoundCloud
        - 🎸 Bandcamp (indie music)
        - 📺 Bilibili (Chinese content)
        - 🎌 Niconico (Japanese content)
        
        **URL-Only Platforms:**
        - TikTok, Instagram, Twitter/X
        - Facebook, Twitch, Reddit
        - Vimeo, and 1000+ more!
        
        **Tips:**
        - Bandcamp is great for indie/underground music
        - Bilibili has lots of anime/Asian content
        - Use URL tab for social media content
        - MP3/M4A support full metadata
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
