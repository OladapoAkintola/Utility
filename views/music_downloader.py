import os
import re
import streamlit as st
import yt_dlp
import requests
from PIL import Image
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TPE2, TRCK, TCON, TDRC

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
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
    return result.get("entries", [])


def download_audio(video_url, video_id, save_path=SAVE_PATH):
    """
    Download audio with fallback:
    - Try MP3 conversion.
    - If fails, fallback to original WebM.
    """
    file_name_mp3 = sanitize_filename(f"{video_id}.mp3")
    file_name_webm = sanitize_filename(f"{video_id}.webm")
    file_path_mp3 = os.path.join(save_path, file_name_mp3)
    file_path_webm = os.path.join(save_path, file_name_webm)

    # Try MP3 first
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "outtmpl": os.path.join(save_path, f"{video_id}.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0"
            }],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
        return file_path_mp3, info, "mp3"
    except Exception:
        st.warning("⚠️ Conversion failed, saving original WebM.")
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "outtmpl": os.path.join(save_path, f"{video_id}.%(ext)s"),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
        return file_path_webm, info, "webm"


def embed_metadata(file_path, info, metadata_inputs):
    """Embed ID3 tags and cover art using mutagen."""
    try:
        audio = ID3(file_path)
    except Exception:
        audio = ID3()

    audio.add(TIT2(encoding=3, text=metadata_inputs.get("title", info.get("title"))))
    audio.add(TPE1(encoding=3, text=metadata_inputs.get("artist", info.get("uploader"))))

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
        except Exception:
            st.warning("⚠️ Could not fetch cover art.")
    audio.save(file_path)


def display_thumbnail(thumbnail_url, title):
    try:
        resp = requests.get(thumbnail_url, timeout=10, stream=True)
        img = Image.open(resp.raw)
        st.image(img, caption=title, use_container_width=True)
    except Exception:
        st.warning("Thumbnail not available.")


def main():
    st.title("🎶 Max Utility - Audio Downloader")

    # Initialize session state
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'metadata' not in st.session_state:
        st.session_state.metadata = {}

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

    if st.button("🔍 Search & Preview"):
        if not title or not artist:
            st.error("Please enter both song title and artist name.")
            return

        query = f"{title} {artist}"
        st.info("Searching YouTube...")
        results = search_youtube(query)
        
        if not results:
            st.warning("No results found.")
            st.session_state.search_results = None
            return
        
        st.session_state.search_results = results
        st.success(f"Found {len(results)} results. Preview below:")

    # Display results if they exist
    if st.session_state.search_results:
        for idx, vid in enumerate(st.session_state.search_results, start=1):
            st.subheader(f"{idx}. {vid.get('title')}")
            if vid.get("thumbnail"):
                display_thumbnail(vid["thumbnail"], vid["title"])

            st.video(vid["url"])

            video_id = vid.get("id")
            cached_file_mp3 = os.path.join(CACHE_PATH, sanitize_filename(f"{video_id}.mp3"))
            cached_file_webm = os.path.join(CACHE_PATH, sanitize_filename(f"{video_id}.webm"))

            if st.button(f"⬇️ Download", key=f"download_{video_id}"):
                if os.path.exists(cached_file_mp3):
                    st.success("✅ Using cached MP3 file.")
                    file_path, fmt = cached_file_mp3, "mp3"
                    # Re-embed metadata on cached file
                    with st.spinner("Updating metadata..."):
                        # Get full info for metadata
                        ydl_opts = {"quiet": True, "skip_download": True}
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(vid["url"], download=False)
                        embed_metadata(file_path, info, st.session_state.metadata)
                elif os.path.exists(cached_file_webm):
                    st.success("✅ Using cached WebM file.")
                    file_path, fmt = cached_file_webm, "webm"
                    info = vid
                else:
                    with st.spinner("Downloading audio..."):
                        try:
                            file_path, info, fmt = download_audio(vid["url"], video_id, save_path=CACHE_PATH)
                        except Exception as e:
                            st.error(f"❌ Download failed: {e}")
                            continue

                    # Embed metadata if mp3
                    if fmt == "mp3":
                        embed_metadata(file_path, info, st.session_state.metadata)
                        st.success(f"✅ Downloaded & tagged: {info.get('title', 'Unknown')}")
                    else:
                        st.warning("⚠️ Downloaded as WebM (no tagging applied).")

                # Provide download button
                with open(file_path, "rb") as f:
                    st.download_button(
                        f"💾 Save {fmt.upper()} File",
                        f,
                        file_name=os.path.basename(file_path),
                        mime="audio/mpeg" if fmt == "mp3" else "audio/webm",
                        key=f"save_{video_id}"
                    )


if __name__ == "__main__":
    main()