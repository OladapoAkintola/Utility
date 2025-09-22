import os
import io
import streamlit as st
import yt_dlp
import requests
from PIL import Image
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TPE2, TRCK, TCON, TDRC

# Setup folders
SAVE_PATH = "downloads"
os.makedirs(SAVE_PATH, exist_ok=True)


def search_youtube(query, max_results=5):
    """Search YouTube for videos matching query and return info dicts without downloading."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'skip_download': True,
        'extract_flat': True,  # Only metadata
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
    return result.get('entries', [])


def get_audio_bytes(video_url):
    """Download audio to BytesIO and return it along with video info."""
    ydl_opts = {'format': 'bestaudio/best', 'quiet': True, 'outtmpl': '%(title)s.%(ext)s'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        audio_file = info['requested_downloads'][0]['filepath']
        with open(audio_file, 'rb') as f:
            audio_bytes = io.BytesIO(f.read())
    return audio_bytes, info, audio_file


def embed_metadata(file_path, info, metadata_inputs):
    """Embed ID3 tags and cover art using mutagen."""
    audio = ID3()
    audio.add(TIT2(encoding=3, text=metadata_inputs.get('title', info.get('title'))))
    audio.add(TPE1(encoding=3, text=metadata_inputs.get('artist', info.get('uploader'))))

    # Optional tags
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

    # Cover art
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
        img = Image.open(io.BytesIO(resp.content))
        st.image(img, caption=title, use_column_width=True)
    except Exception:
        st.warning("Thumbnail not available.")


def main():
    st.title("🎶 MP3 Downloader with Playable Previews")

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
        st.success(f"Found {len(results)} results.")

        for idx, vid in enumerate(results, start=1):
            st.subheader(f"{idx}. {vid.get('title')}")
            display_thumbnail(vid.get('thumbnail', ''), vid.get('title'))

            # Playable preview
            try:
                audio_bytes, info, audio_file = get_audio_bytes(vid['url'])
                st.audio(audio_bytes)
            except Exception as e:
                st.warning(f"Could not generate audio preview: {e}")
                continue

            if st.button(f"⬇️ Download '{vid.get('title')}'", key=vid['url']):
                metadata_inputs = {
                    'title': title,
                    'artist': artist,
                    'album': album or None,
                    'album_artist': album_artist or None,
                    'track_number': track_number or None,
                    'genre': genre or None,
                    'year': year or None
                }
                embed_metadata(audio_file, info, metadata_inputs)
                st.success(f"Downloaded and tagged: {info['title']}")
                with open(audio_file, 'rb') as f:
                    st.download_button("⬇️ Download MP3", f, file_name=os.path.basename(audio_file), mime="audio/mpeg")


if __name__ == "__main__":
    main()