# app.py
import streamlit as st
from io import BytesIO
import cairosvg
from PIL import Image, ImageOps
import os
import zipfile
import numpy as np

st.set_page_config(page_title="Conversor de logos", page_icon="🖼", layout="centered")
st.title("🖼 Conversor de logotipos SVG → JPG")

FORMATS = [
    ((64, 64), (6, 6), "64x64"),
    ((180, 135), (18, 18), "180x135"),
    ((200, 200), (18, 18), "200x200"),
    ((224, 128), (18, 18), "224x128"),
    ((224, 198), (18, 18), "224x198"),
    ((290, 163), (26, 20), "WCHICA"),
    ((200, 300), (35, 28), "WMEDIANA"),
    ((675, 380), (60, 60), "WGRANDE"),
    ((480, 720), (80, 72), "WVERTICAL"),
    ((1280, 720), (104, 117), "WHORIZONTAL"),
    ((1080, 1080), (150, 130), "WCUADRADO"),
    ((1920, 1080), (200, 180), "1920x1080")
]

st.subheader("📐 Formatos disponibles")
st.table({
    "Tamaño": [f"{w}x{h}" for (w, h), _, _ in FORMATS],
    "Márgenes (horiz, vert)": [f"{m[0]}, {m[1]}" for _, m, _ in FORMATS],
    "Sufijo": [s for _, _, s in FORMATS],
})

def render_svg_to_png(svg_bytes, width, height, dpi=300):
    png_bytes = cairosvg.svg2png(bytestring=svg_bytes, output_width=width, output_height=height, dpi=dpi)
    img = Image.open(BytesIO(png_bytes)).convert("RGBA")
    return img

def is_pure_white_or_black(img: Image.Image) -> str:
    arr = np.array(img)
    if arr.shape[2] == 4:
        mask = arr[:, :, 3] > 0
        rgb = arr[:, :, :3][mask]
    else:
        rgb = arr[:, :, :3]
    if rgb.size == 0:
        return ""
    if np.all(rgb == 255):
        return "white"
    if np.all(rgb == 0):
        return "black"
    return ""

def invert_logo(img: Image.Image) -> Image.Image:
    r, g, b, a = img.split()
    rgb_inverted = ImageOps.invert(Image.merge("RGB", (r, g, b)))
    return Image.merge("RGBA", (*rgb_inverted.split(), a))

def compose_on_canvas(logo_img: Image.Image, canvas_w: int, canvas_h: int, bg_color: str):
    canvas = Image.new("RGB", (canvas_w, canvas_h), bg_color)
    w, h = logo_img.size
    x = (canvas_w - w) // 2
    y = (canvas_h - h) // 2
    canvas.paste(logo_img, (x, y), logo_img)
    return canvas

def crop_to_content(img: Image.Image) -> Image.Image:
    arr = np.array(img)
    if arr.shape[2] == 4:
        alpha = arr[:, :, 3]
        mask = alpha > 10
        coords = np.argwhere(mask)
        if coords.size == 0:
            return img
        y0, x0 = coords.min(axis=0)
        y1, x1 = coords.max(axis=0) + 1
        return img.crop((x0, y0, x1, y1))
    else:
        return img

uploaded_files = st.file_uploader("Sube uno o varios archivos SVG o PNG", type=["svg", "png"], accept_multiple_files=True)

if not uploaded_files:
    st.info("⬆️ Sube al menos un archivo SVG o PNG para generar las variantes.")
else:
    all_files = []
    previews = []

    for uploaded in uploaded_files:
        base_name = os.path.splitext(uploaded.name)[0]
        ext = os.path.splitext(uploaded.name)[1].lower()

        if ext == ".svg":
            svg_bytes = uploaded.read()
            def get_logo(box_w, box_h):
                return render_svg_to_png(svg_bytes, box_w, box_h, dpi=300)
        elif ext == ".png":
            img = Image.open(uploaded).convert("RGBA")
            def get_logo(box_w, box_h):
                cropped = crop_to_content(img)
                lw, lh = cropped.size
                if lw / box_w > lh / box_h:
                    scale = box_w / lw
                else:
                    scale = box_h / lh
                new_size = (int(lw * scale), int(lh * scale))
                return cropped.resize(new_size, Image.LANCZOS)
        else:
            continue

        for (canvas_size, margins, suffix) in FORMATS:
            cw, ch = canvas_size
            mx, my = margins
            box_w = cw - 2 * mx
            box_h = ch - 2 * my

            logo_png = get_logo(box_w, box_h)
            pure = is_pure_white_or_black(logo_png)

            for color in ["white", "black"]:
                logo_final = logo_png
                if (pure == "black" and color == "black") or (pure == "white" and color == "white"):
                    logo_final = invert_logo(logo_png)
                result = compose_on_canvas(logo_final, cw, ch, bg_color=color)
                buf = BytesIO()
                result.save(buf, format="JPEG", quality=100, dpi=(300, 300))
                buf.seek(0)
                folder = f"{base_name} FONDO BLANCO" if color == "white" else f"{base_name} FONDO NEGRO"
                fname = f"{folder}/{base_name}{suffix}.jpg"
                all_files.append((fname, buf.getvalue()))
                if suffix == "WHORIZONTAL":
                    previews.append((base_name, color, result))

            if suffix == "WCHICA":
                transparent_canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
                w, h = logo_png.size
                x = (cw - w) // 2
                y = (ch - h) // 2
                transparent_canvas.paste(logo_png, (x, y), logo_png)
                buf_png = BytesIO()
                transparent_canvas.save(buf_png, format="PNG")
                buf_png.seek(0)
                fname_png = f"{base_name} FONDO TRANSPARENTE/{base_name}{suffix}.png"
                all_files.append((fname_png, buf_png.getvalue()))

    st.subheader("👀 Vista previa (formato 1280x720, fondo blanco y negro)")
    for name, color, img in previews:
        fondo = "blanco" if color == "white" else "negro"
        st.image(img, caption=f"{name} - 1280x720 fondo {fondo}", use_container_width=False)

    st.subheader("👁 Vista previa 64x64 (100%)")
    for uploaded in uploaded_files:
        base_name = os.path.splitext(uploaded.name)[0]
        ext = os.path.splitext(uploaded.name)[1].lower()
        if ext not in [".svg", ".png"]:
            continue
        for color in ["white", "black"]:
            folder = f"{base_name} FONDO BLANCO" if color == "white" else f"{base_name} FONDO NEGRO"
            fname = f"{folder}/{base_name}64x64.jpg"
            for f, data in all_files:
                if f == fname:
                    img = Image.open(BytesIO(data))
                    fondo = "blanco" if color == "white' else 'negro'"
                    st.image(img, caption=f"{base_name} - 64x64 fondo {fondo}", width=64)

    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as z:
        for fname, data in all_files:
            z.writestr(fname, data)
    zip_buf.seek(0)

    st.success("✅ Archivos generados correctamente.")
    st.download_button(label="⬇️ Descargar ZIP con todas las variantes", data=zip_buf.getvalue(), file_name="logos_variantes.zip", mime="application/zip")
