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

    font = get_font("C:/Windows/Fonts/arialbd.ttf", 18)
    clean_label = color_name.replace("Built-in magnetic suction - ", "").replace("Built-in magnetic suction-", "").strip().upper()

    draw.rounded_rectangle([545, 715, 785, 775], radius=12, fill=(18, 18, 22, 255), outline=(70, 70, 75, 255), width=1)
    bbox = draw.textbbox((0, 0), clean_label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    cx = 545 + (240 - tw) / 2
    cy = 715 + (60 - th) / 2 - 2
    draw.text((cx, cy), clean_label, fill=(245, 245, 245, 255), font=font)

    im.convert("RGB").save(out_path, quality=95)
    return out_path

def translate_stand_tpu_gallery_01(img_path: str, out_path: Optional[str] = None):
    """Translates Honor X series Stand TPU showcase gallery_01.jpg in-place."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(im)

    # Top banner: cover orange/white [0, 0, 800, 120]
    draw.rectangle([0, 0, 800, 120], fill=(235, 80, 20, 255))
    font_top = get_font("C:/Windows/Fonts/arialbd.ttf", 36)
    draw.text((120, 40), "PREMIUM MAGNETIC STAND CASE", fill=(255, 255, 255, 255), font=font_top)

    # Top right title: 磁吸支点壳 -> MAGNETIC STAND
    draw.rectangle([350, 130, 800, 240], fill=(235, 235, 238, 255))
    font_h1 = get_font("C:/Windows/Fonts/arialbd.ttf", 40)
    draw.text((370, 150), "MAGNETIC STAND", fill=(25, 25, 25, 255), font=font_h1)

    # Pill badges: 四角气囊防摔, 可横竖支撑
    draw.rounded_rectangle([610, 250, 785, 305], radius=15, fill=(100, 105, 115, 255))
    font_badge = get_font("C:/Windows/Fonts/segoeuib.ttf", 18)
    draw.text((625, 265), "4-CORNER AIRBAG", fill=(255, 255, 255, 255), font=font_badge)

    draw.rounded_rectangle([660, 325, 785, 380], radius=15, fill=(25, 25, 28, 255))
    draw.text((675, 342), "DUAL STAND", fill=(255, 255, 255, 255), font=font_badge)

    # Bottom left model tag: 适用荣耀X系列 -> FOR HONOR X SERIES
    draw.rectangle([20, 820, 360, 885], fill=(244, 244, 245, 255))
    font_model = get_font("C:/Windows/Fonts/arialbd.ttf", 26)
    draw.text((35, 835), "HONOR X SERIES", fill=(30, 30, 30, 255), font=font_model)

    # Bottom orange banner: cover [0, 890, 800, 1000]
    draw.rectangle([0, 890, 800, 1000], fill=(235, 80, 20, 255))
    font_btm = get_font("C:/Windows/Fonts/arialbd.ttf", 34)
    draw.text((70, 925), "OFFICIAL FACTORY DIRECT | FAST DISPATCH", fill=(255, 255, 255, 255), font=font_btm)

    im.convert("RGB").save(out_path, quality=95)
    return out_path

def translate_stand_tpu_sku(img_path: str, color_name: str, out_path: Optional[str] = None):
    """Translates Honor X series Stand TPU SKU images in-place."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(im)

    # Top title: cover [20, 20, 580, 125] with off-white
    draw.rectangle([20, 20, 580, 125], fill=(244, 244, 244, 255))
    font_title = get_font("C:/Windows/Fonts/arialbd.ttf", 36)
    draw.text((30, 45), "MAGNETIC STAND CASE", fill=(25, 25, 25, 255), font=font_title)

    # Color pill: cover [25, 135, 250, 200]
    draw.rectangle([25, 135, 250, 200], fill=(244, 244, 244, 255))
    font_pill = get_font("C:/Windows/Fonts/arialbd.ttf", 20)

    clean_color = color_name.upper().strip()
    bbox = draw.textbbox((0, 0), clean_color, font=font_pill)
    tw = bbox[2] - bbox[0]
    pw = max(tw + 40, 130)

    draw.rounded_rectangle([30, 142, 30 + pw, 192], radius=12, fill=(60, 60, 65, 255))
    draw.text((30 + (pw - tw) / 2, 154), clean_color, fill=(255, 255, 255, 255), font=font_pill)

    # Bullet points: cover [25, 265, 280, 450]
    draw.rectangle([25, 265, 280, 450], fill=(244, 244, 244, 255))
    font_bullet = get_font("C:/Windows/Fonts/segoeuib.ttf", 17)
    bullets = [
        "• Multi-Angle Stand",
        "• Integrated Lens Film",
        "• Airbag Shockproof",
        "• Ultra-Clear Anti-Yellow"
    ]
    y_start = 280
    for b in bullets:
        draw.text((30, y_start), b, fill=(40, 40, 45, 255), font=font_bullet)
        y_start += 38

    # Bottom disclaimer: cover [15, 725, 280, 785]
    draw.rectangle([15, 725, 280, 785], fill=(235, 235, 236, 255))
    font_disc = get_font("C:/Windows/Fonts/segoeui.ttf", 12)
    draw.text((25, 735), "Tailored precision cutouts", fill=(110, 110, 115, 255), font=font_disc)
    draw.text((25, 755), "for your selected phone model", fill=(110, 110, 115, 255), font=font_disc)

    im.convert("RGB").save(out_path, quality=95)
    return out_path

def translate_magnetic_matte_sku(img_path: str, out_path: Optional[str] = None, color_name: str = "TITANIUM GRAY", model_name: str = "Honor x80i"):
    """Translates 1600x1600 Magnetic Matte AF Lens SKU cover images in-place."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(im)

    # 1. Box side text (cover Chinese vertical text)
    draw.rectangle([25, 300, 105, 1100], fill=(68, 72, 80))
    font_box = get_font("C:/Windows/Fonts/arialbd.ttf", 32)
    txt_img = Image.new("RGBA", (750, 60), (0, 0, 0, 0))
    d_txt = ImageDraw.Draw(txt_img)
    d_txt.text((0, 10), "MAGNETIC AF LENS PROTECTIVE CASE", fill=(200, 205, 215, 255), font=font_box)
    rotated = txt_img.rotate(90, expand=True)
    im.paste(rotated, (35, 320), rotated)

    # 2. Right side text container
    bg_color = (244, 244, 246)
    draw.rectangle([880, 240, 1550, 1000], fill=bg_color)

    # Top badge
    draw.rounded_rectangle([890, 250, 1530, 380], radius=30, fill=(255, 228, 196), outline=(30, 30, 30), width=4)
    draw.rounded_rectangle([900, 260, 1140, 370], radius=24, fill=(15, 15, 15))
    font_badge_w = get_font("C:/Windows/Fonts/arialbd.ttf", 44)
    draw.text((920, 290), "UPGRADE", fill=(255, 255, 255), font=font_badge_w)
    font_badge_t = get_font("C:/Windows/Fonts/arialbd.ttf", 48)
    draw.text((1170, 288), "AF LENS FILM", fill=(20, 20, 20), font=font_badge_t)

    # Subtitle [1:1 PRECISION FIT]
    font_sub = get_font("C:/Windows/Fonts/arialbd.ttf", 46)
    draw.text((1000, 415), "[ 1:1 PRECISION FIT ]", fill=(40, 40, 40), font=font_sub)

    # Big color title
    font_color = get_font("C:/Windows/Fonts/arialbd.ttf", 74)
    c_str = color_name.upper()
    cbbox = draw.textbbox((0, 0), c_str, font=font_color)
    cw = cbbox[2] - cbbox[0]
    draw.text((880 + (670 - cw) / 2, 520), c_str, fill=(15, 15, 15), font=font_color)

    # Craft description
    font_craft = get_font("C:/Windows/Fonts/segoeuib.ttf", 36)
    draw.text((890, 780), "FULL LENS COVER | 3D LASER CRAFT", fill=(60, 60, 60), font=font_craft)

    # Model pill (exact replacement of original black pill)
    draw.rounded_rectangle([900, 880, 1530, 970], radius=45, fill=(15, 15, 15))
    font_model = get_font("C:/Windows/Fonts/arialbd.ttf", 42)
    m_str = f"FOR: {model_name.upper()}"
    mbbox = draw.textbbox((0, 0), m_str, font=font_model)
    mw = mbbox[2] - mbbox[0]
    draw.text((900 + (630 - mw) / 2, 905), m_str, fill=(255, 255, 255), font=font_model)

    # 3. Bottom 3 badge pills
    # Badge 1
    draw.rounded_rectangle([1300, 1050, 1540, 1130], radius=40, fill=(255, 235, 215), outline=(30, 30, 30), width=3)
    font_sm = get_font("C:/Windows/Fonts/arialbd.ttf", 20)
    draw.text((1315, 1075), "BUILT-IN LENS FILM", fill=(30, 30, 30), font=font_sm)

    # Badge 2
    draw.rounded_rectangle([1350, 1240, 1590, 1320], radius=40, fill=(255, 235, 215), outline=(30, 30, 30), width=3)
    draw.text((1365, 1265), "CLEAR PHOTOS", fill=(30, 30, 30), font=font_sm)

    # Badge 3
    draw.rounded_rectangle([1270, 1440, 1580, 1520], radius=40, fill=(255, 235, 215), outline=(30, 30, 30), width=3)
    draw.text((1290, 1465), "ANTI-GLARE HD", fill=(30, 30, 30), font=font_sm)

    im.save(out_path, quality=95)
    return out_path

def translate_magnetic_matte_gallery_02(img_path: str, out_path: Optional[str] = None):
    """Translates gallery_02.jpg (scratch resistance)."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(im)
    draw.rectangle([30, 30, 1450, 270], fill=(7, 9, 14))
    font_title = get_font("C:/Windows/Fonts/arialbd.ttf", 64)
    font_sub = get_font("C:/Windows/Fonts/segoeuib.ttf", 36)
    font_org = get_font("C:/Windows/Fonts/arialbd.ttf", 38)
    draw.text((50, 45), "SCRATCH & ABRASION RESISTANT", fill=(255, 255, 255), font=font_title)
    draw.text((50, 145), "Premium Micro-Matte Craftsmanship • Prevents Daily Scuffs", fill=(190, 195, 205), font=font_sub)
    draw.text((50, 205), "DURABLE HARD PC MATERIAL", fill=(255, 120, 0), font=font_org)
    im.save(out_path, quality=95)
    return out_path

def translate_magnetic_matte_gallery_03(img_path: str, out_path: Optional[str] = None):
    """Translates gallery_03.jpg (matte texture)."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(im)
    draw.rectangle([40, 30, 1480, 250], fill=(30, 40, 52))
    font_title = get_font("C:/Windows/Fonts/arialbd.ttf", 64)
    font_pill = get_font("C:/Windows/Fonts/arialbd.ttf", 34)
    draw.text((60, 45), "FLAGSHIP LUXURY MATTE", fill=(255, 255, 255), font=font_title)
    draw.rounded_rectangle([60, 145, 660, 220], radius=35, fill=(200, 25, 25))
    draw.text((90, 162), "SILKY TOUCH • ULTRA-PREMIUM", fill=(255, 255, 255), font=font_pill)

    # Bottom badge
    draw.rectangle([1080, 1290, 1560, 1550], fill=(20, 25, 35))
    draw.rounded_rectangle([1080, 1300, 1550, 1400], radius=20, fill=(200, 25, 25))
    draw.text((1110, 1325), "BUILT-IN LENS FILM", fill=(255, 255, 255), font=font_pill)
    draw.text((1110, 1435), "SLIM STRAIGHT EDGE", fill=(255, 255, 255), font=font_pill)
    im.save(out_path, quality=95)
    return out_path

def translate_magnetic_matte_gallery_04(img_path: str, out_path: Optional[str] = None):
    """Translates gallery_04.jpg (dustproof mesh)."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(im)
    draw.rectangle([30, 30, 800, 380], fill=(15, 18, 26))
    font_title = get_font("C:/Windows/Fonts/arialbd.ttf", 58)
    font_sub = get_font("C:/Windows/Fonts/segoeuib.ttf", 32)
    font_org = get_font("C:/Windows/Fonts/arialbd.ttf", 36)
    draw.text((45, 45), "PRECISION DUST MESH", fill=(255, 255, 255), font=font_title)
    draw.text((45, 135), "FEAR NO DUST OR SAND", fill=(255, 255, 255), font=font_title)
    draw.text((45, 230), "ANTI-FINGERPRINT & ANTI-SWEAT", fill=(190, 195, 205), font=font_sub)
    draw.text((45, 290), "1:1 PRECISION FIT", fill=(255, 120, 0), font=font_org)

    # Bottom badge
    draw.rounded_rectangle([1060, 1440, 1520, 1540], radius=40, fill=(255, 230, 205), outline=(30, 30, 30), width=4)
    font_mesh = get_font("C:/Windows/Fonts/arialbd.ttf", 28)
    draw.text((1085, 1470), "HONEYCOMB DUST MESH", fill=(30, 30, 30), font=font_mesh)
    im.save(out_path, quality=95)
    return out_path

def translate_magnetic_matte_gallery_05(img_path: str, out_path: Optional[str] = None):
    """Translates gallery_05.jpg (comparison)."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(im)
    draw.rectangle([40, 40, 1560, 300], fill=(12, 16, 22))
    font_title = get_font("C:/Windows/Fonts/arialbd.ttf", 64)
    font_sub = get_font("C:/Windows/Fonts/segoeuib.ttf", 36)
    font_org = get_font("C:/Windows/Fonts/arialbd.ttf", 38)
    draw.text((60, 50), "UPGRADED FRAME & BACKPLATE", fill=(255, 255, 255), font=font_title)
    draw.text((60, 150), "Smooth Cool Matte Touch • Superior To Bare Phone Feel", fill=(190, 195, 205), font=font_sub)
    draw.text((60, 220), "ANTI-FINGERPRINT • ANTI-OXIDATION", fill=(255, 120, 0), font=font_org)

    # Badges
    font_badge = get_font("C:/Windows/Fonts/arialbd.ttf", 32)
    draw.rectangle([135, 880, 215, 1160], fill=(12, 16, 22))
    draw.rounded_rectangle([135, 890, 215, 1150], radius=35, fill=(255, 120, 0))
    t1 = Image.new("RGBA", (240, 60), (0, 0, 0, 0))
    dt1 = ImageDraw.Draw(t1)
    dt1.text((10, 10), "OUR CASE", fill=(255, 255, 255), font=font_badge)
    rt1 = t1.rotate(90, expand=True)
    im.paste(rt1, (145, 900), rt1)

    draw.rectangle([815, 800, 895, 1100], fill=(12, 16, 22))
    draw.rounded_rectangle([815, 810, 895, 1090], radius=35, fill=(120, 125, 135))
    t2 = Image.new("RGBA", (260, 60), (0, 0, 0, 0))
    dt2 = ImageDraw.Draw(t2)
    dt2.text((10, 10), "STANDARD CASE", fill=(255, 255, 255), font=font_badge)
    rt2 = t2.rotate(90, expand=True)
    im.paste(rt2, (825, 820), rt2)

    im.save(out_path, quality=95)
    return out_path

def translate_frosted_pc_gallery_01(img_path: str, out_path: Optional[str] = None):
    """Translates Realme Neo8/Neo7 Frosted PC gallery_01 in-place."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(im)
    bg = (175, 175, 175, 255)

    # Title '磁吸磨砂壳': y=[250, 360], x=[540, 800]
    draw.rectangle([540, 250, 800, 360], fill=bg)
    font_title = get_font("C:/Windows/Fonts/arialbd.ttf", 36)
    draw.text((560, 275), "MAGNETIC", fill=(255, 255, 255, 255), font=font_title)
    draw.text((560, 315), "FROSTED", fill=(255, 255, 255, 255), font=font_title)

    # Icon labels: y=[415, 455], x=[560, 800]
    draw.rectangle([560, 415, 800, 455], fill=bg)
    font_icon = get_font("C:/Windows/Fonts/segoeui.ttf", 13)
    draw.text((580, 422), "FROSTED", fill=(255, 255, 255, 255), font=font_icon)
    draw.text((670, 422), "DROP-PROOF", fill=(255, 255, 255, 255), font=font_icon)
    draw.text((760, 422), "ANTI-SMUDGE", fill=(255, 255, 255, 255), font=font_icon)

    # '适用于:' y=[480, 520], x=[570, 720]
    draw.rectangle([570, 480, 720, 520], fill=bg)
    font_comp = get_font("C:/Windows/Fonts/segoeuib.ttf", 22)
    draw.text((585, 488), "COMPATIBLE:", fill=(255, 255, 255, 255), font=font_comp)

    im.convert("RGB").save(out_path, quality=95)
    return out_path

def translate_frosted_pc_gallery_03(img_path: str, out_path: Optional[str] = None):
    """Translates Realme Neo8/Neo7 raised camera frame gallery_03 in-place."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(im)

    draw.rectangle([20, 20, 480, 250], fill=(236, 222, 205, 255))
    font_h1 = get_font("C:/Windows/Fonts/arialbd.ttf", 36)
    draw.text((35, 45), "RAISED CAMERA FRAME", fill=(255, 255, 255, 255), font=font_h1)
    draw.text((35, 95), "LENS PROTECTION", fill=(255, 255, 255, 255), font=font_h1)

    font_sub = get_font("C:/Windows/Fonts/segoeui.ttf", 16)
    draw.text((35, 160), "Precision bezel design shields camera lenses", fill=(70, 60, 55, 255), font=font_sub)
    draw.text((35, 185), "against scratches, drops, and everyday wear.", fill=(70, 60, 55, 255), font=font_sub)

    im.convert("RGB").save(out_path, quality=95)
    return out_path

def translate_frosted_pc_sku(img_path: str, color_name: str, model_name: str = "Realme Neo8", out_path: Optional[str] = None):
    """Translates Realme Neo8/Neo7 Frosted PC SKU image top banner in-place."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(im)

    draw.rectangle([180, 20, 620, 150], fill=(246, 246, 246, 255))
    font_title = get_font("C:/Windows/Fonts/arialbd.ttf", 30)
    draw.text((215, 38), "FROSTED PC · MAGNETIC", fill=(25, 25, 25, 255), font=font_title)

    font_p = get_font("C:/Windows/Fonts/arialbd.ttf", 15)
    model_label = f"FOR {model_name.upper()}"
    draw.rounded_rectangle([190, 95, 410, 138], radius=16, fill=(255, 255, 255, 255), outline=(220, 220, 225, 255), width=1)
    draw.text((212, 107), model_label, fill=(30, 30, 35, 255), font=font_p)

    clean_color = color_name.upper().strip()
    bbox = draw.textbbox((0, 0), clean_color, font=font_p)
    tw = bbox[2] - bbox[0]
    cw = max(tw + 36, 130)
    draw.rounded_rectangle([425, 95, 425 + cw, 138], radius=16, fill=(20, 20, 25, 255))
    draw.text((425 + (cw - tw) / 2, 107), clean_color, fill=(255, 255, 255, 255), font=font_p)

    im.convert("RGB").save(out_path, quality=95)
    return out_path

def translate_graphene_banner_800(img_path: str, color_name: str = "", model_name: str = "Realme Neo8", out_path: Optional[str] = None):
    """Translates 800x800 Graphene Cooling Silicone showcase & SKU images in-place."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(im)

    bg_fill = (150, 168, 190, 255)
    draw.rounded_rectangle([35, 20, 765, 175], radius=16, fill=bg_fill, outline=(180, 195, 215, 255), width=2)

    font_title = get_font("C:/Windows/Fonts/arialbd.ttf", 30)
    draw.text((55, 38), "GRAPHENE COOLING · AIRBAG ARMOR", fill=(255, 255, 255, 255), font=font_title)

    font_badge = get_font("C:/Windows/Fonts/arialbd.ttf", 15)
    model_str = f"FOR {model_name.upper()}"
    draw.rounded_rectangle([55, 105, 275, 148], radius=12, fill=(255, 255, 255, 255))
    draw.text((75, 117), model_str, fill=(35, 45, 60, 255), font=font_badge)

    if color_name:
        clean_col = color_name.upper().strip()
        bbox = draw.textbbox((0, 0), clean_col, font=font_badge)
        tw = bbox[2] - bbox[0]
        cw = max(tw + 36, 140)
        draw.rounded_rectangle([290, 105, 290 + cw, 148], radius=12, fill=(30, 40, 55, 255))
        draw.text((290 + (cw - tw) / 2, 117), clean_col, fill=(255, 255, 255, 255), font=font_badge)
    else:
        draw.rounded_rectangle([290, 105, 520, 148], radius=12, fill=(30, 40, 55, 255))
        draw.text((310, 117), "MAGNETIC HEAT RELEASE", fill=(255, 255, 255, 255), font=font_badge)

    im.convert("RGB").save(out_path, quality=95)
    return out_path

def translate_graphene_gallery_04(img_path: str, out_path: Optional[str] = None):
    """Translates 1440x1440 Graphene Heat Conduction technical graphic in-place."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(im)

    draw.rounded_rectangle([80, 80, 1360, 270], radius=20, fill=(10, 15, 22, 240), outline=(40, 55, 75, 255), width=2)
    font_h1 = get_font("C:/Windows/Fonts/arialbd.ttf", 52)
    draw.text((120, 110), "GRAPHENE HEAT CONDUCTION MATRIX", fill=(255, 255, 255, 255), font=font_h1)

    font_sub = get_font("C:/Windows/Fonts/segoeui.ttf", 26)
    draw.text((120, 185), "Snowflake magnetic thermal sheet accelerates CPU cooling during gaming.", fill=(160, 185, 215, 255), font=font_sub)

    im.convert("RGB").save(out_path, quality=95)
    return out_path

def translate_graphene_gallery_05(img_path: str, out_path: Optional[str] = None):
    """Translates 1440x1440 Airbag Drop Protection graphic in-place."""
    if out_path is None:
        out_path = img_path
    im = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(im)

    draw.rounded_rectangle([80, 70, 1360, 260], radius=20, fill=(235, 242, 248, 240), outline=(200, 215, 230, 255), width=2)
    font_h1 = get_font("C:/Windows/Fonts/arialbd.ttf", 52)
    draw.text((120, 100), "AIRBAG CORNER DROP PROTECTION", fill=(20, 30, 45, 255), font=font_h1)

    font_sub = get_font("C:/Windows/Fonts/segoeui.ttf", 26)
    draw.text((120, 175), "Reinforced shock-absorbing silicone bumpers shield against hard drops.", fill=(80, 95, 115, 255), font=font_sub)

    im.convert("RGB").save(out_path, quality=95)
    return out_path

def translate_in_place(gallery_dir: str, sku_dir: str, material: str = "Liquid Silicone", model_name: str = "Realme Neo8"):
    """
    Translates all images containing non-English text directly in-place,
    replacing the original file in \\gallery\\ and \\sku\\.
    """
    is_tpu = "tpu" in material.lower()
    is_graphene = ("neo8" in model_name.lower() or "neo8" in gallery_dir.lower()) and "silicone" in material.lower() and "liquid" not in material.lower()
    is_frosted_pc = ("neo8" in model_name.lower() or "neo7" in model_name.lower()) and ("pc" in material.lower() or "pet" in material.lower() or "hard" in material.lower())
    is_pc = ("pc" in material.lower() or "hard" in material.lower() or "pet" in material.lower()) and not is_frosted_pc
    is_stand = is_tpu and ("x80" in model_name.lower() or "x70" in model_name.lower() or "x60" in model_name.lower() or "stand" in gallery_dir.lower())
    is_moire = ("silicone" in material.lower() and ("honor" in model_name.lower() or "600 lite" in model_name.lower())) or "moire" in material.lower() or "moire" in gallery_dir.lower()

    # 1. Process gallery images
    if os.path.exists(gallery_dir):
        for f in os.listdir(gallery_dir):
            if not f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                continue
            path = os.path.join(gallery_dir, f)
            if is_graphene:
                if "01" in f:
                    translate_graphene_banner_800(path, "TERRACOTTA ORANGE", model_name, path)
                    print(f"    [✓] In-place translated Graphene Silicone showcase: {f}")
                elif "02" in f:
                    translate_graphene_banner_800(path, "MATTE GRAY", model_name, path)
                    print(f"    [✓] In-place translated Graphene Silicone showcase: {f}")
                elif "03" in f:
                    translate_graphene_banner_800(path, "OBSIDIAN BLACK", model_name, path)
                    print(f"    [✓] In-place translated Graphene Silicone showcase: {f}")
                elif "04" in f:
                    translate_graphene_gallery_04(path, path)
                    print(f"    [✓] In-place translated Graphene Heat Conduction: {f}")
                elif "05" in f:
                    translate_graphene_gallery_05(path, path)
                    print(f"    [✓] In-place translated Graphene Airbag Protection: {f}")
            elif is_frosted_pc:
                if "01" in f:
                    translate_frosted_pc_gallery_01(path, path)
                    print(f"    [✓] In-place translated Frosted PC showcase: {f}")
                elif "02" in f:
                    translate_frosted_pc_sku(path, color_name="PEAK ROCK", model_name=model_name, out_path=path)
                    print(f"    [✓] In-place translated Frosted PC gallery: {f}")
                elif "03" in f:
                    translate_frosted_pc_gallery_03(path, path)
                    print(f"    [✓] In-place translated Frosted PC lens gallery: {f}")
                else:
                    print(f"    [i] Skipped clean 3D graphic image: {f}")
            elif is_pc:
                if "01" in f:
                    translate_magnetic_matte_sku(path, path, color_name="DESERT GOLD", model_name=model_name)
                    print(f"    [✓] In-place translated Hard PC showcase: {f}")
                elif "02" in f:
                    translate_magnetic_matte_gallery_02(path, path)
                    print(f"    [✓] In-place translated Hard PC gallery: {f}")
                elif "03" in f:
                    translate_magnetic_matte_gallery_03(path, path)
                    print(f"    [✓] In-place translated Hard PC gallery: {f}")
                elif "04" in f:
                    translate_magnetic_matte_gallery_04(path, path)
                    print(f"    [✓] In-place translated Hard PC gallery: {f}")
                elif "05" in f:
                    translate_magnetic_matte_gallery_05(path, path)
                    print(f"    [✓] In-place translated Hard PC gallery: {f}")
                else:
                    print(f"    [i] Clean image verified: {f}")
            elif is_stand:
                if "01" in f:
                    translate_stand_tpu_gallery_01(path, path)
                    print(f"    [✓] In-place translated Stand TPU showcase: {f}")
                else:
                    print(f"    [i] Skipped clean studio/lifestyle image: {f}")
            elif is_moire:
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
            if is_graphene:
                col_name = "OBSIDIAN BLACK"
                if "-GY-" in f:
                    col_name = "MATTE GRAY"
                elif "-OR-" in f:
                    col_name = "TERRACOTTA ORANGE"
                translate_graphene_banner_800(path, col_name, model_name, path)
                print(f"    [✓] In-place translated Graphene Silicone SKU ({col_name}): {f}")
            elif is_frosted_pc:
                col_name = "CLASSIC BLACK"
                if "-RK-" in f:
                    col_name = "PEAK ROCK"
                elif "-GD-" in f:
                    col_name = "DESERT GOLD"
                elif "-BL-" in f:
                    col_name = "WAVE BLUE"
                elif "-PK-" in f:
                    col_name = "SAKURA PINK"
                elif "-CG-" in f:
                    col_name = "CARBON GRAY"
                elif "-PR-" in f:
                    col_name = "SUNSET PURPLE"
                elif "-TG-" in f:
                    col_name = "TITANIUM GRAY"
                elif "-BK-" in f:
                    col_name = "CLASSIC BLACK"
                translate_frosted_pc_sku(path, color_name=col_name, model_name=model_name, out_path=path)
                print(f"    [✓] In-place translated Frosted PC SKU ({col_name}): {f}")
            elif is_pc:
                color_name = "TITANIUM GRAY"
                if "-GY-" in f:
                    color_name = "TITANIUM GRAY"
                elif "-WT-" in f:
                    color_name = "SILVER WHITE"
                elif "-GN-" in f:
                    color_name = "FEITIAN GREEN"
                elif "-GD-" in f:
                    color_name = "DESERT GOLD"
                elif "-BK-" in f:
                    color_name = "GRAPHITE BLACK"
                translate_magnetic_matte_sku(path, path, color_name=color_name, model_name=model_name)
                print(f"    [✓] In-place translated Hard PC SKU: {f} ({color_name})")
            elif is_stand:
                col_name = "CLEAR"
                if "-SV-" in f or "silver" in f.lower():
                    col_name = "SILVER"
                elif "-BK-" in f or "black" in f.lower():
                    col_name = "CLASSIC BLACK"
                elif "-PR-" in f or "purple" in f.lower():
                    col_name = "DEEP PURPLE"
                elif "-BL-" in f or "blue" in f.lower():
                    col_name = "PACIFIC BLUE"
                elif "-PK-" in f or "pink" in f.lower():
                    col_name = "ROSE PINK"
                elif "-GN-" in f or "green" in f.lower():
                    col_name = "PINE GREEN"
                elif "-CL-" in f or "transparent" in f.lower():
                    col_name = "CRYSTAL CLEAR"
                translate_stand_tpu_sku(path, col_name, path)
                print(f"    [✓] In-place translated Stand TPU SKU ({col_name}): {f}")
            elif is_moire:
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
