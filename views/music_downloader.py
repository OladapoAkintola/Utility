import streamlit as st
import yt_dlp as youtube_dl
import os
import urllib.parse
import requests
from bs4 import BeautifulSoup

# Ensure the download folder exists
def ensure_folder_exists(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

# Function to search YouTube for a song
def search_youtube(song_name):
    query = urllib.parse.quote(song_name)  # Encode the search query
    search_url = f"https://www.youtube.com/results?search_query={query}"
    
    response = requests.get(search_url)
    if response.status_code != 200:
        return None
    
    soup = BeautifulSoup(response.text, "html.parser")
    video_links = soup.find_all("a", href=True)
    
    for link in video_links:
        if "/watch?v=" in link["href"]:
            return f"https://www.youtube.com{link['href']}"
    
    return None

# Function to download the audio
def download_audio(youtube_url):
    download_folder = "music_downloads"
    ensure_folder_exists(download_folder)
    
    file_name = "song.mp3"
    file_path = os.path.join(download_folder, file_name)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": file_path,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": False,
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

    return file_path

# Streamlit UI
st.title("🎵 YouTube Music Downloader")
st.write("Enter a song name, and we'll find and download it as an audio file!")

song_name = st.text_input("Enter song name:")

if st.button("Search & Download"):
    if not song_name.strip():
        st.error("Please enter a valid song name.")
    else:
        st.info("Searching for the song")
        
        youtube_url = search_youtube(song_name.strip())

        if youtube_url:
            st.success(f"Found the song! Downloading from: {youtube_url}")
            
            with st.spinner("Downloading..."):
                file_path = download_audio(youtube_url)
            
            if file_path:
                st.success("Download complete! 🎶")
                st.audio(file_path)

                with open(file_path, "rb") as file:
                    audio_bytes = file.read()
                
                st.download_button(
                    label="⬇️ Download MP3",
                    data=audio_bytes,
                    file_name="song.mp3",
                    mime="audio/mpeg"
                )
            else:
                st.error("Failed to download audio.")
        else:
            st.error("Could not find the song")


