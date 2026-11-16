"""Generate simpledraw.ico next to this script."""
import sys, os, struct, math
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QPolygon, QPainterPath
from PyQt5.QtCore import Qt, QPoint, QPointF

def _draw_icon(size):
    pix = QPixmap(size, size)
    pix.fill(Qt.white)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    s = size

    # ── palette circle (background) ──────────────────────────────────────
    cx, cy = s * 0.46, s * 0.54
    r = s * 0.40
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(60, 60, 60), max(1, s / 32)))
    p.drawEllipse(QPointF(cx, cy), r, r)

    # colour blobs on palette
    blobs = [
        (0.20, QColor(220,  50,  50)),   # red    left
        (0.55, QColor( 50, 180,  50)),   # green  bottom-left
        (0.90, QColor( 50, 100, 220)),   # blue   bottom-right
        (1.25, QColor(240, 200,  30)),   # yellow right
    ]
    br = r * 0.22
    for angle_frac, color in blobs:
        angle = math.pi * angle_frac
        bx = cx + (r * 0.68) * math.cos(angle)
        by = cy + (r * 0.68) * math.sin(angle)
        p.setBrush(color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(bx, by), br, br)

    # thumb hole (punch transparent)
    hole_r = r * 0.18
    p.setCompositionMode(QPainter.CompositionMode_Clear)
    p.setBrush(Qt.transparent)
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(cx + r * 0.30, cy - r * 0.30), hole_r, hole_r)
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)

    # ── pencil (top-right, angled 45°) ───────────────────────────────────
    # pencil runs from tip (bottom-left) to eraser (top-right)
    tip   = QPointF(s * 0.18, s * 0.82)
    eraser_end = QPointF(s * 0.78, s * 0.22)
    dx = eraser_end.x() - tip.x()
    dy = eraser_end.y() - tip.y()
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length   # unit along pencil
    nx, ny = -uy, ux                    # unit perpendicular

    hw = s * 0.055   # half-width of pencil body

    def along(t):   return QPointF(tip.x() + ux * t, tip.y() + uy * t)
    def perp(pt, d): return QPointF(pt.x() + nx * d, pt.y() + ny * d)

    body_start = length * 0.22   # where body begins (after tip)
    eraser_len = length * 0.12

    # body (yellow)
    body = QPolygon([
        QPoint(int(perp(along(body_start), -hw).x()), int(perp(along(body_start), -hw).y())),
        QPoint(int(perp(along(body_start),  hw).x()), int(perp(along(body_start),  hw).y())),
        QPoint(int(perp(along(length - eraser_len),  hw).x()), int(perp(along(length - eraser_len),  hw).y())),
        QPoint(int(perp(along(length - eraser_len), -hw).x()), int(perp(along(length - eraser_len), -hw).y())),
    ])
    p.setBrush(QColor(255, 220, 60))
    p.setPen(QPen(QColor(120, 90, 0), max(1, s / 48)))
    p.drawPolygon(body)

    # tip triangle (dark wood + graphite)
    tip_poly = QPolygon([
        QPoint(int(tip.x()), int(tip.y())),
        QPoint(int(perp(along(body_start), -hw).x()), int(perp(along(body_start), -hw).y())),
        QPoint(int(perp(along(body_start),  hw).x()), int(perp(along(body_start),  hw).y())),
    ])
    p.setBrush(QColor(200, 160, 100))
    p.setPen(QPen(QColor(80, 50, 10), max(1, s / 48)))
    p.drawPolygon(tip_poly)

    # graphite dot at very tip
    p.setBrush(QColor(40, 40, 40))
    p.setPen(Qt.NoPen)
    p.drawEllipse(tip, s * 0.025, s * 0.025)

    # eraser (pink)
    eraser = QPolygon([
        QPoint(int(perp(along(length - eraser_len), -hw).x()), int(perp(along(length - eraser_len), -hw).y())),
        QPoint(int(perp(along(length - eraser_len),  hw).x()), int(perp(along(length - eraser_len),  hw).y())),
        QPoint(int(perp(along(length),  hw).x()), int(perp(along(length),  hw).y())),
        QPoint(int(perp(along(length), -hw).x()), int(perp(along(length), -hw).y())),
    ])
    p.setBrush(QColor(255, 160, 160))
    p.setPen(QPen(QColor(180, 80, 80), max(1, s / 48)))
    p.drawPolygon(eraser)

    p.end()
    return pix


def _pix_to_bmp_bytes(pix, size):
    """Convert QPixmap to 32-bit ARGB BMP bytes (BITMAPV4HEADER) for ICO."""
    img = pix.toImage().convertToFormat(
        __import__('PyQt5.QtGui', fromlist=['QImage']).QImage.Format_ARGB32)
    # ICO BMP: BITMAPINFOHEADER (40 bytes) + pixel data (bottom-up, BGRA)
    w, h = size, size
    header_size = 40
    pixel_data_size = w * h * 4
    # XOR mask (pixel data) + AND mask (1-bit, padded to DWORD rows)
    and_row_bytes = ((w + 31) // 32) * 4
    and_mask_size = and_row_bytes * h

    header = struct.pack('<IiiHHIIiiII',
        header_size,        # biSize
        w,                  # biWidth
        h * 2,              # biHeight (doubled for ICO: XOR+AND)
        1,                  # biPlanes
        32,                 # biBitCount
        0,                  # biCompression (BI_RGB)
        pixel_data_size,    # biSizeImage
        0, 0,               # biXPelsPerMeter, biYPelsPerMeter
        0, 0,               # biClrUsed, biClrImportant
    )

    pixels = bytearray(pixel_data_size)
    for y in range(h):
        src_y = h - 1 - y   # bottom-up
        for x in range(w):
            c = QColor(img.pixel(x, src_y))
            off = (y * w + x) * 4
            pixels[off]     = c.blue()
            pixels[off + 1] = c.green()
            pixels[off + 2] = c.red()
            pixels[off + 3] = c.alpha()

    and_mask = bytearray(and_mask_size)  # all zeros = fully opaque

    return header + bytes(pixels) + bytes(and_mask)


def build_ico(path, sizes=(16, 32, 48, 256)):
    app = QApplication.instance() or QApplication(sys.argv)
    images = [(s, _draw_icon(s)) for s in sizes]
    bmp_data = [_pix_to_bmp_bytes(pix, s) for s, pix in images]

    n = len(sizes)
    # ICO header: 6 bytes
    # Directory entries: n * 16 bytes
    dir_offset = 6 + n * 16
    entries = []
    offset = dir_offset
    for i, (s, _) in enumerate(images):
        data = bmp_data[i]
        w = 0 if s == 256 else s   # 0 means 256 in ICO format
        h = 0 if s == 256 else s
        entries.append((w, h, offset, len(data)))
        offset += len(data)

    with open(path, 'wb') as f:
        f.write(struct.pack('<HHH', 0, 1, n))   # reserved, type=1 (ICO), count
        for w, h, off, size in entries:
            f.write(struct.pack('<BBBBHHII', w, h, 0, 0, 1, 32, size, off))
        for data in bmp_data:
            f.write(data)

    print(f"Written: {path}")


if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'simpledraw.ico')
    build_ico(out)
