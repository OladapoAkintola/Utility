import streamlit as st
import os
import shutil
import tempfile
import subprocess
from datetime import datetime
from views.video_downloader import sanitize_filename, ffmpeg_available

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

AUDIO_FORMATS = {
    "mp3": {"name": "MP3", "icon": "🎵", "desc": "Most compatible, good quality"},
    "wav": {"name": "WAV", "icon": "🎼", "desc": "Lossless, large file size"},
    "aac": {"name": "AAC", "icon": "🎶", "desc": "High quality, smaller size"},
    "ogg": {"name": "OGG", "icon": "🎧", "desc": "Open format, good compression"},
    "flac": {"name": "FLAC", "icon": "💿", "desc": "Lossless compression"},
    "m4a": {"name": "M4A", "icon": "📱", "desc": "Apple devices compatible"},
}

MIME_MAP = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "aac": "audio/aac",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
    "m4a": "audio/mp4",
}


def get_file_size(path: str) -> str:
    """Get human-readable file size."""
    size = os.path.getsize(path)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def get_audio_duration(path: str) -> str:
    """Get audio duration using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return f"{minutes}:{seconds:02d}"
    except:
        return "Unknown"


def extract_audio(video_path: str, filename_prefix: str, progress_placeholder) -> str:
    """Extract audio from a video and return the cached path."""
    if not ffmpeg_available():
        st.error("❌ FFmpeg not found. Please install FFmpeg and add it to your PATH.")
        return None

    temp_dir = tempfile.mkdtemp(prefix="extract_")
    try:
        progress_placeholder.info("🎬 Extracting audio from video...")
        audio_temp = os.path.join(temp_dir, f"{filename_prefix}.mp3")
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
               "-i", video_path, "-vn", "-acodec", "libmp3lame", "-q:a", "2", audio_temp]
        subprocess.run(cmd, check=True)

        if not os.path.exists(audio_temp):
            raise RuntimeError("FFmpeg failed: output file not created.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cache_path = os.path.join(CACHE_DIR, f"{filename_prefix}_{timestamp}.mp3")
        shutil.move(audio_temp, cache_path)
        progress_placeholder.success("✅ Audio extracted successfully!")
        return cache_path
    except subprocess.CalledProcessError as e:
        progress_placeholder.error(f"❌ Audio extraction failed: {e}")
        return None
    except Exception as e:
        progress_placeholder.error(f"❌ Unexpected error: {e}")
        return None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def convert_audio(input_path: str, output_format: str, progress_placeholder) -> str:
    """Convert audio file to another format."""
    if not ffmpeg_available():
        st.error("❌ FFmpeg not found. Please install FFmpeg and add it to your PATH.")
        return None

    filename_prefix = sanitize_filename(os.path.splitext(os.path.basename(input_path))[0])[:50]
    temp_dir = tempfile.mkdtemp(prefix="convert_")
    try:
        progress_placeholder.info(f"🔄 Converting to {output_format.upper()}...")
        output_temp = os.path.join(temp_dir, f"{filename_prefix}.{output_format}")
        
        # Quality settings based on format
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", input_path]
        
        if output_format == "mp3":
            cmd.extend(["-q:a", "2"])  # High quality MP3
        elif output_format == "aac":
            cmd.extend(["-c:a", "aac", "-b:a", "256k"])
        elif output_format == "ogg":
            cmd.extend(["-q:a", "6"])  # Quality 6 for OGG
        
        cmd.append(output_temp)
        subprocess.run(cmd, check=True)

        if not os.path.exists(output_temp):
            raise RuntimeError("FFmpeg failed: output file not created.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cache_path = os.path.join(CACHE_DIR, f"{filename_prefix}_{timestamp}.{output_format}")
        shutil.move(output_temp, cache_path)
        progress_placeholder.success(f"✅ Converted to {output_format.upper()} successfully!")
        return cache_path
    except subprocess.CalledProcessError as e:
        progress_placeholder.error(f"❌ Conversion failed: {e}")
        return None
    except Exception as e:
        progress_placeholder.error(f"❌ Unexpected error: {e}")
        return None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def display_audio_info(audio_path: str):
    """Display audio file information in a nice card."""
    file_size = get_file_size(audio_path)
    duration = get_audio_duration(audio_path)
    file_ext = os.path.splitext(audio_path)[1][1:].upper()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Format", file_ext)
    with col2:
        st.metric("Duration", duration)
    with col3:
        st.metric("File Size", file_size)


def main():
    st.set_page_config(page_title="Audio Converter", page_icon="🎵", layout="wide")
    
    # Header
    st.title("🎵 Audio Converter & Extractor")
    st.markdown("Extract audio from videos and convert between audio formats with ease.")
    
    # Initialize session state
    if 'audio_path' not in st.session_state:
        st.session_state['audio_path'] = None
    if 'original_filename' not in st.session_state:
        st.session_state['original_filename'] = None
    if 'conversion_history' not in st.session_state:
        st.session_state['conversion_history'] = []

    # Check FFmpeg availability
    with st.sidebar:
        st.header("⚙️ System Status")
        if ffmpeg_available():
            st.success("✅ FFmpeg: Available")
        else:
            st.error("❌ FFmpeg: Not Found")
            st.markdown("""
            **Install FFmpeg:**
            - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
            - **Mac**: `brew install ffmpeg`
            - **Linux**: `sudo apt install ffmpeg`
            """)
        
        st.divider()
        st.header("ℹ️ Supported Formats")
        st.markdown("""
        **Video Input:**
        - MP4, MOV, MKV, AVI
        
        **Audio Input/Output:**
        - MP3, WAV, AAC, OGG, FLAC, M4A
        """)
        
        if st.session_state.get('conversion_history'):
            st.divider()
            st.header("📊 Conversion History")
            for i, conv in enumerate(reversed(st.session_state['conversion_history'][-5:]), 1):
                st.caption(f"{i}. {conv}")

    # Main content area
    st.divider()
    
    # Upload section
    st.subheader("📁 Step 1: Upload Your File")
    uploaded_file = st.file_uploader(
        "Drag and drop or click to browse",
        type=["mp4", "mov", "mkv", "avi", "mp3", "wav", "ogg", "flac", "m4a", "aac"],
        help="Upload a video file to extract audio, or an audio file to convert formats"
    )

    progress_placeholder = st.empty()

    if uploaded_file:
        filename_prefix = sanitize_filename(os.path.splitext(uploaded_file.name)[0])[:50]
        st.session_state['original_filename'] = uploaded_file.name
        
        # Show file info
        with st.expander("📄 File Information", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Filename:** {uploaded_file.name}")
                st.write(f"**Size:** {uploaded_file.size / (1024*1024):.2f} MB")
            with col2:
                file_type = "Video" if uploaded_file.name.lower().endswith(("mp4", "mov", "mkv", "avi")) else "Audio"
                st.write(f"**Type:** {file_type}")
        
        temp_input = os.path.join(tempfile.gettempdir(), f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        with st.spinner("📥 Uploading file..."):
            with open(temp_input, "wb") as f:
                f.write(uploaded_file.read())

        # Handle video files (extract audio)
        if uploaded_file.name.lower().endswith(("mp4", "mov", "mkv", "avi")):
            output_audio = extract_audio(temp_input, filename_prefix, progress_placeholder)
            if output_audio:
                st.session_state['audio_path'] = output_audio
                st.session_state['conversion_history'].append(f"Extracted from {uploaded_file.name}")
        else:
            # Handle audio files
            st.session_state['audio_path'] = temp_input
            progress_placeholder.success("✅ Audio file uploaded successfully!")

    # Audio preview and conversion section
    if st.session_state.get('audio_path'):
        audio_path = st.session_state['audio_path']
        
        st.divider()
        st.subheader("🎧 Step 2: Preview & Download")
        
        # Audio info card
        display_audio_info(audio_path)
        
        # Audio player
        try:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            
            st.audio(audio_bytes, format=f"audio/{os.path.splitext(audio_path)[1][1:]}")
            
            # Download current version
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.download_button(
                    "💾 Download Current Audio",
                    data=audio_bytes,
                    file_name=os.path.basename(audio_path),
                    mime=MIME_MAP.get(os.path.splitext(audio_path)[1][1:], "audio/mpeg"),
                    use_container_width=True,
                    type="primary"
                )
        except Exception as e:
            st.error(f"❌ Failed to load audio: {e}")

        # Conversion section
        st.divider()
        st.subheader("🔄 Step 3: Convert Format (Optional)")
        
        # Format selection with cards
        st.write("Choose your target format:")
        
        cols = st.columns(3)
        selected_format = None
        
        for idx, (fmt, info) in enumerate(AUDIO_FORMATS.items()):
            col = cols[idx % 3]
            with col:
                if st.button(
                    f"{info['icon']} {info['name']}\n\n{info['desc']}", 
                    key=f"fmt_{fmt}",
                    use_container_width=True
                ):
                    selected_format = fmt
        
        # Alternative: Dropdown selector
        with st.expander("Or select from dropdown"):
            target_format = st.selectbox(
                "Select target format",
                options=list(AUDIO_FORMATS.keys()),
                format_func=lambda x: f"{AUDIO_FORMATS[x]['icon']} {AUDIO_FORMATS[x]['name']} - {AUDIO_FORMATS[x]['desc']}",
                key="format_dropdown"
            )
            if st.button("🔄 Convert to Selected Format", use_container_width=True):
                selected_format = target_format

        # Perform conversion
        if selected_format:
            current_format = os.path.splitext(audio_path)[1][1:]
            
            if selected_format == current_format:
                st.warning(f"⚠️ File is already in {selected_format.upper()} format!")
            else:
                converted_path = convert_audio(audio_path, selected_format, progress_placeholder)
                
                if converted_path:
                    st.session_state['audio_path'] = converted_path
                    st.session_state['conversion_history'].append(
                        f"{current_format.upper()} → {selected_format.upper()}"
                    )
                    
                    # Show before/after comparison
                    st.success("🎉 Conversion Complete!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Original Size", get_file_size(audio_path), delta=None)
                    with col2:
                        new_size = get_file_size(converted_path)
                        st.metric("New Size", new_size)
                    
                    # Play converted audio
                    st.write("**Preview Converted Audio:**")
                    with open(converted_path, "rb") as f:
                        converted_bytes = f.read()
                    st.audio(converted_bytes, format=f"audio/{selected_format}")
                    
                    # Download converted version
                    st.download_button(
                        f"💾 Download {selected_format.upper()} File",
                        data=converted_bytes,
                        file_name=os.path.basename(converted_path),
                        mime=MIME_MAP.get(selected_format, "audio/mpeg"),
                        use_container_width=True,
                        type="primary"
                    )
                    
                    # Rerun to update display
                    st.rerun()

    # Help section
    if not uploaded_file:
        st.info("👆 Upload a file to get started!")
        
        with st.expander("💡 Quick Start Guide"):
            st.markdown("""
            **For Video Files:**
            1. Upload your video (MP4, MOV, MKV, AVI)
            2. Audio will be automatically extracted as MP3
            3. Download or convert to another format
            
            **For Audio Files:**
            1. Upload your audio file
            2. Preview the audio
            3. Convert to your desired format
            4. Download the result
            
            **Tips:**
            - MP3 is the most compatible format
            - FLAC/WAV for lossless quality
            - AAC for smaller file sizes
            """)


if __name__ == "__main__":
    main()