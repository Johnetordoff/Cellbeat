from PIL import Image, ImageDraw, ImageFont
import os
import colorsys

# Output directory
OUTPUT_DIR = "assets/images"

# Icon settings
ICON_SIZE = (64, 64)  # Width x Height
BELL_COUNT = 30

# Try loading a font; fallback to default if not found
def get_font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except IOError:
        return ImageFont.load_default()

# Generate a color palette (HSL evenly spaced colors)
def generate_colors(n):
    colors = []
    for i in range(n):
        hue = i / n
        r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 0.95)
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    return colors

def draw_bell_icon(color, index):
    # Create a transparent image
    img = Image.new("RGBA", ICON_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Bell body settings
    width, height = ICON_SIZE
    center_x = width // 2
    bell_radius = width // 3

    # Draw bell body (triangle)
    triangle = [
        (center_x - bell_radius, height // 2),
        (center_x + bell_radius, height // 2),
        (center_x, height // 5)
    ]
    draw.polygon(triangle, fill=color)

    # Draw clapper (circle)
    clapper_radius = width // 10
    draw.ellipse([
        (center_x - clapper_radius, height // 2),
        (center_x + clapper_radius, height // 2 + clapper_radius * 2)
    ], fill=color)

    # Draw index number (in the center bottom)
    font = get_font(size=14)
    text = str(index)

    # ➡️ Use getbbox() instead of draw.textsize()
    bbox = font.getbbox(text)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Position the text (bottom center)
    text_x = center_x - text_w / 2
    text_y = height * 0.7  # Slightly above the bottom

    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))

    return img

def generate_bell_icons():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    colors = generate_colors(BELL_COUNT)

    for i in range(BELL_COUNT):
        color = colors[i]
        img = draw_bell_icon(color, i)
        filename = os.path.join(OUTPUT_DIR, f"bell_{i}.png")
        img.save(filename)
        print(f"Generated {filename}")

if __name__ == "__main__":
    generate_bell_icons()
