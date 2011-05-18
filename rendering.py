from functools import partial
import os.path

import xcb.xproto as xproto
import Image, ImageDraw, ImageFont

import xpybutil.image as image

from state import conn, core, root, rsetup

imgs = os.path.join('/', 'home', 'andrew', 'clones', 'pyndow', 'images')
stdgc = conn.generate_id()
core.CreateGC(stdgc, root, 0, [])

# Load images
p = partial(os.path.join, imgs)
close = Image.open(p('close.png'))
maximize = Image.open(p('maximize.png'))
minimize = Image.open(p('minimize.png'))
restore = Image.open(p('restore.png'))
shade = Image.open(p('shade.png'))
openbox = Image.open(p('openbox.png'))

def paint_pix(wid, data, w, h):
    pix = conn.generate_id()
    core.CreatePixmap(rsetup.root_depth, pix, root, w, h)

    core.PutImage(xproto.ImageFormat.ZPixmap, pix, stdgc, w, h, 0, 0, 0, 24, 
                  len(data), data)

    core.ChangeWindowAttributes(wid, xproto.CW.BackPixmap, [pix])

    core.ClearArea(0, wid, 0, 0, 0, 0)

    core.FreePixmap(pix)

def draw_text_bgcolor(font, text, color_bg, color_text, max_width, max_height):
    fw, fh = get_text_extents(font, text)

    w, h = min(fw, max_width), min(fh, max_height)

    im = Image.new('RGBA', (w, h), color=image.color_humanize(color_bg))
    d = ImageDraw.Draw(im)
    d.text((0, 0), unicode(text, 'utf-8'), font=font,
           fill=image.color_humanize(color_text))

    return im

def create_font(font, size):
    f = ImageFont.truetype(font, size, encoding='unic')

    return f

def get_text_extents(font, text):
    return font.getsize(unicode(text, 'utf-8'))

def blend(img, mask, color, width, height, alpha=1):
    assert width > 0 and height > 0

    bg = Image.new('RGBA', (width, height), color=image.color_humanize(color))
    blended = Image.composite(img, bg, mask)

    if alpha != 1:
        bg2 = bg.copy()
        blended = Image.blend(bg2, blended, alpha)

    return blended

def bevel_up(img):
    x = y = 0
    w, h = img.size

    imgd = ImageDraw.Draw(img)

    imgd.line([(0, h - 1), (0, 0), (w - 1, 0)], fill=(210, 210, 210))
    imgd.line([(w - 1, 0), (w - 1, h - 1), (0, h - 1)], fill=(0, 0, 0))

def bevel_down(img):
    x = y = 0
    w, h = img.size

    imgd = ImageDraw.Draw(img)

    imgd.line([(0, h - 1), (0, 0), (w - 1, 0)], fill=(0, 0, 0))
    imgd.line([(w - 1, 0), (w - 1, h - 1), (0, h - 1)], fill=(210, 210, 210))

# Some shapes
def border(border_color, bg_color, width, height, orient):
    assert ((width == 1 and orient in ('top', 'bottom')) or
            (height == 1 and orient in ('left', 'right')))

    im = Image.new('RGBA', (width, height))
    bg = (max(width, height) - 1) * [image.hex_to_rgb(bg_color)]
    border = [image.hex_to_rgb(border_color)]

    if orient in ('bottom', 'right'):
        data = bg + border
    else:
        data = border + bg

    im.putdata(data)

    return im

def corner(border_color, bg_color, width, height, orient):
    im = Image.new('RGBA', (width, height), color=image.color_humanize(bg_color))
    d = ImageDraw.Draw(im)

    coords = None

    w, h = width, height
    if orient in ('top_left', 'left_top'):
        coords = [(0, h), (0, 0), (w, 0)]
    elif orient in ('top_right', 'right_top'):
        coords = [(0, 0), (w - 1, 0), (w - 1, h)]
    elif orient in ('right_bottom', 'bottom_right'):
        coords = [(w - 1, 0), (w - 1, h - 1), (0, h - 1)]
    elif orient in ('bottom_left', 'left_bottom'):
        coords = [(0, 0), (0, h - 1), (w - 1, h - 1)]

    assert coords is not None

    d.line(coords, fill=image.hex_to_rgb(border_color))

    return im

def box(color, width, height):
    im = Image.new('RGBA', (width, height), color=image.color_humanize(color))

    return im
