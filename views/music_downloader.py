import os
import streamlit as st
import yt_dlp

# Ensure the download folder exists
SAVE_PATH = "downloads"
os.makedirs(SAVE_PATH, exist_ok=True)

def download_best_audio_as_mp3(query, save_path=SAVE_PATH):
    """
    Uses yt_dlp to search for the query on YouTube (using ytsearch)
    and downloads the best audio as an MP3 file.
    """
    ydl_opts = {
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0',  # '0' means best quality, as determined by the source
        }],
        'quiet': True,  # Suppress console output for a cleaner streamlit experience
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Use ytsearch1 to search for the first matching video
        result = ydl.extract_info(f"ytsearch1:{query}", download=True)
    return result

def main():
    st.title("YouTube Audio Downloader")
    
    song = st.text_input("Enter a song name to search on YouTube:")
    
    if st.button("Download"):
        if not song:
            st.error("Please enter a song name.")
            return
        
        with st.spinner("Searching and downloading..."):
            try:
                info = download_best_audio_as_mp3(song)
                
                # The search returns an 'entries' list containing the search results
                if 'entries' in info and info['entries']:
                    video_info = info['entries'][0]
                    file_name = f"{video_info['title']}.mp3"
                    file_path = os.path.join(SAVE_PATH, file_name)
                    
                    # Confirm that file was downloaded
                    if os.path.exists(file_path):
                        st.success(f"Download completed: {file_name}")
                        
                        # Open the file and offer it for download
                        with open(file_path, "rb") as f:
                            st.download_button("Download MP3", data=f, file_name=file_name, mime="audio/mpeg")
                    else:
                        st.error("File not found. Something went wrong during the download.")
                else:
                    st.error("No results found for your query.")
            except Exception as e:
                st.error(f"An error occurred: {e}")

main()
