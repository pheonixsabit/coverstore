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

def translate_in_place(gallery_dir: str, sku_dir: str):
    """
    Translates all images containing non-English text directly in-place,
    replacing the original file in \\gallery\\ and \\sku\\.
    """
    # 1. Process gallery images
    if os.path.exists(gallery_dir):
        for f in os.listdir(gallery_dir):
            if not f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                continue
            path = os.path.join(gallery_dir, f)
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
            if "-CL-" in f or "Transparent" in f:
                translate_side_banner_blue(path, path)
                print(f"    [✓] In-place translated clear SKU: {f}")
            else:
                translate_top_banner_colored(path, path)
                print(f"    [✓] In-place translated colored SKU: {f}")
