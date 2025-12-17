import streamlit as st
from PIL import Image
import io
from typing import Tuple, Optional

# Page configuration
st.set_page_config(page_title="Image Converter", page_icon="🖼️")

# Custom CSS for better UI
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #FF4B4B;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #FF6B6B;
    }
    .upload-section {
        padding: 2rem;
        border: 2px dashed #FF4B4B;
        border-radius: 10px;
        text-align: center;
        background-color: #f8f9fa;
    }
    .info-box {
        padding: 1rem;
        border-radius: 8px;
        background-color: #e7f3ff;
        border-left: 4px solid #2196F3;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Title and description
st.title("🖼️ Image Converter & Resizer")
st.markdown("Convert images between formats and resize them with ease")

# Sidebar settings
st.sidebar.header("⚙️ Settings")

# Initialize session state
if 'processed_image' not in st.session_state:
    st.session_state.processed_image = None
if 'original_image' not in st.session_state:
    st.session_state.original_image = None

# File uploader
uploaded_file = st.file_uploader(
    "Choose an image file",
    type=['png', 'jpg', 'jpeg', 'webp', 'bmp', 'gif', 'tiff'],
    help="Upload an image in any common format"
)

if uploaded_file is not None:
    # Load the image
    try:
        original_image = Image.open(uploaded_file)
        st.session_state.original_image = original_image
        
        # Display original image info
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📥 Original Image")
            st.image(original_image, use_container_width=True)
        
        with col2:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown("**Image Info:**")
            st.write(f"📐 Size: {original_image.size[0]} × {original_image.size[1]} px")
            st.write(f"🎨 Mode: {original_image.mode}")
            st.write(f"📁 Format: {original_image.format if original_image.format else 'Unknown'}")
            
            # Calculate file size
            img_byte_arr = io.BytesIO()
            original_image.save(img_byte_arr, format=original_image.format if original_image.format else 'PNG')
            file_size = len(img_byte_arr.getvalue()) / 1024
            st.write(f"💾 Size: {file_size:.2f} KB")
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        
        # Conversion and resizing options
        st.subheader("🔧 Conversion Options")
        
        tab1, tab2, tab3 = st.tabs(["Format Conversion", "Resize", "Both"])
        
        with tab1:
            st.markdown("### Convert Image Format")
            output_format = st.selectbox(
                "Select output format",
                options=['PNG', 'JPEG', 'WEBP', 'BMP', 'GIF', 'TIFF'],
                help="Choose the format you want to convert to"
            )
            
            if output_format == 'JPEG':
                quality = st.slider(
                    "JPEG Quality",
                    min_value=1,
                    max_value=100,
                    value=95,
                    help="Higher quality = larger file size"
                )
            else:
                quality = 95
            
            if st.button("Convert Format", key="convert_only"):
                processed_image = original_image.copy()
                
                # Convert RGBA to RGB for JPEG
                if output_format == 'JPEG' and processed_image.mode in ('RGBA', 'LA', 'P'):
                    rgb_image = Image.new('RGB', processed_image.size, (255, 255, 255))
                    if processed_image.mode == 'P':
                        processed_image = processed_image.convert('RGBA')
                    rgb_image.paste(processed_image, mask=processed_image.split()[-1] if processed_image.mode in ('RGBA', 'LA') else None)
                    processed_image = rgb_image
                
                st.session_state.processed_image = processed_image
                st.session_state.output_format = output_format
                st.session_state.quality = quality
                st.success(f"✅ Converted to {output_format}!")
        
        with tab2:
            st.markdown("### Resize Image")
            
            resize_method = st.radio(
                "Resize method",
                options=['Percentage', 'Custom dimensions', 'Preset sizes'],
                horizontal=True
            )
            
            new_width, new_height = None, None
            
            if resize_method == 'Percentage':
                percentage = st.slider(
                    "Resize percentage",
                    min_value=10,
                    max_value=200,
                    value=100,
                    step=5,
                    help="100% = original size"
                )
                new_width = int(original_image.size[0] * percentage / 100)
                new_height = int(original_image.size[1] * percentage / 100)
                st.info(f"New size: {new_width} × {new_height} px")
            
            elif resize_method == 'Custom dimensions':
                col_w, col_h = st.columns(2)
                with col_w:
                    new_width = st.number_input(
                        "Width (px)",
                        min_value=1,
                        max_value=10000,
                        value=original_image.size[0]
                    )
                with col_h:
                    new_height = st.number_input(
                        "Height (px)",
                        min_value=1,
                        max_value=10000,
                        value=original_image.size[1]
                    )
                
                maintain_ratio = st.checkbox(
                    "Maintain aspect ratio",
                    value=True,
                    help="Lock proportions"
                )
                
                if maintain_ratio:
                    aspect_ratio = original_image.size[0] / original_image.size[1]
                    new_height = int(new_width / aspect_ratio)
                    st.info(f"Adjusted size: {new_width} × {new_height} px")
            
            else:  # Preset sizes
                preset = st.selectbox(
                    "Select preset",
                    options=[
                        'HD (1920×1080)',
                        'Full HD (1920×1080)',
                        'Instagram Square (1080×1080)',
                        'Instagram Portrait (1080×1350)',
                        'Facebook Cover (820×312)',
                        'Twitter Header (1500×500)',
                        'YouTube Thumbnail (1280×720)'
                    ]
                )
                
                preset_sizes = {
                    'HD (1920×1080)': (1920, 1080),
                    'Full HD (1920×1080)': (1920, 1080),
                    'Instagram Square (1080×1080)': (1080, 1080),
                    'Instagram Portrait (1080×1350)': (1080, 1350),
                    'Facebook Cover (820×312)': (820, 312),
                    'Twitter Header (1500×500)': (1500, 500),
                    'YouTube Thumbnail (1280×720)': (1280, 720)
                }
                
                new_width, new_height = preset_sizes[preset]
            
            resample_method = st.selectbox(
                "Resampling method",
                options=['LANCZOS (Best quality)', 'BILINEAR', 'BICUBIC', 'NEAREST (Fastest)'],
                help="LANCZOS provides the best quality for downsizing"
            )
            
            resample_map = {
                'LANCZOS (Best quality)': Image.Resampling.LANCZOS,
                'BILINEAR': Image.Resampling.BILINEAR,
                'BICUBIC': Image.Resampling.BICUBIC,
                'NEAREST (Fastest)': Image.Resampling.NEAREST
            }
            
            if st.button("Resize Image", key="resize_only"):
                processed_image = original_image.resize(
                    (new_width, new_height),
                    resample_map[resample_method]
                )
                st.session_state.processed_image = processed_image
                st.session_state.output_format = original_image.format if original_image.format else 'PNG'
                st.session_state.quality = 95
                st.success(f"✅ Resized to {new_width} × {new_height} px!")
        
        with tab3:
            st.markdown("### Convert Format AND Resize")
            
            # Format selection
            output_format_both = st.selectbox(
                "Output format",
                options=['PNG', 'JPEG', 'WEBP', 'BMP', 'GIF', 'TIFF'],
                key="format_both"
            )
            
            if output_format_both == 'JPEG':
                quality_both = st.slider(
                    "JPEG Quality",
                    min_value=1,
                    max_value=100,
                    value=95,
                    key="quality_both"
                )
            else:
                quality_both = 95
            
            # Resize options
            resize_method_both = st.radio(
                "Resize method",
                options=['Percentage', 'Custom dimensions'],
                horizontal=True,
                key="resize_both"
            )
            
            if resize_method_both == 'Percentage':
                percentage_both = st.slider(
                    "Resize percentage",
                    min_value=10,
                    max_value=200,
                    value=100,
                    step=5,
                    key="percentage_both"
                )
                new_width_both = int(original_image.size[0] * percentage_both / 100)
                new_height_both = int(original_image.size[1] * percentage_both / 100)
            else:
                col_w, col_h = st.columns(2)
                with col_w:
                    new_width_both = st.number_input(
                        "Width (px)",
                        min_value=1,
                        max_value=10000,
                        value=original_image.size[0],
                        key="width_both"
                    )
                with col_h:
                    new_height_both = st.number_input(
                        "Height (px)",
                        min_value=1,
                        max_value=10000,
                        value=original_image.size[1],
                        key="height_both"
                    )
            
            if st.button("Convert & Resize", key="both"):
                # Resize first
                processed_image = original_image.resize(
                    (new_width_both, new_height_both),
                    Image.Resampling.LANCZOS
                )
                
                # Convert format if needed for JPEG
                if output_format_both == 'JPEG' and processed_image.mode in ('RGBA', 'LA', 'P'):
                    rgb_image = Image.new('RGB', processed_image.size, (255, 255, 255))
                    if processed_image.mode == 'P':
                        processed_image = processed_image.convert('RGBA')
                    rgb_image.paste(processed_image, mask=processed_image.split()[-1] if processed_image.mode in ('RGBA', 'LA') else None)
                    processed_image = rgb_image
                
                st.session_state.processed_image = processed_image
                st.session_state.output_format = output_format_both
                st.session_state.quality = quality_both
                st.success(f"✅ Converted to {output_format_both} and resized!")
        
        # Display processed image
        if st.session_state.processed_image is not None:
            st.divider()
            st.subheader("📤 Processed Image")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.image(st.session_state.processed_image, use_container_width=True)
            
            with col2:
                processed_img = st.session_state.processed_image
                st.markdown('<div class="info-box">', unsafe_allow_html=True)
                st.markdown("**New Image Info:**")
                st.write(f"📐 Size: {processed_img.size[0]} × {processed_img.size[1]} px")
                st.write(f"🎨 Mode: {processed_img.mode}")
                st.write(f"📁 Format: {st.session_state.output_format}")
                
                # Calculate new file size
                img_byte_arr = io.BytesIO()
                save_kwargs = {'format': st.session_state.output_format}
                if st.session_state.output_format == 'JPEG':
                    save_kwargs['quality'] = st.session_state.quality
                processed_img.save(img_byte_arr, **save_kwargs)
                new_file_size = len(img_byte_arr.getvalue()) / 1024
                st.write(f"💾 Size: {new_file_size:.2f} KB")
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Download button
                img_byte_arr.seek(0)
                file_extension = st.session_state.output_format.lower()
                if file_extension == 'jpeg':
                    file_extension = 'jpg'
                
                st.download_button(
                    label="⬇️ Download Image",
                    data=img_byte_arr,
                    file_name=f"converted_image.{file_extension}",
                    mime=f"image/{file_extension}",
                    use_container_width=True
                )
    
    except Exception as e:
        st.error(f"❌ Error processing image: {str(e)}")
        st.info("Please make sure you've uploaded a valid image file.")

else:
    # Show upload instructions
    st.markdown("""
        <div class="upload-section">
            <h3>👆 Upload an image to get started</h3>
            <p>Supported formats: PNG, JPEG, WEBP, BMP, GIF, TIFF</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Show features
    st.markdown("---")
    st.subheader("✨ Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🔄 Format Conversion")
        st.markdown("""
        - Convert between all major formats
        - Adjust JPEG quality
        - Automatic transparency handling
        """)
    
    with col2:
        st.markdown("### 📏 Smart Resizing")
        st.markdown("""
        - Percentage-based scaling
        - Custom dimensions
        - Social media presets
        """)
    
    with col3:
        st.markdown("### 🎯 Quality Options")
        st.markdown("""
        - Multiple resampling methods
        - Maintain aspect ratio
        - Preview before download
        """)