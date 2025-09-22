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


def sanitize_filename(s):
    """Sanitize filename to be filesystem-safe."""
    return re.sub(r'[\\/*?:"<>|]', "", s)


def search_youtube(query, max_results=5):
    """Search YouTube and return metadata for videos."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'skip_download': True,
        'extract_flat': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
    return result.get('entries', [])


def download_audio(video_url, save_path=SAVE_PATH):
    """Download audio if not cached; return local path and info."""
    with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'quiet': True,
                           'postprocessors': [{'key': 'FFmpegExtractAudio',
                                               'preferredcodec': 'mp3',
                                               'preferredquality': '0'}]}) as ydl:
        info = ydl.extract_info(video_url, download=True)
        video_id = info.get('id')
        file_name = sanitize_filename(f"{video_id}.mp3")
        file_path = os.path.join(save_path, file_name)
        return file_path, info


def embed_metadata(file_path, info, metadata_inputs):
    """Embed ID3 tags and cover art using mutagen."""
    audio = ID3()
    audio.add(TIT2(encoding=3, text=metadata_inputs.get('title', info.get('title'))))
    audio.add(TPE1(encoding=3, text=metadata_inputs.get('artist', info.get('uploader'))))

    if metadata_inputs.get('album'):
        audio.add(TALB(encoding=3, text=metadata_inputs['album']))
    if metadata_inputs.get('album_artist'):
        audio.add(TPE2(encoding=3, text=metadata_inputs['album_artist']))
    if metadata_inputs.get('track_number'):
        audio.add(TRCK(encoding=3, text=str(metadata_inputs['track_number'])))
    if metadata_inputs.get('genre'):
        audio.add(TCON(encoding=3, text=metadata_inputs['genre']))
    if metadata_inputs.get('year'):
        audio.add(TDRC(encoding=3, text=str(metadata_inputs['year'])))

    thumbnail_url = info.get('thumbnail')
    if thumbnail_url:
        try:
            resp = requests.get(thumbnail_url, timeout=10)
            if resp.status_code == 200:
                audio.add(APIC(
                    encoding=3,
                    mime=resp.headers.get('Content-Type', 'image/jpeg'),
                    type=3,
                    desc='Cover',
                    data=resp.content
                ))
        except Exception:
            st.warning("Could not fetch cover art.")
    audio.save(file_path)


def display_thumbnail(thumbnail_url, title):
    try:
        resp = requests.get(thumbnail_url, timeout=10)
        img = Image.open(resp.content if hasattr(resp, "content") else resp.raw)
        st.image(img, caption=title, use_column_width=True)
    except Exception:
        st.warning("Thumbnail not available.")


def main():
    st.title("🎶 MP3 Downloader with Previews & Cache")

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

    if st.button("🔍 Search & Preview"):
        if not title or not artist:
            st.error("Please enter both song title and artist name.")
            return

        query = f"{title} {artist}"
        st.info("Searching YouTube...")
        results = search_youtube(query)
        if not results:
            st.warning("No results found.")
            return

        st.success(f"Found {len(results)} results. Preview below:")

        for idx, vid in enumerate(results, start=1):
            st.subheader(f"{idx}. {vid.get('title')}")
            if vid.get('thumbnail'):
                display_thumbnail(vid['thumbnail'], vid['title'])

            # Use YouTube embed for preview
            st.video(vid['url'])

            # Prepare cached file path
            video_id = vid.get('id')
            cached_file = os.path.join(CACHE_PATH, sanitize_filename(f"{video_id}.mp3"))

            if st.button(f"⬇️ Download '{vid.get('title')}'", key=vid['url']):
                if os.path.exists(cached_file):
                    st.success("Using cached audio file.")
                    file_path = cached_file
                    info = vid
                else:
                    with st.spinner("Downloading audio..."):
                        try:
                            file_path, info = download_audio(vid['url'], save_path=CACHE_PATH)
                        except Exception as e:
                            st.error(f"Download failed: {e}")
                            continue

                # Embed metadata
                metadata_inputs = {
                    'title': title,
                    'artist': artist,
                    'album': album or None,
                    'album_artist': album_artist or None,
                    'track_number': track_number or None,
                    'genre': genre or None,
                    'year': year or None
                }
                embed_metadata(file_path, info, metadata_inputs)
                st.success(f"Downloaded & tagged: {info['title']}")

                # Provide download button
                with open(file_path, 'rb') as f:
                    st.download_button("⬇️ Download MP3", f, file_name=os.path.basename(file_path), mime="audio/mpeg")


if __name__ == "__main__":
    main()