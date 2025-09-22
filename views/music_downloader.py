import os
import streamlit as st
import yt_dlp
import requests
from io import BytesIO
from PIL import Image
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TPE2, TRCK, TCON, TDRC

# Setup download folder
SAVE_PATH = "downloads"
CACHE_PATH = "cache"
os.makedirs(SAVE_PATH, exist_ok=True)
os.makedirs(CACHE_PATH, exist_ok=True)


def search_youtube(query, max_results=5):
    """
    Search YouTube for videos matching query and return info dicts without downloading.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'skip_download': True,
        'extract_flat': True  # Get metadata only
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        except yt_dlp.utils.DownloadError:
            st.warning("YouTube search failed.")
            return []

    return result.get('entries', [])


def download_audio(video_url, save_path=SAVE_PATH):
    """
    Download audio from YouTube video URL and return the local file path.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0',
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        file_name = f"{info['title']}.mp3"
        file_path = os.path.join(save_path, file_name)
        return file_path, info


def embed_metadata(file_path, info, metadata_inputs):
    """
    Embed ID3 tags and cover art using mutagen.
    """
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
                img_data = resp.content
                audio.add(APIC(
                    encoding=3,
                    mime=resp.headers.get('Content-Type', 'image/jpeg'),
                    type=3,
                    desc='Cover',
                    data=img_data
                ))
        except Exception:
            st.warning("Could not fetch cover art.")
    audio.save(file_path)


def display_audio_preview(info):
    """
    Display an audio preview in Streamlit without saving permanently.
    """
    url = info.get('url')
    if not url:
        return
    ydl_opts = {'format': 'bestaudio/best', 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            data = ydl.extract_info(url, download=False)
            audio_url = data['url']
            st.audio(audio_url)
        except Exception as e:
            st.warning(f"Could not generate audio preview: {e}")


def main():
    st.title("🎶 MP3 Downloader with Previews & Metadata Cache")

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

        # Check cache first
        cache_file = os.path.join(CACHE_PATH, f"{query}.txt")
        cached_results = []
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cached_results = [line.strip() for line in f.readlines()]

        if cached_results:
            st.success(f"Loaded {len(cached_results)} cached results")
            results = [{'url': url} for url in cached_results]
        else:
            results = search_youtube(query)
            # Cache the video URLs
            with open(cache_file, 'w') as f:
                for vid in results:
                    f.write(vid['url'] + "\n")

        st.info(f"Found {len(results)} results. Listen and choose to download.")

        for idx, vid in enumerate(results, start=1):
            st.subheader(f"{idx}. {vid.get('title')}")
            display_audio_preview(vid)
            if st.button(f"⬇️ Download '{vid.get('title')}'", key=vid.get('url')):
                with st.spinner("Downloading..."):
                    try:
                        file_path, info = download_audio(vid['url'])
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
                        st.success(f"Downloaded and tagged: {info['title']}")
                        st.download_button("⬇️ Download MP3", file_path, file_name=os.path.basename(file_path), mime="audio/mpeg")
                    except Exception as e:
                        st.error(f"Download failed: {e}")


if __name__ == "__main__":
    main()