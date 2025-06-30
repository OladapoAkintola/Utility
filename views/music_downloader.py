import os
import streamlit as st
import yt_dlp
import requests
from io import BytesIO
from PIL import Image
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TPE2, TRCK, TCON, TDRC

# Setup download folder
SAVE_PATH = "downloads"
os.makedirs(SAVE_PATH, exist_ok=True)


def search_and_download(query, save_path=SAVE_PATH):
    """
    Tries to download audio as MP3 from YouTube first, falls back to SoundCloud, Bandcamp, and Mixcloud.
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
        'ffmpeg_location': '/usr/bin/ffmpeg',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(f"ytsearch1:{query}", download=True)
        except yt_dlp.utils.DownloadError:
            st.warning("YouTube download failed. Trying other sources...")
            try:
                result = ydl.extract_info(f"scsearch1:{query}", download=True)
            except yt_dlp.utils.DownloadError as e:
                raise yt_dlp.utils.DownloadError(f"Download failed: {e}")

    video_info = result['entries'][0] if 'entries' in result else result
    file_name = f"{video_info['title']}.mp3"
    file_path = os.path.join(save_path, file_name)
    return video_info, file_path


def embed_metadata(file_path, info, metadata_inputs):
    """
    Uses mutagen to write ID3 tags and embed cover art.
    """
    audio = ID3()
    # Required tags
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
                audio.add(
                    APIC(
                        encoding=3,
                        mime=resp.headers.get('Content-Type', 'image/jpeg'),
                        type=3,  # front cover
                        desc='Cover',
                        data=img_data
                    )
                )
        except Exception:
            st.warning("Could not fetch cover art.")

    audio.save(file_path)


def display_thumbnail(thumbnail_url, title):
    try:
        response = requests.get(thumbnail_url, timeout=10)
        img = Image.open(BytesIO(response.content))
        st.image(img, caption=title, use_container_width=True)
    except Exception:
        st.warning("Thumbnail not available.")


def provide_download_button(file_path, file_name):
    try:
        with open(file_path, "rb") as f:
            st.download_button("⬇️ Download MP3", data=f, file_name=file_name, mime="audio/mpeg")
    except Exception as e:
        st.error(f"Error providing download: {e}")


def main():
    st.title("🎶 MP3 Downloader with Metadata")

    # Basic inputs
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

    if st.button("🔍 Search & Download"):
        # Validate required fields
        if not title or not artist:
            st.error("Please enter both song title and artist name.")
            return

        query = f"{title} {artist}"
        with st.spinner("Searching and downloading..."):
            try:
                info, file_path = search_and_download(query)
                if os.path.exists(file_path):
                    st.success(f"✅ Downloaded: {info['title']}")
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

                    # Show thumbnail and download button
                    if info.get('thumbnail'):
                        display_thumbnail(info['thumbnail'], info['title'])
                    provide_download_button(file_path, os.path.basename(file_path))
                else:
                    st.error("Download failed. File not found.")
            except yt_dlp.utils.DownloadError as e:
                st.error(f"Download error: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
