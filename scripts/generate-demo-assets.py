#!/usr/bin/env python3
from __future__ import annotations

from math import sin, pi
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'docs' / 'images'
OUT_DIR.mkdir(parents=True, exist_ok=True)

W, H = 1600, 980
BG = '#f6f8fb'
CARD = '#ffffff'
BORDER = '#d8e0ea'
TEXT = '#1d2736'
MUTED = '#6b7a90'
BLUE = '#2f6fcb'
GREEN = '#18a874'
ORANGE = '#f59f00'
PINK = '#d63384'
TEAL = '#0f766e'
PURPLE = '#7c3aed'
GRAY = '#64748b'
LIGHT = '#ecf2fa'

FONT_REG = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def font(size: int, bold: bool = False):
    path = FONT_BOLD if bold else FONT_REG
    return ImageFont.truetype(path, size=size)


def round_rect(draw, box, radius=24, fill=CARD, outline=BORDER, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def shadow(base: Image, box, radius=26, alpha=30):
    layer = Image.new('RGBA', base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(box, radius=radius, fill=(15, 23, 42, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(12))
    base.alpha_composite(layer)


def draw_text(draw, xy, text, size, color=TEXT, bold=False, anchor='la'):
    draw.text(xy, text, font=font(size, bold), fill=color, anchor=anchor)


def metric_card(base, box, title, value, sub, accent):
    shadow(base, box)
    draw = ImageDraw.Draw(base)
    round_rect(draw, box, radius=28)
    x1, y1, x2, y2 = box
    draw.rounded_rectangle((x1 + 18, y1 + 18, x1 + 102, y1 + 36), radius=10, fill=accent)
    draw_text(draw, (x1 + 22, y1 + 58), title, 17, MUTED)
    draw_text(draw, (x1 + 22, y1 + 122), value, 26, TEXT, bold=True)
    draw_text(draw, (x1 + 22, y1 + 168), sub, 14, MUTED)


def panel(base, box, title, subtitle):
    shadow(base, box)
    draw = ImageDraw.Draw(base)
    round_rect(draw, box, radius=26)
    x1, y1, x2, y2 = box
    draw_text(draw, (x1 + 22, y1 + 26), title, 20, TEXT, bold=True)
    draw_text(draw, (x1 + 22, y1 + 52), subtitle, 14, MUTED)


def hbar_panel(base, box, title, subtitle, items):
    panel(base, box, title, subtitle)
    draw = ImageDraw.Draw(base)
    x1, y1, x2, y2 = box
    top = y1 + 88
    left = x1 + 24
    right = x2 - 28
    maxv = max(v for _, _, _, v in items)
    span = right - left - 170
    for i, (name, label, color, value) in enumerate(items):
        y = top + i * 50
        draw_text(draw, (left, y + 10), name, 16, GRAY, anchor='lm')
        bx1 = left + 120
        bx2 = bx1 + int(span * (value / maxv))
        draw.rounded_rectangle((bx1, y, bx2, y + 22), radius=11, fill=color)
        draw_text(draw, (bx2 + 12, y + 11), label, 14, TEXT, anchor='lm')


def hourly_panel(base, box, title, subtitle):
    panel(base, box, title, subtitle)
    draw = ImageDraw.Draw(base)
    x1, y1, x2, y2 = box
    chart = (x1 + 28, y1 + 90, x2 - 26, y2 - 36)
    cx1, cy1, cx2, cy2 = chart
    values = [0,0,0,0,0,0,.2,.55,.78,.92,.66,.4,.6,.88,.7,.8,.62,.45,0,0,0,0,0,0]
    for i in range(6):
        y = cy1 + i * (cy2 - cy1) / 5
        draw.line((cx1, y, cx2, y), fill='#e6edf6', width=1)
    for i in range(24):
        x = cx1 + i * (cx2 - cx1) / 23
        draw.line((x, cy1, x, cy2), fill='#edf3fa', width=1)
    bw = (cx2 - cx1) / 30
    for i, v in enumerate(values):
        x = cx1 + i * (cx2 - cx1) / 24 + 6
        h = (cy2 - cy1) * v
        draw.rounded_rectangle((x, cy2 - h, x + bw, cy2), radius=6, fill=BLUE)
    peak_i = max(range(len(values)), key=lambda i: values[i])
    px = cx1 + peak_i * (cx2 - cx1) / 24 + 6 + bw/2
    py = cy2 - (cy2 - cy1) * values[peak_i]
    draw.ellipse((px-6, py-6, px+6, py+6), fill=GREEN)
    draw_text(draw, (px, py - 18), 'Peak 0.9h', 14, '#0b7285', anchor='ms')


def trend_panel(base, box, title, subtitle):
    panel(base, box, title, subtitle)
    draw = ImageDraw.Draw(base)
    x1, y1, x2, y2 = box
    cx1, cy1, cx2, cy2 = x1 + 28, y1 + 92, x2 - 28, y2 - 42
    dates = ['05-04','05-05','05-06','05-07','05-08','05-09','05-10']
    active = [6.8,7.6,5.4,8.1,7.2,6.4,8.4]
    deep = [4.1,4.8,3.0,5.0,4.4,3.9,5.6]
    focus = [66,71,63,79,75,69,82]
    step = (cx2-cx1)/len(dates)
    for i in range(5):
        y = cy1 + i * (cy2-cy1)/4
        draw.line((cx1, y, cx2, y), fill='#e6edf6', width=1)
    maxh = 9
    for i, d in enumerate(dates):
        x = cx1 + i*step + step*0.12
        aw = step*0.26
        dw = step*0.26
        ah = (cy2-cy1) * (active[i]/maxh)
        dh = (cy2-cy1) * (deep[i]/maxh)
        draw.rounded_rectangle((x, cy2-ah, x+aw, cy2), radius=6, fill=BLUE)
        draw.rounded_rectangle((x+aw+8, cy2-dh, x+aw+8+dw, cy2), radius=6, fill=GREEN)
        draw_text(draw, (x+step*0.23, cy2+18), d, 13, MUTED, anchor='ms')
    pts = []
    for i, f in enumerate(focus):
        x = cx1 + i*step + step*0.28
        y = cy2 - (cy2-cy1) * (f/100)
        pts.append((x,y))
    draw.line(pts, fill=ORANGE, width=4, joint='curve')
    for x,y in pts:
        draw.ellipse((x-5,y-5,x+5,y+5), fill=ORANGE)


def top_lists_row(base, y):
    hbar_panel(base, (60, y, 770, y+250), 'Top apps', 'Most time-consuming applications.', [
        ('VS Code','2h 04m', BLUE, 124), ('Obsidian','1h 46m', BLUE, 106), ('Google Chrome','1h 22m', BLUE, 82), ('Terminal','1h 10m', BLUE, 70)
    ])
    hbar_panel(base, (830, y, 1540, y+250), 'Top domains', 'Browser watcher URL/domain usage.', [
        ('docs.python.org','34m', BLUE, 34), ('github.com','28m', BLUE, 28), ('arxiv.org','21m', BLUE, 21), ('stackoverflow.com','18m', BLUE, 18)
    ])


def dashboard_frame(highlight=None, banner=None, show_report=False):
    base = Image.new('RGBA', (W, H), BG)
    draw = ImageDraw.Draw(base)

    # subtle background gradients
    draw.ellipse((1050, -220, 1600, 260), fill='#edf4ff')
    draw.ellipse((-120, -180, 420, 220), fill='#eefbf4')

    draw_text(draw, (60, 44), 'ActivityWatch Usage Dashboard', 30, TEXT, bold=True)
    draw_text(draw, (60, 82), 'ActivityWatch + Tabler', 15, MUTED)
    draw_text(draw, (60, 112), 'Daily machine-usage analysis with categories, trends, and report export.', 16, MUTED)

    # top toolbar mock
    shadow(base, (1130, 32, 1540, 88), radius=18, alpha=18)
    round_rect(draw, (1130, 32, 1540, 88), radius=18)
    draw.rounded_rectangle((1150, 46, 1265, 74), radius=10, fill='#f3f7fc', outline=BORDER)
    draw_text(draw, (1208, 60), '2026-05-10', 14, TEXT, anchor='mm')
    for label, x, fill, fg in [('Refresh', 1305, BLUE, '#ffffff'), ('Generate PNG', 1422, '#eef5ff', BLUE)]:
        w = 102 if label=='Refresh' else 116
        draw.rounded_rectangle((x, 46, x+w, 74), radius=10, fill=fill, outline=BLUE if fill!='#ffffff' and fill!='#eef5ff' else BORDER)
        draw_text(draw, (x+w/2, 60), label, 13, fg, bold=(label=='Refresh'), anchor='mm')

    # info card
    shadow(base, (60, 150, 1540, 230), radius=22, alpha=20)
    round_rect(draw, (60, 150, 1540, 230), radius=22, fill='#fbfdff')
    draw_text(draw, (88, 179), 'Linked to the original ActivityWatch Web UI', 18, TEXT, bold=True)
    draw_text(draw, (88, 206), 'Reads the same local ActivityWatch buckets and enriches browser sessions with URL/title context.', 15, MUTED)
    for label, x in [('Open original AW', 1240), ('Open latest PNG', 1385)]:
        draw.rounded_rectangle((x, 174, x+126, 206), radius=12, fill='#ffffff', outline=BORDER)
        draw_text(draw, (x+63, 190), label, 13, BLUE, anchor='mm')

    cards = [
        ('Total active', '8h 24m', '23 context switches', BLUE),
        ('Deep work', '5h 36m', '81.2% focus ratio', GREEN),
        ('Productive time', '6h 52m', '5 category groups', ORANGE),
        ('Longest session', '2h 05m', 'Longest continuous block', PINK),
    ]
    for i, card in enumerate(cards):
        x1 = 60 + i * 370
        metric_card(base, (x1, 260, x1 + 340, 430), *card)

    hbar_panel(base, (60, 460, 830, 770), 'Category breakdown', 'Where time went, grouped into categories and subcategories.', [
        ('Learning', '3h 12m', '#2e7d32', 192), ('Coding', '2h 24m', TEAL, 144), ('Web', '1h 18m', BLUE, 78), ('Communication', '42m', '#c2410c', 42), ('Admin', '28m', GRAY, 28)
    ])
    hourly_panel(base, (860, 460, 1540, 770), 'Hourly activity map', 'A compact view of active time by hour.')
    trend_panel(base, (60, 800, 1540, 1130), '7-day trend', 'Active time, deep work, and top category across days.')

    if show_report:
        report = Image.open(OUT_DIR / 'report-demo.png').convert('RGBA')
        report.thumbnail((360, 405))
        rx, ry = 1130, 335
        shadow(base, (rx-8, ry-8, rx + report.width + 8, ry + report.height + 8), radius=24, alpha=28)
        base.alpha_composite(report, (rx, ry))
        draw.rounded_rectangle((1030, 300, 1510, 338), radius=14, fill='#fff7e6', outline='#ffd27a')
        draw_text(draw, (1270, 319), 'One click → PNG report export', 18, '#9a6700', bold=True, anchor='mm')

    if highlight:
        overlay = Image.new('RGBA', (W, H), (8, 15, 30, 84))
        mask = Image.new('L', (W, H), 0)
        md = ImageDraw.Draw(mask)
        md.rounded_rectangle(highlight, radius=28, fill=255)
        overlay.putalpha(Image.eval(mask, lambda p: 84 - p//3))
        base = Image.alpha_composite(base, overlay)
        draw = ImageDraw.Draw(base)
        draw.rounded_rectangle(highlight, radius=28, outline='#ffffff', width=4)

    if banner:
        bx1, by1, bx2, by2 = 80, 30, 770, 98
        shadow(base, (bx1, by1, bx2, by2), radius=24, alpha=36)
        draw.rounded_rectangle((bx1, by1, bx2, by2), radius=24, fill='#182433')
        draw_text(draw, (108, 54), banner[0], 20, '#ffffff', bold=True)
        draw_text(draw, (108, 82), banner[1], 14, '#d5deeb')

    return base


def main():
    # Static dashboard preview with lower lists added in an extended canvas
    base = dashboard_frame()
    ext = Image.new('RGBA', (W, 1630), BG)
    ext.alpha_composite(base, (0,0))
    top_lists_row(ext, 1160)
    draw = ImageDraw.Draw(ext)
    # activities + insights
    hbar_panel(ext, (60, 1435, 770, 1560), 'Top activities', 'Most time-consuming tabs, windows, or contexts.', [
        ('Implementing dashboard export', '1h 06m', BLUE, 66), ('Reading Python logging docs', '34m', BLUE, 34), ('Reviewing research notes', '28m', BLUE, 28)
    ])
    panel(ext, (830, 1435, 1540, 1560), 'Shareable highlights', 'Short takeaways for posting to a study or accountability group.')
    draw_text(draw, (860, 1490), 'Primary mode: Learning', 17, TEXT)
    draw_text(draw, (860, 1518), 'Most-used app: VS Code', 17, TEXT)
    draw_text(draw, (860, 1546), 'Most-used site: docs.python.org', 17, TEXT)
    ext.save(OUT_DIR / 'dashboard-demo.png', optimize=True)

    frames = [
        dashboard_frame(banner=('Dashboard overview', 'Enhanced local analytics on top of ActivityWatch.')),
        dashboard_frame(highlight=(60, 460, 830, 770), banner=('Category breakdown', 'Custom categorization with clearer productivity signals.')),
        dashboard_frame(highlight=(860, 460, 1540, 770), banner=('Hourly patterns', 'Quickly spot focus windows and peak activity.')),
        dashboard_frame(highlight=(60, 800, 1540, 1130), banner=('7-day trend', 'Track active time, deep work, and focus ratio over time.')),
        dashboard_frame(show_report=True, banner=('Report export', 'Generate a shareable PNG report directly from the dashboard.')),
    ]
    frames = [f.convert('P', palette=Image.Palette.ADAPTIVE) for f in frames]
    frames[0].save(
        OUT_DIR / 'dashboard-demo.gif',
        save_all=True,
        append_images=frames[1:],
        duration=[1200, 1200, 1200, 1200, 1500],
        loop=0,
        optimize=True,
        disposal=2,
    )


if __name__ == '__main__':
    main()
