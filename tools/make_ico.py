import struct
from pathlib import Path

def main():
    icons_dir = Path(__file__).resolve().parent.parent / "icons"
    img_path = icons_dir / "kiri_logo.png"
    if not img_path.exists():
        img_path = icons_dir / "kiri_logo.jpg"
    
    img_data = img_path.read_bytes()
    # Windows Icon Format:
    # ICONDIR (6 bytes): Reserved(2), Type(2)=1, Count(2)=1
    header = struct.pack("<HHH", 0, 1, 1)
    # ICONDIRENTRY (16 bytes): Width(1), Height(1), Colors(1), Reserved(1), Planes(2), BitCount(2), Size(4), Offset(4)
    # Width 0 and Height 0 represent 256x256
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(img_data), 22)
    ico_bytes = header + entry + img_data
    
    ico_path = icons_dir / "kiri.ico"
    ico_path.write_bytes(ico_bytes)
    print(f"Generated {ico_path} ({len(ico_bytes)} bytes)")

if __name__ == "__main__":
    main()
