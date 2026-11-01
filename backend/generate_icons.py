from PIL import Image, ImageDraw, ImageFont
import os

out_dir = r"c:\PROJECTS\MEDIVERIFY\frontend\public\icons"
os.makedirs(out_dir, exist_ok=True)

def make_icon(size):
    img = Image.new('RGB', (size, size), (10, 15, 30))
    draw = ImageDraw.Draw(img)
    cx, cy, s = size // 2, size // 2, size

    # Shield polygon
    pts = [
        (cx, int(s*.09)),
        (int(s*.83), int(s*.22)),
        (int(s*.83), int(s*.55)),
        (cx, int(s*.92)),
        (int(s*.17), int(s*.55)),
        (int(s*.17), int(s*.22)),
    ]
    draw.polygon(pts, fill=(13, 60, 120))
    draw.polygon(pts, outline=(13, 145, 225), width=max(2, size//48))

    # Medical cross
    a, e = int(s*.10), int(s*.20)
    draw.rectangle([cx-a, cy-e, cx+a, cy+e], fill=(255,255,255))
    draw.rectangle([cx-e, cy-a, cx+e, cy+a], fill=(255,255,255))

    # "MV" label
    fsz = max(10, size // 10)
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", fsz)
    except:
        font = ImageFont.load_default()
    bb = draw.textbbox((0,0), "MV", font=font)
    draw.text((cx-(bb[2]-bb[0])//2, int(s*.74)), "MV", font=font, fill=(13,145,225))
    return img

for sz, nm in [(192,"icon-192.png"),(512,"icon-512.png")]:
    p = os.path.join(out_dir, nm)
    make_icon(sz).save(p, "PNG")
    print(f"OK: {p}")

print("ICONS GENERATED")
