import streamlit as st
import os
import tempfile
from pathlib import Path
import subprocess
import shutil

st.title("📄 Document Converter")
st.write("Convert between different document formats: DOCX, HTML, PDF, Markdown, and TXT")

# Supported formats and their conversions
SUPPORTED_FORMATS = {
    "docx": ["html", "pdf", "md", "txt"],
    "html": ["docx", "pdf", "md", "txt"],
    "pdf": ["txt", "md", "html"],
    "md": ["docx", "html", "pdf", "txt"],
    "txt": ["docx", "html", "pdf", "md"]
}

def get_file_extension(filename):
    """Get file extension without the dot"""
    return Path(filename).suffix.lstrip('.').lower()



def convert_with_pandoc(input_file, output_file, from_format, to_format):
    """Convert document using pandoc"""
    try:
        cmd = ['pandoc', input_file, '-f', from_format, '-t', to_format, '-o', output_file]
        
        # Add special options for PDF conversion
        if to_format == 'pdf':
            cmd.extend(['--pdf-engine=wkhtmltopdf'])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return True, "Conversion successful!"
        else:
            return False, f"Conversion failed: {result.stderr}"
    except subprocess.TimeoutExpired:
        return False, "Conversion timed out"
    except Exception as e:
        return False, f"Error during conversion: {str(e)}"

def convert_pdf_to_text(input_file, output_file):
    """Convert PDF to text using pdfplumber"""
    try:
        import pdfplumber
        
        text = ""
        with pdfplumber.open(input_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
                text += "\n\n"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
        
        return True, "Conversion successful!"
    except ImportError:
        # Install pdfplumber
        subprocess.run(['pip', 'install', 'pdfplumber', '--break-system-packages'], 
                      capture_output=True)
        return convert_pdf_to_text(input_file, output_file)
    except Exception as e:
        return False, f"Error extracting text from PDF: {str(e)}"

def perform_conversion(input_path, output_path, from_format, to_format):
    """Route to appropriate conversion method"""
    
    # Special case: PDF to text
    if from_format == 'pdf' and to_format in ['txt', 'md']:
        success, message = convert_pdf_to_text(input_path, output_path)
        
        # If converting to markdown, add some basic formatting
        if success and to_format == 'md':
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Add markdown header
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# Converted from PDF\n\n{content}")
        
        return success, message
    
    # Special case: PDF to HTML
    if from_format == 'pdf' and to_format == 'html':
        # First convert to text, then to HTML
        temp_txt = output_path.replace('.html', '_temp.txt')
        success, message = convert_pdf_to_text(input_path, temp_txt)
        if not success:
            return False, message
        
        # Convert text to HTML with pandoc
        success, message = convert_with_pandoc(temp_txt, output_path, 'plain', 'html')
        
        # Clean up temp file
        if os.path.exists(temp_txt):
            os.remove(temp_txt)
        
        return success, message
    
    # Map format names to pandoc format names
    format_map = {
        'docx': 'docx',
        'html': 'html',
        'md': 'markdown',
        'txt': 'plain',
        'pdf': 'pdf'
    }
    
    pandoc_from = format_map.get(from_format, from_format)
    pandoc_to = format_map.get(to_format, to_format)
    
    return convert_with_pandoc(input_path, output_path, pandoc_from, pandoc_to)

# File uploader
uploaded_file = st.file_uploader(
    "Choose a document to convert",
    type=['docx', 'html', 'pdf', 'md', 'txt'],
    help="Supported formats: DOCX, HTML, PDF, Markdown (MD), and TXT"
)

if uploaded_file:
    # Get input format
    input_format = get_file_extension(uploaded_file.name)
    
    if input_format not in SUPPORTED_FORMATS:
        st.error(f"Unsupported input format: {input_format}")
    else:
        # Display file info
        st.success(f"📄 Loaded: {uploaded_file.name} ({input_format.upper()})")
        
        # Select output format
        available_formats = SUPPORTED_FORMATS[input_format]
        
        output_format = st.selectbox(
            "Convert to:",
            options=available_formats,
            format_func=lambda x: x.upper()
        )
        
        # Convert button
        if st.button("🔄 Convert", type="primary"):
            with st.spinner("Converting..."):
                # Create temporary files
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Save uploaded file
                    input_path = os.path.join(temp_dir, f"input.{input_format}")
                    with open(input_path, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Prepare output path
                    output_filename = f"{Path(uploaded_file.name).stem}.{output_format}"
                    output_path = os.path.join(temp_dir, output_filename)
                    
                    # Perform conversion
                    success, message = perform_conversion(
                        input_path, 
                        output_path, 
                        input_format, 
                        output_format
                    )
                    
                    if success and os.path.exists(output_path):
                        st.success(message)
                        
                        # Read converted file
                        with open(output_path, 'rb') as f:
                            converted_data = f.read()
                        
                        # Determine MIME type
                        mime_types = {
                            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                            'html': 'text/html',
                            'pdf': 'application/pdf',
                            'md': 'text/markdown',
                            'txt': 'text/plain'
                        }
                        
                        mime_type = mime_types.get(output_format, 'application/octet-stream')
                        
                        # Download button
                        st.download_button(
                            label=f"⬇️ Download {output_format.upper()}",
                            data=converted_data,
                            file_name=output_filename,
                            mime=mime_type
                        )
                        
                        # Preview for text-based formats
                        if output_format in ['txt', 'md', 'html']:
                            with st.expander("📝 Preview"):
                                try:
                                    preview_text = converted_data.decode('utf-8')
                                    if output_format == 'html':
                                        st.code(preview_text, language='html')
                                    elif output_format == 'md':
                                        st.markdown(preview_text)
                                    else:
                                        st.text(preview_text[:2000] + ("..." if len(preview_text) > 2000 else ""))
                                except:
                                    st.info("Preview not available for this file")
                    else:
                        st.error(message)

# Information section
with st.expander("ℹ️ Supported Conversions"):
    st.markdown("""
    ### Supported Format Conversions
    
    **From DOCX:**
    - → HTML, PDF, Markdown, TXT
    
    **From HTML:**
    - → DOCX, PDF, Markdown, TXT
    
    **From PDF:**
    - → TXT, Markdown, HTML (text extraction)
    
    **From Markdown:**
    - → DOCX, HTML, PDF, TXT
    
    **From TXT:**
    - → DOCX, HTML, PDF, Markdown
    
    ### Notes
    - PDF conversions extract text content (formatting may be lost)
    - Complex formatting may not be preserved in all conversions
    - Large files may take longer to convert
    """)

st.markdown("---")
st.markdown("💡 **Tip:** For best results, use source documents with clean formatting")
