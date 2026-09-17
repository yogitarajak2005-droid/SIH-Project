"""
Generate synthetic demo identity documents for testing VerifyAI.
All data is completely fictional/synthetic.
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def get_font(size):
    # Try standard Windows fonts or fall back to default
    font_paths = [
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\tahoma.ttf",
        "C:\\Windows\\Fonts\\cour.ttf"
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_card_base(draw, width=800, height=500, header_color=(24, 43, 73), bg_color=(245, 247, 250)):
    # Background
    draw.rectangle([(0, 0), (width, height)], fill=bg_color)
    
    # Outer border
    draw.rounded_rectangle([(10, 10), (width - 10, height - 10)], radius=16, outline=(180, 195, 215), width=3)
    
    # Header banner
    draw.rounded_rectangle([(15, 15), (width - 15, 95)], radius=10, fill=header_color)
    
    # Header text
    font_title = get_font(22)
    font_sub = get_font(12)
    font_badge = get_font(11)
    
    draw.text((35, 25), "FICTIONAL CITIZEN IDENTITY CREDENTIAL", fill=(255, 255, 255), font=font_title)
    draw.text((35, 60), "GOVERNMENT OF DEMO STATE • SYNTHETIC DOCUMENT FOR TESTING ONLY", fill=(140, 200, 255), font=font_sub)
    
    # Demo disclaimer watermark
    font_wm = get_font(28)
    draw.text((220, 240), "SYNTHETIC DEMO ONLY", fill=(225, 230, 240), font=font_wm)
    draw.text((220, 280), "NOT A REAL IDENTIFICATION", fill=(225, 230, 240), font=font_wm)

    # Photo Box
    photo_box = [(40, 120), (200, 320)]
    draw.rounded_rectangle(photo_box, radius=10, fill=(215, 225, 240), outline=(120, 150, 190), width=2)
    
    # Stylized Avatar Silhouette
    # Head
    draw.ellipse([(95, 155), (145, 215)], fill=(120, 140, 175))
    # Torso
    draw.chord([(60, 225), (180, 330)], start=180, end=360, fill=(120, 140, 175))
    draw.text((70, 330), "SYNTHETIC PHOTO", fill=(120, 140, 175), font=font_badge)

def create_valid_sample(output_path):
    img = Image.new("RGB", (800, 500), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw_card_base(draw)

    font_lbl = get_font(12)
    font_val = get_font(18)
    font_bold = get_font(20)
    font_mrz = get_font(16)

    # Fields
    x_lbl = 230
    x_val = 230
    
    # Document ID
    draw.text((x_lbl, 115), "DOCUMENT ID / NUMBER:", fill=(100, 115, 130), font=font_lbl)
    draw.text((x_val, 135), "DEMO-9824-XYZ", fill=(20, 35, 60), font=font_bold)

    # Full Name
    draw.text((x_lbl, 175), "NAME / FULL NAME:", fill=(100, 115, 130), font=font_lbl)
    draw.text((x_val, 195), "JOHNATHAN E. DOE", fill=(20, 35, 60), font=font_bold)

    # Date of Birth
    draw.text((x_lbl, 235), "DATE OF BIRTH (DOB):", fill=(100, 115, 130), font=font_lbl)
    draw.text((x_val, 255), "14/08/1992", fill=(20, 35, 60), font=font_val)

    # Gender & Nationality
    draw.text((450, 235), "GENDER:", fill=(100, 115, 130), font=font_lbl)
    draw.text((450, 255), "MALE", fill=(20, 35, 60), font=font_val)

    # Issue & Expiry
    draw.text((x_lbl, 295), "DATE OF ISSUE:", fill=(100, 115, 130), font=font_lbl)
    draw.text((x_val, 315), "10/01/2020", fill=(20, 35, 60), font=font_val)

    draw.text((450, 295), "EXPIRY DATE:", fill=(100, 115, 130), font=font_lbl)
    draw.text((450, 315), "09/01/2030", fill=(20, 35, 60), font=font_val)

    # Security Chip / Hologram placeholder
    draw.rounded_rectangle([(650, 130), (740, 210)], radius=8, fill=(235, 225, 190), outline=(190, 170, 110), width=2)
    draw.rectangle([(665, 145), (725, 195)], outline=(160, 140, 80), width=1)
    draw.text((662, 160), "CHIP", fill=(130, 110, 60), font=get_font(12))

    # Barcode/MRZ Band
    draw.rectangle([(20, 385), (780, 480)], fill=(230, 235, 245), outline=(190, 200, 215))
    draw.text((35, 400), "I<UTODEMO9824XYZ1<<<<<<<<<<<<<<<", fill=(30, 40, 55), font=font_mrz)
    draw.text((35, 435), "9208144M3001095UTO<<<<<<<<<<<8", fill=(30, 40, 55), font=font_mrz)

    img.save(output_path, quality=95)
    print(f"Generated {output_path}")

def create_blurry_sample(output_path):
    temp_valid = "temp_valid_sample.png"
    create_valid_sample(temp_valid)
    
    img = cv2.imread(temp_valid)
    # Apply strong blur & lower contrast
    blurred = cv2.GaussianBlur(img, (25, 25), 9)
    # Add noise & slight brightness loss
    matrix = np.ones(blurred.shape, dtype="uint8") * 20
    darkened = cv2.subtract(blurred, matrix)
    
    cv2.imwrite(output_path, darkened)
    if os.path.exists(temp_valid):
        os.remove(temp_valid)
    print(f"Generated {output_path}")

def create_inconsistent_sample(output_path):
    img = Image.new("RGB", (800, 500), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw_card_base(draw, header_color=(120, 40, 40))

    font_lbl = get_font(12)
    font_val = get_font(18)
    font_bold = get_font(20)
    font_mrz = get_font(16)

    x_lbl = 230
    x_val = 230
    
    # Missing / corrupted Document ID
    draw.text((x_lbl, 115), "DOCUMENT ID / NUMBER:", fill=(100, 115, 130), font=font_lbl)
    draw.text((x_val, 135), "??? INVALID-ID ???", fill=(180, 40, 40), font=font_bold)

    # Full Name missing proper format
    draw.text((x_lbl, 175), "NAME / FULL NAME:", fill=(100, 115, 130), font=font_lbl)
    draw.text((x_val, 195), "X1#9_TEST USER", fill=(180, 40, 40), font=font_bold)

    # Inconsistent / Invalid Date of Birth (year 2099 - future DOB!)
    draw.text((x_lbl, 235), "DATE OF BIRTH (DOB):", fill=(100, 115, 130), font=font_lbl)
    draw.text((x_val, 255), "31/02/2099", fill=(180, 40, 40), font=font_val)

    draw.text((450, 235), "GENDER:", fill=(100, 115, 130), font=font_lbl)
    draw.text((450, 255), "UNKNOWN", fill=(20, 35, 60), font=font_val)

    draw.text((x_lbl, 295), "DATE OF ISSUE:", fill=(100, 115, 130), font=font_lbl)
    draw.text((x_val, 315), "99/99/9999", fill=(180, 40, 40), font=font_val)

    # Low quality corrupt MRZ band
    draw.rectangle([(20, 385), (780, 480)], fill=(240, 220, 220), outline=(215, 180, 180))
    draw.text((35, 400), "I<UTOXXXXXXXXXX<<<<<CORRUPTED<<<<<<<", fill=(120, 30, 30), font=font_mrz)
    draw.text((35, 435), "9999999X9999999UTO<<<<<<<<<<<X", fill=(120, 30, 30), font=font_mrz)

    img.save(output_path, quality=85)
    print(f"Generated {output_path}")

if __name__ == "__main__":
    os.makedirs("static/samples", exist_ok=True)
    os.makedirs("media/temp", exist_ok=True)
    create_valid_sample("static/samples/sample_valid.png")
    create_blurry_sample("static/samples/sample_blurry.png")
    create_inconsistent_sample("static/samples/sample_inconsistent.png")
    print("All synthetic demo samples created successfully.")
