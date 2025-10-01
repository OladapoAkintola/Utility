import os
import re
import streamlit as st
import yt_dlp
import requests
import tempfile
from PIL import Image
from io import BytesIO
from mutagen.id3 import (
    ID3, APIC, TIT2, TPE1, TALB, TPE2, TRCK, TCON, TDRC, ID3NoHeaderError
)

def sanitize_filename(s):
    return re.sub(r'[\\/*?:"<>|]', "", s)

def search_youtube(query, max_results=5):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'skip_download': True,
        'extract_flat': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
    return result.get('entries', [])

def download_audio(video_url, video_id):
    """Download audio into a temporary file and return its path + info."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_file.close()

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'outtmpl': temp_file.name.replace(".mp3", ".%(ext)s"),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0'
        }]
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)

    return temp_file.name, info

def embed_metadata(file_path, info, metadata_inputs):
    try:
        audio = ID3(file_path)
    except ID3NoHeaderError:
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
        except Exception as e:
            st.warning(f"Could not fetch cover art: {e}")

    audio.save(file_path)

def display_thumbnail(thumbnail_url, title):
    try:
        resp = requests.get(thumbnail_url, timeout=10)
        img = Image.open(BytesIO(resp.content))
        st.image(img, caption=title, use_column_width=True)
    except Exception as e:
        st.warning(f"Thumbnail not available: {e}")

def main():
    st.title("🎶 Max Utility - MP3 Downloader")

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

            video_url = vid.get('url') or vid.get('webpage_url')
            st.video(video_url)

            video_id = vid.get('id')

            if st.button(f"⬇️ Download '{vid.get('title')}'", key=f"download_{video_id}"):
                with st.spinner("Downloading audio..."):
                    try:
                        file_path, info = download_audio(video_url, video_id)
                    except Exception as e:
                        st.error(f"Download failed: {e}")
                        continue

                metadata_inputs = {
                    'title': title,
                    'artist': artist,
                    'album': album or None,
                    'album_artist': album_artist or None,
                    'track_number': track_number or None,
                    'genre': genre or None,
                    'year': year or None
                }
                embed_metadata(file_path, info or vid, metadata_inputs)
                st.success(f"Downloaded & tagged: {title} - {artist}")

                with open(file_path, 'rb') as f:
                    st.download_button(
                        "⬇️ Save MP3",
                        f,
                        file_name=f"{sanitize_filename(title)} - {sanitize_filename(artist)}.mp3",
                        mime="audio/mpeg",
                        key=f"save_{video_id}"
                    )

if __name__ == "__main__":
    main()