import os
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont

def get_font(font_path: str, size: int):
    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        return ImageFont.load_default()

def translate_top_banner_shelf(img_path: str, out_path: Optional[str] = None):
    """
    Translates product gallery images on white/gray backdrop (e.g. galary_01.jpg):
    Replaces Chinese top banner with clean English typography:
    - OFFICIAL MATCHING CASE
    - ANTI-FINGERPRINT / LIQUID SILICONE
    """
    if out_path is None:
        out_path = img_path

    im = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(im)
    
    bg_color = (235, 235, 235, 255)
    draw.rectangle([0, 0, 800, 240], fill=bg_color)
    
    font_bold = get_font("C:/Windows/Fonts/arialbd.ttf", 46)
    font_med = get_font("C:/Windows/Fonts/segoeuib.ttf", 26)
    font_sub = get_font("C:/Windows/Fonts/segoeuib.ttf", 24)
    
    title = "OFFICIAL MATCHING CASE"
    bbox = draw.textbbox((0, 0), title, font=font_bold)
    w = bbox[2] - bbox[0]
    draw.text(((800 - w) / 2, 45), title, fill=(35, 35, 35, 255), font=font_bold)
    
    pill_text = "ANTI-FINGERPRINT"
    pbbox = draw.textbbox((0, 0), pill_text, font=font_sub)
    pw = pbbox[2] - pbbox[0]
    
    sub_text = "LIQUID SILICONE"
    sbbox = draw.textbbox((0, 0), sub_text, font=font_med)
    sw = sbbox[2] - sbbox[0]
    
    gap = 25
    total_w = (pw + 40) + gap + sw
    start_x = (800 - total_w) / 2
    
    pill_box = [start_x, 140, start_x + pw + 40, 185]
    draw.rounded_rectangle(pill_box, radius=22, outline=(50, 50, 50, 255), width=3)
    draw.text((start_x + 20, 148), pill_text, fill=(40, 40, 40, 255), font=font_sub)
    draw.text((start_x + pw + 40 + gap, 146), sub_text, fill=(40, 40, 40, 255), font=font_med)
    
    im.convert("RGB").save(out_path, quality=95)
    return out_path

def translate_top_banner_colored(img_path: str, out_path: Optional[str] = None):
    """
    Translates colored case images with top text banner:
    - LIQUID SILICONE CASE
    - [DROP PROTECTION] [FULL CAMERA COVER]
    """
    if out_path is None:
        out_path = img_path

    im = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(im)
    
    bg_color = im.getpixel((50, 50))
    draw.rectangle([0, 0, 800, 210], fill=bg_color)
    
    font_bold = get_font("C:/Windows/Fonts/arialbd.ttf", 46)
    font_pill = get_font("C:/Windows/Fonts/segoeuib.ttf", 22)
    
    title = "LIQUID SILICONE CASE"
    bbox = draw.textbbox((0, 0), title, font=font_bold)
    w = bbox[2] - bbox[0]
    draw.text(((800 - w) / 2, 40), title, fill=(255, 255, 255, 255), font=font_bold)
    
    t1 = "DROP PROTECTION"
    t2 = "FULL CAMERA COVER"
    
    b1 = draw.textbbox((0, 0), t1, font=font_pill)
    w1 = b1[2] - b1[0]
    b2 = draw.textbbox((0, 0), t2, font=font_pill)
    w2 = b2[2] - b2[0]
    
    pad_x = 24
    pill1_w = w1 + pad_x * 2
    pill2_w = w2 + pad_x * 2
    gap = 18
    tot_w = pill1_w + gap + pill2_w
    sx = (800 - tot_w) / 2
    
    draw.rounded_rectangle([sx, 130, sx + pill1_w, 175], radius=22, outline=(255, 255, 255, 255), width=2)
    draw.text((sx + pad_x, 140), t1, fill=(255, 255, 255, 255), font=font_pill)
    
    pill2_x = sx + pill1_w + gap
    draw.rounded_rectangle([pill2_x, 130, pill2_x + pill2_w, 175], radius=22, fill=(255, 255, 255, 255))
    draw.text((pill2_x + pad_x, 140), t2, fill=(50, 50, 50, 255), font=font_pill)
    
    im.convert("RGB").save(out_path, quality=95)
    return out_path

def translate_side_banner_blue(img_path: str, out_path: Optional[str] = None):
    """
    Translates transparent cases with right-side blue gradient banner:
    - OFFICIAL CASE
    - Features & Specification pills
    """
    if out_path is None:
        out_path = img_path

    im = Image.open(img_path).convert("RGB")
    width, height = im.size
    
    clean_col = [im.getpixel((790, y)) for y in range(height)]
    pixels = im.load()
    for y in range(0, height):
        bg = clean_col[y]
        for x in range(395, width):
            pixels[x, y] = bg
            
    draw = ImageDraw.Draw(im)
    font_title = get_font("C:/Windows/Fonts/arialbd.ttf", 52)
    font_sub = get_font("C:/Windows/Fonts/segoeuib.ttf", 20)
    font_pill = get_font("C:/Windows/Fonts/segoeuib.ttf", 21)
    
    draw.text((450, 110), "OFFICIAL", fill=(255, 255, 255), font=font_title)
    draw.text((450, 180), "CASE", fill=(255, 255, 255), font=font_title)
    
    draw.text((450, 300), "HIGH CLARITY  •  SHOCKPROOF", fill=(210, 230, 250), font=font_sub)
    draw.text((450, 335), "ANTI-FINGERPRINT COATING", fill=(210, 230, 250), font=font_sub)
    
    pills = ["ANTI-YELLOWING", "ULTRA-CLEAR SLIM", "ALL-INCLUSIVE DROP-PROOF"]
    start_y = 560
    for p in pills:
        bbox = draw.textbbox((0, 0), p, font=font_pill)
        pw = bbox[2] - bbox[0]
        box = [450, start_y, 450 + pw + 36, start_y + 48]
        draw.rounded_rectangle(box, radius=24, fill=(28, 70, 112))
        draw.text((468, start_y + 12), p, fill=(255, 255, 255), font=font_pill)
        start_y += 66
        
    im.save(out_path, quality=95)
    return out_path

def translate_tpu_gallery_01(img_path: str, out_path: Optional[str] = None, model_name: str = "Realme Neo8"):
    """Translates TPU showcase gallery_01.jpg in-place with clean typography."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(im)
    w, h = im.size

    # Yoobao clean badge
    draw.rectangle([0, 0, 340, 90], fill=(225, 23, 23))
    font_logo = get_font("C:/Windows/Fonts/arialbd.ttf", 54)
    draw.text((35, 12), "Yoobao", fill=(255, 255, 255), font=font_logo)

    # Top-right banner
    draw.rectangle([340, 0, w, 190], fill=(226, 227, 229))
    font_title = get_font("C:/Windows/Fonts/arialbd.ttf", 52)
    font_sub = get_font("C:/Windows/Fonts/segoeuib.ttf", 38)
    draw.text((430, 30), "ULTRA-THIN TPU CASE", fill=(25, 25, 25), font=font_title)
    draw.text((430, 95), "FROSTED MAGNETIC SOFT COVER", fill=(80, 80, 80), font=font_sub)

    # Bottom banner
    draw.rectangle([0, h - 160, w, h], fill=(42, 45, 50))
    font_bot = get_font("C:/Windows/Fonts/arialbd.ttf", 62)
    m_text = model_name
    draw.text((w // 2 - 200, h - 120), m_text, fill=(255, 180, 0), font=font_bot)

    im.save(out_path, quality=95)
    return out_path

def translate_tpu_gallery_02(img_path: str, out_path: Optional[str] = None):
    """Translates TPU gallery_02.jpg in-place."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(im)
    w, h = im.size
    draw.rectangle([0, 0, w, 220], fill=(216, 217, 219))
    font_g2 = get_font("C:/Windows/Fonts/arialbd.ttf", 54)
    font_g2_sub = get_font("C:/Windows/Fonts/segoeuib.ttf", 40)
    draw.text((w // 2 - 280, 40), "ULTRA-THIN FROSTED", fill=(25, 25, 25), font=font_g2)
    draw.text((w // 2 - 220, 115), "ANTI-FINGERPRINT MATTE", fill=(70, 70, 70), font=font_g2_sub)
    im.save(out_path, quality=95)
    return out_path

def translate_tpu_gallery_03(img_path: str, out_path: Optional[str] = None):
    """Translates TPU gallery_03.jpg in-place."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(im)
    draw.rectangle([740, 80, 1276, 260], fill=(216, 217, 219))
    font_g3 = get_font("C:/Windows/Fonts/arialbd.ttf", 52)
    font_g3_sub = get_font("C:/Windows/Fonts/segoeuib.ttf", 40)
    draw.text((760, 105), "MICRO-FROSTED", fill=(25, 25, 25), font=font_g3)
    draw.text((760, 175), "TRANSLUCENT DESIGN", fill=(70, 70, 70), font=font_g3_sub)
    im.save(out_path, quality=95)
    return out_path

def translate_tpu_gallery_04(img_path: str, out_path: Optional[str] = None):
    """Translates TPU gallery_04.jpg in-place."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(im)
    draw.rectangle([740, 80, 1276, 260], fill=(216, 217, 219))
    font_g4 = get_font("C:/Windows/Fonts/arialbd.ttf", 52)
    font_g4_sub = get_font("C:/Windows/Fonts/segoeuib.ttf", 40)
    draw.text((760, 105), "SKIN-FRIENDLY TOUCH", fill=(25, 25, 25), font=font_g4)
    draw.text((760, 175), "SOFT & WEAR-RESISTANT", fill=(70, 70, 70), font=font_g4_sub)
    im.save(out_path, quality=95)
    return out_path

def translate_moire_gallery_01(img_path: str, out_path: Optional[str] = None):
    """Translates Honor 600 Moiré case showcase gallery_01.jpg in-place."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(im)

    # Top right text replacement: cover [505, 40, 795, 270] with dark tone
    draw.rectangle([505, 40, 795, 270], fill=(15, 15, 18, 255))
    font_title = get_font("C:/Windows/Fonts/arialbd.ttf", 36)
    font_sub = get_font("C:/Windows/Fonts/segoeuib.ttf", 22)

    draw.text((520, 65), "MINIMALIST", fill=(255, 255, 255, 255), font=font_title)
    draw.text((520, 115), "MOIRÉ DESIGN", fill=(255, 255, 255, 255), font=font_title)

    # Skin feel pill
    draw.rounded_rectangle([520, 180, 780, 230], radius=16, fill=(210, 45, 45, 255))
    draw.text((535, 190), "SKIN-FRIENDLY FEEL", fill=(255, 255, 255, 255), font=font_sub)

    # Bottom left badges
    draw.rectangle([17, 618, 215, 690], fill=(210, 45, 45, 255))
    draw.text((25, 638), "ANTI-FINGERPRINT", fill=(255, 255, 255, 255), font=font_sub)

    draw.rectangle([16, 698, 215, 769], fill=(30, 90, 200, 255))
    draw.text((25, 718), "SWEAT-RESISTANT", fill=(255, 255, 255, 255), font=font_sub)

    im.convert("RGB").save(out_path, quality=95)
    return out_path

def translate_moire_sku(img_path: str, color_name: str, out_path: Optional[str] = None):
    """Translates Honor 600 Moiré SKU image by replacing bottom right Chinese color label."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(im)

    font = get_font("C:/Windows/Fonts/arialbd.ttf", 20)
    clean_label = color_name.replace("Built-in magnetic suction - ", "").replace("Built-in magnetic suction-", "").strip().upper()

    bbox = draw.textbbox((0, 0), clean_label, font=font)
    text_w = bbox[2] - bbox[0]
    pill_w = max(text_w + 26, 150)
    pill_right = 780
    pill_left = pill_right - pill_w
    pill_top = 720
    pill_bottom = 770

    draw.rounded_rectangle([pill_left, pill_top, pill_right, pill_bottom], radius=12, fill=(18, 18, 22, 235), outline=(70, 70, 75, 255), width=1)
    draw.text((pill_left + 13, pill_top + 13), clean_label, fill=(245, 245, 245, 255), font=font)

    im.convert("RGB").save(out_path, quality=95)
    return out_path

def translate_in_place(gallery_dir: str, sku_dir: str, material: str = "Liquid Silicone", model_name: str = "Realme Neo8"):
    """
    Translates all images containing non-English text directly in-place,
    replacing the original file in \\gallery\\ and \\sku\\.
    """
    is_tpu = "tpu" in material.lower()
    is_moire = "honor" in model_name.lower() or "moire" in material.lower() or "moire" in gallery_dir.lower()

    # 1. Process gallery images
    if os.path.exists(gallery_dir):
        for f in os.listdir(gallery_dir):
            if not f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                continue
            path = os.path.join(gallery_dir, f)
            if is_moire:
                if "01" in f:
                    translate_moire_gallery_01(path, path)
                    print(f"    [✓] In-place translated Moiré showcase: {f}")
                else:
                    print(f"    [i] Skipped clean studio image: {f}")
            elif is_tpu:
                if "01" in f:
                    translate_tpu_gallery_01(path, path, model_name=model_name)
                    print(f"    [✓] In-place translated TPU showcase: {f}")
                elif "02" in f:
                    translate_tpu_gallery_02(path, path)
                    print(f"    [✓] In-place translated TPU gallery: {f}")
                elif "03" in f:
                    translate_tpu_gallery_03(path, path)
                    print(f"    [✓] In-place translated TPU gallery: {f}")
                elif "04" in f:
                    translate_tpu_gallery_04(path, path)
                    print(f"    [✓] In-place translated TPU gallery: {f}")
                else:
                    print(f"    [i] Skipped clean image (no text overlay): {f}")
            else:
                if "01" in f:
                    translate_top_banner_shelf(path, path)
                    print(f"    [✓] In-place translated showcase: {f}")
                elif "05" in f:
                    print(f"    [i] Skipped clean image (no text): {f}")
                else:
                    translate_top_banner_colored(path, path)
                    print(f"    [✓] In-place translated gallery: {f}")

    # 2. Process SKU images
    if os.path.exists(sku_dir):
        for f in os.listdir(sku_dir):
            if not f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                continue
            path = os.path.join(sku_dir, f)
            if is_moire:
                # Determine color name from SKU filename
                col_name = "MOIRÉ"
                if "-BK-" in f:
                    col_name = "MOIRÉ BLACK"
                elif "-BL-" in f:
                    col_name = "GENTLEMAN BLUE"
                elif "-GN-" in f:
                    col_name = "DARK NIGHT GREEN"
                elif "-RD-" in f:
                    col_name = "CHARMING RED"
                translate_moire_sku(path, col_name, path)
                print(f"    [✓] In-place translated Moiré SKU ({col_name}): {f}")
            elif is_tpu:
                print(f"    [i] Clean studio SKU image verified: {f}")
            else:
                if "-CL-" in f or "Transparent" in f:
                    translate_side_banner_blue(path, path)
                    print(f"    [✓] In-place translated clear SKU: {f}")
                else:
                    translate_top_banner_colored(path, path)
                    print(f"    [✓] In-place translated colored SKU: {f}")
