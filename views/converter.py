import streamlit as st
import os
import shutil
import tempfile
import subprocess
from datetime import datetime
from views.video_downloader import sanitize_filename, ffmpeg_available

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

AUDIO_FORMATS = ["mp3", "wav", "aac", "ogg", "flac", "m4a"]
MIME_MAP = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "aac": "audio/aac",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
    "m4a": "audio/mp4",
}


def extract_audio(video_path: str, filename_prefix: str) -> str:
    """Extract audio from a video and return the cached path."""
    if not ffmpeg_available():
        st.error("⚠️ ffmpeg not found. Install it and add to PATH.")
        return None

    temp_dir = tempfile.mkdtemp(prefix="extract_")
    try:
        audio_temp = os.path.join(temp_dir, f"{filename_prefix}.mp3")
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
               "-i", video_path, "-vn", "-acodec", "libmp3lame", "-q:a", "2", audio_temp]
        subprocess.run(cmd, check=True)

        if not os.path.exists(audio_temp):
            raise RuntimeError("FFmpeg failed: output file not created.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cache_path = os.path.join(CACHE_DIR, f"{filename_prefix}_{timestamp}.mp3")
        shutil.move(audio_temp, cache_path)
        return cache_path
    except subprocess.CalledProcessError as e:
        st.error(f"Audio extraction failed: {e}")
        return None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def convert_audio(input_path: str, output_format: str) -> str:
    """Convert audio file to another format."""
    if not ffmpeg_available():
        st.error("⚠️ ffmpeg not found. Install it and add to PATH.")
        return None

    filename_prefix = sanitize_filename(os.path.splitext(os.path.basename(input_path))[0])[:50]
    temp_dir = tempfile.mkdtemp(prefix="convert_")
    try:
        output_temp = os.path.join(temp_dir, f"{filename_prefix}.{output_format}")
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
               "-i", input_path, output_temp]
        subprocess.run(cmd, check=True)

        if not os.path.exists(output_temp):
            raise RuntimeError("FFmpeg failed: output file not created.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cache_path = os.path.join(CACHE_DIR, f"{filename_prefix}_{timestamp}.{output_format}")
        shutil.move(output_temp, cache_path)
        return cache_path
    except subprocess.CalledProcessError as e:
        st.error(f"Conversion failed: {e}")
        return None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    st.title("🎵 Audio Converter & Extractor")
    st.write("Extract audio from video and convert audio to different formats.")

    if 'audio_path' not in st.session_state:
        st.session_state['audio_path'] = None

    uploaded_file = st.file_uploader(
        "Upload a video or audio file",
        type=["mp4", "mov", "mkv", "avi", "mp3", "wav", "ogg", "flac", "m4a"]
    )

    if uploaded_file:
        filename_prefix = sanitize_filename(os.path.splitext(uploaded_file.name)[0])[:50]
        temp_input = os.path.join(tempfile.gettempdir(), f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        with open(temp_input, "wb") as f:
            f.write(uploaded_file.read())

        if uploaded_file.name.lower().endswith(("mp4", "mov", "mkv", "avi")):
            st.info("Extracting audio from video...")
            output_audio = extract_audio(temp_input, filename_prefix)
            if output_audio:
                st.session_state['audio_path'] = output_audio
                st.success("Audio extracted successfully.")
        else:
            st.session_state['audio_path'] = temp_input
            st.success("Audio ready for conversion.")

    if st.session_state.get('audio_path'):
        audio_path = st.session_state['audio_path']
        st.subheader("Preview Audio")
        try:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            st.audio(audio_bytes)
            st.download_button(
                "💾 Download Audio",
                data=audio_bytes,
                file_name=os.path.basename(audio_path),
                mime=MIME_MAP.get(os.path.splitext(audio_path)[1][1:], "audio/mpeg")
            )
        except Exception as e:
            st.error(f"Failed to play/download audio: {e}")

        st.subheader("Convert Audio Format")
        target_format = st.selectbox("Select target format", AUDIO_FORMATS)
        if st.button("🔄 Convert Audio"):
            converted_path = convert_audio(audio_path, target_format)
            if converted_path:
                st.session_state['audio_path'] = converted_path
                st.success(f"Audio converted to {target_format}.")
                with open(converted_path, "rb") as f:
                    converted_bytes = f.read()
                st.audio(converted_bytes)
                st.download_button(
                    "💾 Download Converted Audio",
                    data=converted_bytes,
                    file_name=os.path.basename(converted_path),
                    mime=MIME_MAP.get(target_format, "audio/mpeg")
                )


if __name__ == "__main__":
    main()