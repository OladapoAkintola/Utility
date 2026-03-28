import streamlit as st
import io
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import mutagen
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE
import pypdf
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
import datetime

#st.set_page_config(page_title="Metadata Cleaner", page_icon="🔏")

# ──────────────────────────────────────────────
# HELPERS — DETECT FILE TYPE
# ──────────────────────────────────────────────

IMAGE_EXTS  = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp", ".bmp"}
AUDIO_EXTS  = {".mp3", ".flac", ".ogg", ".m4a", ".mp4", ".aac", ".wav"}
PDF_EXTS    = {".pdf"}
DOCX_EXTS   = {".docx"}

def file_category(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXTS:  return "image"
    if ext in AUDIO_EXTS:  return "audio"
    if ext in PDF_EXTS:    return "pdf"
    if ext in DOCX_EXTS:   return "docx"
    return "unsupported"


# ──────────────────────────────────────────────
# IMAGE
# ──────────────────────────────────────────────

def extract_image_metadata(file_bytes: bytes) -> dict:
    img = Image.open(io.BytesIO(file_bytes))
    meta = {
        "Format":     img.format or "Unknown",
        "Color mode": img.mode,
        "Dimensions": f"{img.width} × {img.height} px",
    }

    # EXIF (JPEG / TIFF / WEBP)
    try:
        exif = img.getexif()
        if exif:
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, f"Tag_{tag_id}")
                # Expand GPS sub-IFD
                if tag == "GPSInfo" and isinstance(value, dict):
                    for gps_id, gps_val in value.items():
                        gps_tag = GPSTAGS.get(gps_id, f"GPS_{gps_id}")
                        meta[f"GPS: {gps_tag}"] = str(gps_val)
                else:
                    meta[f"EXIF: {tag}"] = str(value)[:200]
    except Exception:
        pass

    # PNG text chunks
    if img.format == "PNG" and hasattr(img, "text") and img.text:
        for k, v in img.text.items():
            meta[f"PNG text: {k}"] = str(v)[:200]

    return meta


def strip_image_metadata(file_bytes: bytes, filename: str) -> bytes:
    img = Image.open(io.BytesIO(file_bytes))
    ext = Path(filename).suffix.lower()
    output = io.BytesIO()

    # Build a fresh image with pixel data only — no info/exif
    data = list(img.getdata())
    clean = Image.new(img.mode, img.size)
    clean.putdata(data)

    fmt_map = {
        ".jpg": "JPEG", ".jpeg": "JPEG",
        ".png": "PNG",
        ".webp": "WEBP",
        ".bmp": "BMP",
        ".tiff": "TIFF", ".tif": "TIFF",
    }
    save_fmt = fmt_map.get(ext, img.format or "PNG")

    if save_fmt == "JPEG" and clean.mode in ("RGBA", "P"):
        clean = clean.convert("RGB")

    save_kwargs = {"format": save_fmt}
    if save_fmt == "JPEG":
        save_kwargs["quality"] = 95
        save_kwargs["subsampling"] = 0

    clean.save(output, **save_kwargs)
    output.seek(0)
    return output.getvalue()


# ──────────────────────────────────────────────
# AUDIO
# ──────────────────────────────────────────────

def extract_audio_metadata(file_bytes: bytes, filename: str) -> dict:
    ext = Path(filename).suffix.lower()
    tmp = io.BytesIO(file_bytes)
    tmp.name = filename  # mutagen uses the name hint

    try:
        audio = mutagen.File(tmp, easy=True)
    except Exception:
        return {"Error": "Could not parse audio metadata"}

    if audio is None:
        return {"Note": "No metadata found in this audio file"}

    meta = {}
    if audio.info:
        info = audio.info
        meta["Length"]   = f"{getattr(info, 'length', 0):.1f}s"
        meta["Bitrate"]  = f"{getattr(info, 'bitrate', 0)} kbps" if hasattr(info, "bitrate") else "N/A"
        meta["Channels"] = str(getattr(info, "channels", "N/A"))
        meta["Sample rate"] = f"{getattr(info, 'sample_rate', 'N/A')} Hz" if hasattr(info, "sample_rate") else "N/A"

    for key, value in audio.tags.items() if audio.tags else []:
        meta[key] = ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)

    return meta


def strip_audio_metadata(file_bytes: bytes, filename: str, keys_to_remove: list | None = None) -> bytes:
    """
    keys_to_remove=None  → strip ALL tags
    keys_to_remove=[...] → strip only those keys
    """
    ext = Path(filename).suffix.lower()
    tmp = io.BytesIO(file_bytes)
    tmp.name = filename

    audio = mutagen.File(tmp, easy=True)
    if audio is None or audio.tags is None:
        return file_bytes  # nothing to strip

    if keys_to_remove is None:
        audio.delete()
    else:
        for k in keys_to_remove:
            try:
                del audio[k]
            except KeyError:
                pass

    output = io.BytesIO()
    audio.save(output)
    output.seek(0)
    return output.getvalue()


# ──────────────────────────────────────────────
# PDF
# ──────────────────────────────────────────────

def extract_pdf_metadata(file_bytes: bytes) -> dict:
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    meta = {}

    if reader.metadata:
        for k, v in reader.metadata.items():
            clean_key = k.lstrip("/")
            meta[clean_key] = str(v)

    meta["Pages"] = str(len(reader.pages))

    # XMP metadata
    try:
        xmp = reader.xmp_metadata
        if xmp:
            meta["XMP present"] = "Yes (stripped with core metadata)"
    except Exception:
        pass

    return meta


def strip_pdf_metadata(file_bytes: bytes, keys_to_remove: list | None = None) -> bytes:
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    writer = pypdf.PdfWriter()

    # Copy all pages
    for page in reader.pages:
        writer.add_page(page)

    if keys_to_remove is None:
        # Wipe everything
        writer.add_metadata({})
    else:
        # Keep everything except chosen keys
        if reader.metadata:
            kept = {k: v for k, v in reader.metadata.items()
                    if k.lstrip("/") not in keys_to_remove}
            writer.add_metadata(kept)

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output.getvalue()


# ──────────────────────────────────────────────
# DOCX
# ──────────────────────────────────────────────

DOCX_CORE_FIELDS = [
    "author", "last_modified_by", "created", "modified",
    "title", "subject", "description", "keywords",
    "category", "content_status", "identifier", "language",
    "revision", "version",
]

def extract_docx_metadata(file_bytes: bytes) -> dict:
    doc = Document(io.BytesIO(file_bytes))
    cp = doc.core_properties
    meta = {}
    for field in DOCX_CORE_FIELDS:
        val = getattr(cp, field, None)
        if val is not None and str(val).strip():
            meta[field.replace("_", " ").title()] = str(val)
    return meta


def strip_docx_metadata(file_bytes: bytes, keys_to_remove: list | None = None) -> bytes:
    doc = Document(io.BytesIO(file_bytes))
    cp = doc.core_properties

    # Map display label → attribute name
    label_to_attr = {f.replace("_", " ").title(): f for f in DOCX_CORE_FIELDS}

    targets = (
        DOCX_CORE_FIELDS
        if keys_to_remove is None
        else [label_to_attr.get(k, k.lower().replace(" ", "_")) for k in keys_to_remove]
    )

    blank_date = datetime.datetime(1900, 1, 1)
    for attr in targets:
        try:
            existing = getattr(cp, attr, None)
            if isinstance(existing, datetime.datetime):
                setattr(cp, attr, blank_date)
            elif existing is not None:
                setattr(cp, attr, "")
        except Exception:
            pass

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output.getvalue()


# ──────────────────────────────────────────────
# MIME TYPES FOR DOWNLOAD
# ──────────────────────────────────────────────

MIME = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png",  ".webp": "image/webp",
    ".bmp": "image/bmp",  ".tiff": "image/tiff", ".tif": "image/tiff",
    ".mp3": "audio/mpeg", ".flac": "audio/flac",
    ".ogg": "audio/ogg",  ".m4a": "audio/mp4",
    ".wav": "audio/wav",  ".aac": "audio/aac",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


# ──────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────

st.title("🔏 Metadata Cleaner")
st.caption(
    "Upload files to inspect hidden metadata — then strip what you don't want. "
    "Supports images, audio, PDF, and DOCX."
)

SUPPORTED = "JPG, PNG, WEBP, TIFF, BMP · MP3, FLAC, OGG, M4A, WAV · PDF · DOCX"

uploaded_files = st.file_uploader(
    "Drop your files here",
    accept_multiple_files=True,
    help=f"Supported: {SUPPORTED}",
)

if not uploaded_files:
    st.info(f"**Supported formats:** {SUPPORTED}")
    st.stop()

for uploaded in uploaded_files:
    filename  = uploaded.name
    file_bytes = uploaded.read()
    category  = file_category(filename)
    ext       = Path(filename).suffix.lower()

    with st.expander(f"📄 {filename}", expanded=True):

        if category == "unsupported":
            st.warning("Unsupported file type — skipping.")
            continue

        # ── Extract metadata ──
        if   category == "image": meta = extract_image_metadata(file_bytes)
        elif category == "audio": meta = extract_audio_metadata(file_bytes, filename)
        elif category == "pdf":   meta = extract_pdf_metadata(file_bytes)
        elif category == "docx":  meta = extract_docx_metadata(file_bytes)

        if not meta or all(k in {"Format", "Color mode", "Dimensions", "Pages", "Length",
                                  "Bitrate", "Channels", "Sample rate"} for k in meta):
            st.success("✅ No significant metadata found in this file.")
            continue

        # ── Display metadata table ──
        st.subheader("Metadata found")

        # Separate technical (non-strippable) vs user metadata for images/audio
        technical_keys = {"Format", "Color mode", "Dimensions", "Pages",
                          "Length", "Bitrate", "Channels", "Sample rate"}
        strippable = {k: v for k, v in meta.items() if k not in technical_keys}
        technical  = {k: v for k, v in meta.items() if k in technical_keys}

        if technical:
            st.markdown("**Technical info** *(not stored as metadata)*")
            st.table(technical)

        if strippable:
            st.markdown("**Embedded metadata** *(can be stripped)*")
            st.table(strippable)
        else:
            st.success("✅ No strippable metadata found.")
            continue

        # ── Strip controls ──
        st.divider()
        st.subheader("Strip options")

        strip_all = st.checkbox("Strip ALL metadata", key=f"all_{filename}", value=True)

        selected_keys = []
        if not strip_all:
            # Images: EXIF can only be fully stripped (no per-field API without piexif)
            if category == "image":
                st.info(
                    "Image EXIF is stored as a binary block. "
                    "Individual field removal requires stripping all EXIF. "
                    "GPS and personal data are included."
                )
                strip_all = True  # force full strip for images
            else:
                st.markdown("Select which fields to remove:")
                cols = st.columns(2)
                for i, key in enumerate(strippable.keys()):
                    with cols[i % 2]:
                        if st.checkbox(key, key=f"field_{filename}_{key}"):
                            selected_keys.append(key)

        # ── Strip button ──
        strip_label = "Strip all metadata" if strip_all else f"Strip {len(selected_keys)} field(s)"
        if st.button(strip_label, key=f"btn_{filename}", type="primary",
                     disabled=(not strip_all and not selected_keys)):
            try:
                keys_arg = None if strip_all else selected_keys

                if   category == "image": cleaned = strip_image_metadata(file_bytes, filename)
                elif category == "audio": cleaned = strip_audio_metadata(file_bytes, filename, keys_arg)
                elif category == "pdf":   cleaned = strip_pdf_metadata(file_bytes, keys_arg)
                elif category == "docx":  cleaned = strip_docx_metadata(file_bytes, keys_arg)

                st.success("✅ Metadata stripped successfully!")

                stem = Path(filename).stem
                clean_name = f"{stem}_clean{ext}"
                st.download_button(
                    label=f"⬇️ Download {clean_name}",
                    data=cleaned,
                    file_name=clean_name,
                    mime=MIME.get(ext, "application/octet-stream"),
                    key=f"dl_{filename}",
                )

            except Exception as e:
                st.error(f"Something went wrong: {e}")
