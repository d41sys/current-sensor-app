#!/usr/bin/env python3
"""
Generate application icons for Windows (.ico) and macOS (.icns)
This script creates a simple placeholder icon if no custom icon exists.

For production, replace with your own professional icon.
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow not installed. Install with: pip install Pillow")
    sys.exit(1)


def create_icon_image(size: int = 512) -> Image.Image:
    """Create a simple icon image with the app initials"""
    # Create image with gradient background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw rounded rectangle background (blue gradient effect)
    padding = size // 16
    corner_radius = size // 8
    
    # Background color (blue-600 from Tailwind)
    bg_color = (37, 99, 235)
    
    # Draw rounded rectangle
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=corner_radius,
        fill=bg_color
    )
    
    # Draw "CM" text (Current Monitor)
    text = "CM"
    
    # Try to use a nice font, fallback to default
    font_size = size // 3
    try:
        # Try common system fonts
        for font_name in ['Arial Bold', 'Helvetica Bold', 'SF Pro Display Bold', 'DejaVuSans-Bold']:
            try:
                font = ImageFont.truetype(font_name, font_size)
                break
            except (IOError, OSError):
                continue
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center the text
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - bbox[1]
    
    # Draw text in white
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    
    # Draw a small electrode grid icon below
    grid_size = size // 6
    grid_start_x = (size - grid_size * 3) // 2
    grid_start_y = size - padding - grid_size * 3 - size // 10
    cell_size = grid_size - 4
    
    for row in range(3):
        for col in range(3):
            cell_x = grid_start_x + col * grid_size
            cell_y = grid_start_y + row * grid_size
            # Vary the color slightly for each cell
            intensity = 200 + (row * 3 + col) * 5
            draw.rounded_rectangle(
                [cell_x, cell_y, cell_x + cell_size, cell_y + cell_size],
                radius=4,
                fill=(intensity, intensity, 255)
            )
    
    return img


def save_ico(img: Image.Image, path: Path):
    """Save image as Windows ICO file"""
    # ICO needs multiple sizes
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icons = []
    
    for size in sizes:
        resized = img.resize(size, Image.Resampling.LANCZOS)
        icons.append(resized)
    
    icons[0].save(path, format='ICO', sizes=[(s[0], s[1]) for s in sizes], append_images=icons[1:])
    print(f"Created: {path}")


def save_icns(img: Image.Image, path: Path):
    """Save image as macOS ICNS file"""
    # For ICNS, we need to create a temporary iconset folder
    # This is a simplified version - for production, use iconutil
    
    # Just save as PNG for now and let PyInstaller handle it
    # or use img2icns tool
    png_path = path.with_suffix('.png')
    img.save(png_path, format='PNG')
    print(f"Created: {png_path}")
    print(f"Note: Convert to .icns using: iconutil -c icns {path.parent}/icon.iconset")
    
    # Try to create iconset if on macOS
    if sys.platform == 'darwin':
        import subprocess
        iconset_path = path.parent / "icon.iconset"
        iconset_path.mkdir(exist_ok=True)
        
        # Create all required sizes for iconset
        sizes = [16, 32, 64, 128, 256, 512, 1024]
        for size in sizes:
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            resized.save(iconset_path / f"icon_{size}x{size}.png")
            if size <= 512:
                # Also create @2x versions
                resized_2x = img.resize((size * 2, size * 2), Image.Resampling.LANCZOS)
                resized_2x.save(iconset_path / f"icon_{size}x{size}@2x.png")
        
        try:
            subprocess.run(['iconutil', '-c', 'icns', str(iconset_path), '-o', str(path)], check=True)
            print(f"Created: {path}")
            # Clean up iconset
            import shutil
            shutil.rmtree(iconset_path)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"Could not create .icns file. PNG saved at {png_path}")


def main():
    # Get the images directory
    script_dir = Path(__file__).parent.absolute()
    images_dir = script_dir / "app" / "resource" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating application icons...")
    
    # Create the base icon image
    img = create_icon_image(1024)
    
    # Save PNG (high-res for any platform)
    png_path = images_dir / "logo.png"
    img.save(png_path, format='PNG')
    print(f"Created: {png_path}")
    
    # Save ICO for Windows
    ico_path = images_dir / "logo.ico"
    save_ico(img, ico_path)
    
    # Save ICNS for macOS
    icns_path = images_dir / "logo.icns"
    save_icns(img, icns_path)
    
    print("\nDone! Icons created in:", images_dir)


if __name__ == "__main__":
    main()
