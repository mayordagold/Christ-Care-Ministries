from PIL import Image
import os

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

def extract_colors(path, num_colors=5):
    img = Image.open(path).convert('RGB')
    # reduce size for speed
    img = img.resize((200, 200))
    # use adaptive palette
    paletted = img.convert('P', palette=Image.ADAPTIVE, colors=num_colors)
    palette = paletted.getpalette()
    color_counts = sorted(paletted.getcolors(), reverse=True)

    colors = []
    for count, idx in color_counts:
        r = palette[idx * 3]
        g = palette[idx * 3 + 1]
        b = palette[idx * 3 + 2]
        colors.append((count, (r, g, b)))
    return colors

if __name__ == '__main__':
    img_path = os.path.join('static', 'logo.jpeg')
    if not os.path.exists(img_path):
        print('ERROR: logo not found at', img_path)
        raise SystemExit(1)
    colors = extract_colors(img_path, num_colors=6)
    print('Top colors (count, RGB, HEX):')
    for count, rgb in colors:
        print(count, rgb, rgb_to_hex(rgb))