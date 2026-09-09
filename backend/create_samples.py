"""Script to generate realistic test packaging label images for Legal Metrology inspection."""

import os
from PIL import Image, ImageDraw, ImageFont

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "samples")
os.makedirs(DATA_DIR, exist_ok=True)

def get_font(size: int, bold: bool = False):
    try:
        # Windows system fonts
        font_name = "arialbd.ttf" if bold else "arial.ttf"
        return ImageFont.truetype(f"C:\\Windows\\Fonts\\{font_name}", size)
    except Exception:
        return ImageFont.load_default()

def create_compliant_sample():
    width, height = 900, 1100
    img = Image.new("RGB", (width, height), color="#FFFDF7")
    draw = ImageDraw.Draw(img)

    # Outer packaging border
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline="#2B4C3F", width=6)
    draw.rectangle([(30, 30), (width - 30, height - 30)], outline="#D4AF37", width=2)

    # Header banner
    draw.rectangle([(32, 32), (width - 32, 160)], fill="#1E4D3E")
    draw.text((width // 2, 70), "ASSAM GOLD PREMIUM TEA", font=get_font(36, True), fill="#FFFFFF", anchor="mm")
    draw.text((width // 2, 120), "100% PURE CTC LEAF TEA • ESTATE BLEND", font=get_font(18, False), fill="#E2D4A8", anchor="mm")

    # Front brand badge
    draw.ellipse([(width // 2 - 60, 190), (width // 2 + 60, 310)], fill="#F2ECE1", outline="#D4AF37", width=3)
    draw.text((width // 2, 250), "PACKCHECK\nCERTIFIED", font=get_font(16, True), fill="#1E4D3E", anchor="mm", align="center")

    # Principal Display Panel Box (Legal Metrology Declarations)
    pdp_top = 340
    draw.rectangle([(60, pdp_top), (width - 60, height - 60)], fill="#FBF9F2", outline="#8FA89B", width=2)

    # Mandatory Declarations Heading
    draw.text((80, pdp_top + 30), "MANDATORY DECLARATIONS (LEGAL METROLOGY):", font=get_font(20, True), fill="#16382C")
    draw.line([(80, pdp_top + 60), (width - 80, pdp_top + 60)], fill="#CCD9D2", width=2)

    fields = [
        ("Product Name:", "Assam Gold CTC Black Tea"),
        ("Net Quantity:", "500 g"),
        ("Maximum Retail Price (MRP):", "₹ 245.00 (Inclusive of all taxes)"),
        ("Unit Sale Price:", "₹ 0.49 per g"),
        ("Month & Year of Mfg:", "08/2026"),
        ("Batch / Lot No:", "LOT-AG26-908B"),
        ("Best Before:", "12 Months from Packaging"),
        ("Manufactured By:", "Himalayan Highlands Tea Estates Pvt. Ltd."),
        ("Manufacturer Address:", "Plot 42, Tea Park Road, Dibrugarh, Assam - 786001, India"),
        ("Packed By:", "PackCheck Agro Products LLP, Shed 9, MIDC, Pune - 411018"),
        ("Country of Origin:", "India"),
        ("Consumer Care Details:", "Toll-Free: 1800-209-8899 | Email: care@assamgoldtea.in"),
        ("Customer Care Address:", "Customer Support Cell, Plot 42, Tea Park Road, Dibrugarh, Assam - 786001")
    ]

    curr_y = pdp_top + 80
    for label, val in fields:
        draw.text((80, curr_y), label, font=get_font(18, True), fill="#2C3E50")
        draw.text((380, curr_y), val, font=get_font(18, False), fill="#1B1B1B")
        curr_y += 42

    # Barcode representation
    barcode_y = height - 120
    draw.text((80, barcode_y - 20), "EAN-13 BARCODE:", font=get_font(14, True), fill="#555555")
    # Draw simple vertical stripes
    stripe_x = 80
    for w in [3, 1, 4, 2, 1, 3, 2, 4, 1, 2, 3, 1, 4, 2, 1, 3, 2, 4, 2, 1, 3, 2, 4, 1, 3]:
        draw.rectangle([(stripe_x, barcode_y), (stripe_x + w, barcode_y + 40)], fill="#000000")
        stripe_x += w + 3
    draw.text((stripe_x + 20, barcode_y + 12), "8 901030 892014", font=get_font(16, True), fill="#000000")

    filepath = os.path.join(DATA_DIR, "compliant_tea_sample.jpg")
    img.save(filepath, quality=95)
    print(f"Generated compliant sample: {filepath}")

def create_non_compliant_sample():
    width, height = 900, 1100
    img = Image.new("RGB", (width, height), color="#FFF5F5")
    draw = ImageDraw.Draw(img)

    # Outer packaging border
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline="#B91C1C", width=6)

    # Header banner
    draw.rectangle([(32, 32), (width - 32, 160)], fill="#991B1B")
    draw.text((width // 2, 70), "CRUNCHY BITES MASALA CHIPS", font=get_font(34, True), fill="#FFFFFF", anchor="mm")
    draw.text((width // 2, 120), "EXTRA SPICY POTATO CRISPS", font=get_font(18, False), fill="#FEE2E2", anchor="mm")

    pdp_top = 220
    draw.rectangle([(60, pdp_top), (width - 60, height - 60)], fill="#FFFFFF", outline="#FCA5A5", width=2)
    draw.text((80, pdp_top + 30), "PRODUCT INFORMATION:", font=get_font(20, True), fill="#7F1D1D")
    draw.line([(80, pdp_top + 60), (width - 80, pdp_top + 60)], fill="#FECACA", width=2)

    # Defect: missing Net Qty unit of measure or non-standard, missing MRP tax declaration, missing consumer care details
    fields = [
        ("Product Name:", "Crunchy Bites Masala Chips"),
        ("Net Weight:", "75"),  # Missing legal unit! (e.g. g or kg)
        ("Price:", "30"),       # Missing 'MRP', missing 'inclusive of all taxes'
        ("Date of Packing:", "05/2026"),
        ("Mfg By:", "FastSnacks Industries"),
        ("Mfg Address:", "Industrial Area, Phase 2, Delhi"),
        # Consumer Care details deliberately MISSING
    ]

    curr_y = pdp_top + 80
    for label, val in fields:
        draw.text((80, curr_y), label, font=get_font(18, True), fill="#2C3E50")
        draw.text((360, curr_y), val, font=get_font(18, False), fill="#1B1B1B")
        curr_y += 50

    draw.text((80, curr_y + 40), "[NOTICE: Consumer helpline and MRP inclusive text missing]", font=get_font(16, True), fill="#B91C1C")

    filepath = os.path.join(DATA_DIR, "non_compliant_snack_sample.jpg")
    img.save(filepath, quality=95)
    print(f"Generated non-compliant sample: {filepath}")

if __name__ == "__main__":
    create_compliant_sample()
    create_non_compliant_sample()
