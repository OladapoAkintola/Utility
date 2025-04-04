import os
import streamlit as st
import yt_dlp
from PIL import Image
import requests
from io import BytesIO

# Ensure the download folder exists
SAVE_PATH = "downloads"
os.makedirs(SAVE_PATH, exist_ok=True)

def search_and_download(query, save_path=SAVE_PATH):
    """
    Uses yt_dlp to search YouTube for the given query or directly download if it's a URL.
    If YouTube fails, attempts a SoundCloud search.
    Returns video info and file path.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0',
        }],
        'quiet': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # If the query looks like a URL, use it directly; otherwise, search YouTube
            if 'youtube.com' in query or 'youtu.be' in query:
                result = ydl.extract_info(query, download=True)
            else:
                result = ydl.extract_info(f"ytsearch1:{query}", download=True)
        except yt_dlp.utils.DownloadError as e:
            st.warning("YouTube download/search failed, trying SoundCloud...")
            try:
                result = ydl.extract_info(f"scsearch1:{query}", download=True)
            except yt_dlp.utils.DownloadError as e_sc:
                raise yt_dlp.utils.DownloadError(f"Both YouTube and SoundCloud searches failed: {e_sc}")
    
    if 'entries' in result:
        video_info = result['entries'][0]
    else:
        video_info = result

    file_name = f"{video_info['title']}.mp3"
    file_path = os.path.join(save_path, file_name)
    return video_info, file_path

def display_thumbnail(thumbnail_url, title):
    """
    Fetch and display the thumbnail image.
    """
    try:
        response = requests.get(thumbnail_url, timeout=10)
        response.raise_for_status()  # Raise an error for HTTP issues
        img = Image.open(BytesIO(response.content))
        st.image(img, caption=title, use_column_width=True)
    except Exception as e:
        st.warning(f"Could not load thumbnail: {e}")

def provide_download_button(file_path, file_name):
    """
    Provide a download button for the MP3 file.
    """
    try:
        with open(file_path, "rb") as f:
            st.download_button("Download MP3", data=f, file_name=file_name, mime="audio/mpeg")
    except Exception as e:
        st.error(f"Error providing download button: {e}")

def main():
    st.title("Music Downloader")
    # Collect song and artist input from the user
    song = st.text_input("Enter the song name:")
    artist = st.text_input("Enter the artist name:")
    
    if st.button("Search & Download"):
        if not song or not artist:
            st.error("Please enter both the song name and the artist name.")
            return
        
        # Build the query from the song and artist names
        query = f"{song} {artist}"
        
        with st.spinner("Searching and downloading..."):
            try:
                info, file_path = search_and_download(query)
                if os.path.exists(file_path):
                    st.success(f"Downloaded: {info['title']}")
                    
                    # Display thumbnail if available
                    if 'thumbnail' in info and info['thumbnail']:
                        display_thumbnail(info['thumbnail'], info['title'])
                    
                    # Provide download button
                    provide_download_button(file_path, os.path.basename(file_path))
                else:
                    st.error("Download failed. Try again.")
            except yt_dlp.utils.DownloadError as e:
                st.error(f"Download error: {e}")
            except requests.exceptions.RequestException as e:
                st.error(f"Network error: {e}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")


main()
