import sys
import os
import math
import random
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QToolBar, QAction, QFileDialog,
    QColorDialog, QInputDialog, QLabel, QComboBox, QSpinBox, QMessageBox,
    QDialog, QFormLayout, QDialogButtonBox, QMenu,
    QHBoxLayout, QVBoxLayout, QStackedWidget, QFrame, QPushButton, QGridLayout, QSizePolicy,
    QFontComboBox, QCheckBox, QLineEdit, QSlider, QRadioButton, QListWidget, QPlainTextEdit
)

from PyQt5.QtGui import (
    QPainter, QPen, QColor, QPixmap, QImage, QBrush, QCursor, QIcon, QFont, QFontMetrics, QPolygon, QPainterPath, QTransform
)
from PyQt5.QtCore import Qt, QPoint, QRect, QRectF, QSize, QBuffer, QByteArray, pyqtSignal, QTimer, QPointF, QObject


APP_VERSION = "1.0.0"

def _app_dir():
    """Return the directory next to the exe (frozen) or the script directory."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BIT_DEPTHS = {"1-bit": 1, "2-bit": 2, "4-bit": 4, "8-bit": 8, "16-bit": 16, "24-bit": 24, "32-bit": 32}
QT_FORMATS = {
    1: QImage.Format_Mono,
    2: QImage.Format_Indexed8,
    4: QImage.Format_Indexed8,
    8: QImage.Format_Indexed8,
    16: QImage.Format_RGB16,
    24: QImage.Format_RGB888,
    32: QImage.Format_ARGB32,
}


class SizeDialog(QDialog):
    _PRESETS = [
        ("Screen",   None),
        ("8x8",      (8,    8)),
        ("16x16",    (16,   16)),
        ("128x64",   (128,  64)),
        ("320x200",  (320,  200)),
        ("640x480",  (640,  480)),
        ("800x600",  (800,  600)),
        ("380p",     (672,  380)),
        ("480p",     (854,  480)),
        ("HD",       (1280, 720)),
        ("Full-HD",  (1920, 1080)),
        ("4K",       (3840, 2160)),
    ]

    def __init__(self, w, h, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Canvas Size")
        self._ratio = w / h if h else 1.0
        self._lock = False
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.wSpin = QSpinBox(); self.wSpin.setRange(1, 9999); self.wSpin.setValue(w)
        self.hSpin = QSpinBox(); self.hSpin.setRange(1, 9999); self.hSpin.setValue(h)
        form.addRow("Width (px):", self.wSpin)
        form.addRow("Height (px):", self.hSpin)
        layout.addLayout(form)
        # ratio row
        ratio_row = QHBoxLayout()
        self._ratio_cb = QCheckBox("Lock ratio")
        self._ratio_label = QLabel()
        self._update_ratio_label(w, h)
        ratio_row.addWidget(self._ratio_cb)
        ratio_row.addWidget(self._ratio_label)
        ratio_row.addStretch()
        layout.addLayout(ratio_row)
        self._ratio_cb.toggled.connect(self._on_lock_toggled)
        # ratio presets
        rpreset_row = QHBoxLayout()
        for label, rw, rh in [("4:3", 4, 3), ("16:9", 16, 9), ("16:10", 16, 10),
                               ("2:3", 2, 3), ("5:7", 5, 7), ("9:16", 9, 16)]:
            btn = QPushButton(label)
            btn.setFixedHeight(22)
            btn.clicked.connect(lambda _, a=rw, b=rh: self._apply_ratio_preset(a, b))
            rpreset_row.addWidget(btn)
        layout.addLayout(rpreset_row)
        preset_grid = QGridLayout()
        preset_grid.setSpacing(2)
        for i, (label, size) in enumerate(self._PRESETS):
            btn = QPushButton(label)
            btn.setFixedHeight(22)
            btn.clicked.connect(lambda _, s=size: self._apply_preset(s))
            preset_grid.addWidget(btn, i // 3, i % 3)
        layout.addLayout(preset_grid)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self.wSpin.valueChanged.connect(self._w_changed)
        self.hSpin.valueChanged.connect(self._h_changed)

    def _on_lock_toggled(self, checked):
        if checked:
            import math
            w = round(self._ratio * 1000)
            h = 1000
            g = math.gcd(w, h)
            self._ratio_label.setText(f"Ratio: {w//g}:{h//g}")
        else:
            self._update_ratio_label(self.wSpin.value(), self.hSpin.value())

    def _update_ratio_label(self, w, h):
        import math
        g = math.gcd(w, h)
        self._ratio_label.setText(f"Ratio: {w//g}:{h//g}")

    def _w_changed(self, w):
        if self._lock:
            return
        if self._ratio_cb.isChecked():
            self._lock = True
            self.hSpin.setValue(max(1, round(w / self._ratio)))
            self._lock = False
        else:
            self._ratio = w / max(1, self.hSpin.value())
            self._update_ratio_label(w, self.hSpin.value())

    def _h_changed(self, h):
        if self._lock:
            return
        if self._ratio_cb.isChecked():
            self._lock = True
            self.wSpin.setValue(max(1, round(h * self._ratio)))
            self._lock = False
        else:
            self._ratio = self.wSpin.value() / max(1, h)
            self._update_ratio_label(self.wSpin.value(), h)

    def _apply_ratio_preset(self, rw, rh):
        self._ratio = rw / rh
        self._lock = True
        self.hSpin.setValue(max(1, round(self.wSpin.value() / self._ratio)))
        self._lock = False
        self._update_ratio_label(rw, rh)

    def _apply_preset(self, size):
        if size is None:
            screen = QApplication.primaryScreen().size()
            self.wSpin.setValue(screen.width())
            self.hSpin.setValue(screen.height())
        else:
            self.wSpin.setValue(size[0])
            self.hSpin.setValue(size[1])


class EffectsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Effects")
        layout = QFormLayout(self)
        self.effect = QComboBox()
        self.effect.addItems(["Grayscale", "Invert Colors", "Smooth"])
        layout.addRow("Effect:", self.effect)
        self.smooth_radius = QSpinBox()
        self.smooth_radius.setRange(1, 20)
        self.smooth_radius.setValue(1)
        self._smooth_row_label = QLabel("Radius:")
        layout.addRow(self._smooth_row_label, self.smooth_radius)
        self._smooth_row_label.setVisible(False)
        self.smooth_radius.setVisible(False)
        self.effect.currentTextChanged.connect(
            lambda t: (self._smooth_row_label.setVisible(t == "Smooth"),
                       self.smooth_radius.setVisible(t == "Smooth")))
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)


class Canvas(QWidget):
    mouse_moved = pyqtSignal(int, int)
    _picked_color = pyqtSignal(QColor)
    _picked_color2 = pyqtSignal(QColor)
    modified = pyqtSignal()

    def __init__(self, width=800, height=600):
        super().__init__()
        self.image = QImage(width, height, QImage.Format_ARGB32)
        self.image.fill(Qt.white)
        self.tool = "pencil"
        self.pencil_mode = "dot"
        self.form_mode = "line"
        self.form_line_style = "solid"
        self.form_fill_transparent = False
        self.line_arrow_start = False
        self.line_arrow_end = False
        self.line_arrow_inward = False
        self.form_antialias = True
        self.pen_color = QColor(Qt.black)
        self.pen_color2 = QColor(Qt.white)
        self.symmetry_h = False
        self.symmetry_v = False
        self.spray_radius = 20
        self.spray_density = 30
        self.spray_density2 = 30
        self.spray_radius2 = 20
        self._spray_timer = QTimer(self)
        self._spray_timer.timeout.connect(self._spray_tick)
        self._spray_pos = None
        self._spray_color = None
        self._stroke_pts = []
        self._spray_pts = []
        self._pencil_cursor_pos = None
        self._pencil_active_btn = None  # "left", "right", or None (hovering)
        self.pen_type1 = "normal"
        self.pen_type2 = "normal"
        self.pen_intensity1 = 100
        self.pen_intensity2 = 100
        self.pencil_bezier = False
        self.pencil_bezier2 = False
        self._pencil_line_smooth = 0
        self._stroke_pts2 = []
        self._resize_handle = None
        self._resize_origin_rect = None
        self.selection_resize_enabled = False
        self.pen_width = 2
        self.pen_width2 = 2
        self.pen_smooth = False
        self.pen_smooth1 = False
        self.pen_smooth2 = False
        self.pen_smooth_pct1 = 50
        self.pen_smooth_pct2 = 50
        self.fill_color = QColor(Qt.red)
        self.fill_color2 = QColor(Qt.white)
        self.form_fill_color = QColor(Qt.red)
        self.bg_color = QColor(Qt.white)
        self.eraser_width = 10
        self.triangle_orientation = "horizontal"
        self.triangle_perpendicular = False
        self.trapezoid_flip = False
        self.star_corners = 4
        self.ngon_edges = 5
        self.rect_corner_radius = 0
        self.circle_start_angle = 0
        self.circle_span_angle = 360
        self.circle_pie_mode = False
        self.circle_donut = False
        self.donut_gap = 20
        self.arrow_head_size = 30
        self.arrow_direction = "right"
        self.parallelogram_orientation = "horizontal"
        self.callout_tail_pos = 0.3
        self.cut_mode = "rectangle"
        self.cut_op = "select"
        self._sel_center = None
        self._lasso_pts = []
        self._copy_lasso_pts = []
        self._lasso_origin = QPoint(0, 0)
        self._wand_path = None
        self._wand_mask_img = None
        self._wand_color = QColor(Qt.black)
        self._wand_inv_color = QColor(Qt.white)
        self._blink_phase = False
        self.text_font = QFont("Arial", 12)
        self.text_color = QColor(Qt.black)
        self.text_bg_color = QColor(Qt.white)
        self.text_bg_transparent = False
        self.text_box = False
        self.text_antialias = True
        self.text_box_color = QColor(Qt.black)
        self.text_box_margin = 4
        self.text_box_style = "solid"
        self.text_box_width = 1
        self.text_str = "Text"
        self._text_cursor_pos = None
        self._last_pos = None
        self._start_pos = None
        self._drag_end_pos = None
        self._preview_image = None
        self._cut_rect = None
        self._cut_pixmap = None
        self._cut_pixmap_base = None
        self._copy_source_pixmap = None
        self._selection_rect = None
        self._dragging_cut = False
        self._resizing_cut = False
        self._resize_cut_handle = None
        self._resize_cut_origin_rect = None
        self._resize_cut_origin_pixmap = None
        self._lasso_pending_blink = False
        self._drag_offset = QPoint()
        self._cut_pos = QPoint()
        self._dash_offset = 0
        self._sel_color = QColor(Qt.black)
        self._undo_stack = []
        self._redo_stack = []
        self._zoom = 1.0
        self._zoom_base = 1.0
        self._offset = QPoint(0, 0)
        self._panning = False
        self._pan_start = QPoint()
        self._march_timer = QTimer(self)
        self._march_timer.timeout.connect(self._march_ants)
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._do_blink)
        self.setMinimumSize(1, 1)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self._color_image = None
        self._emit_modified = True
        self._grid_visible = False
        self._grid_snap = False
        self._grid_w = 10
        self._grid_h = 10
        self.picker_sample_radius = 0
        self.picker_sample_radius2 = 0
        self.fill_tolerance = 0
        self.fill_tolerance2 = 0
        self._prev_tool = None
        self._color_history = []
        self._ruler_start = None
        self._ruler_end = None

    def _to_canvas_pos(self, pos):
        return QPoint(int((pos.x() - self._offset.x()) / self._zoom),
                      int((pos.y() - self._offset.y()) / self._zoom))

    def _push_undo(self):
        sel = QRect(self._selection_rect) if self._selection_rect else None
        self._undo_stack.append((self.image.copy(), sel))
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        if hasattr(self, "main_window"):
            self.main_window._update_undo_redo_state()

    def undo(self):
        if self._undo_stack:
            sel = QRect(self._selection_rect) if self._selection_rect else None
            self._redo_stack.append((self.image.copy(), sel))
            self.image, saved_sel = self._undo_stack.pop()
            self._cancel_cut()
            if saved_sel:
                self._selection_rect = saved_sel
                self._march_timer.start(100)
            self.update()
        if hasattr(self, "main_window"):
            self.main_window._update_undo_redo_state()

    def redo(self):
        if self._redo_stack:
            sel = QRect(self._selection_rect) if self._selection_rect else None
            self._undo_stack.append((self.image.copy(), sel))
            self.image, saved_sel = self._redo_stack.pop()
            self._cancel_cut()
            if saved_sel:
                self._selection_rect = saved_sel
                self._march_timer.start(100)
            self.update()
        if hasattr(self, "main_window"):
            self.main_window._update_undo_redo_state()

    def _mod(self):
        if self._emit_modified:
            self.modified.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def resize_canvas(self, w, h):
        self._push_undo()
        new_img = QImage(w, h, QImage.Format_ARGB32)
        new_img.fill(self.bg_color)
        p = QPainter(new_img)
        p.drawImage(0, 0, self.image)
        p.end()
        self.image = new_img
        self._mod()
        self.update()
        if hasattr(self, "main_window"):
            self.main_window.recorder.record(f"canvas.set_size({w}, {h})")

    def _sync_gray(self):
        """Re-derive self.image as grayscale from _color_image."""
        self.image = self._color_image.convertToFormat(QImage.Format_Grayscale8).convertToFormat(QImage.Format_ARGB32)

    def apply_effect(self, effect, smooth_radius=1):
        self._push_undo()
        if self._cut_pixmap:
            self._apply_effect_to_pixmap(effect, smooth_radius)
            self._cut_pixmap_base = self._cut_pixmap
            self._mod()
            self.update()
            return
        r = self._selection_rect
        if effect == "Grayscale":
            if r:
                region = self.image.copy(r)
                gray = region.convertToFormat(QImage.Format_Grayscale8).convertToFormat(QImage.Format_ARGB32)
                p = QPainter(self.image)
                p.drawImage(r.topLeft(), gray)
                p.end()
                if self._color_image:
                    region_c = self._color_image.copy(r)
                    gray_c = region_c.convertToFormat(QImage.Format_Grayscale8).convertToFormat(QImage.Format_ARGB32)
                    p = QPainter(self._color_image)
                    p.drawImage(r.topLeft(), gray_c)
                    p.end()
            elif self._color_image is not None:
                self.image = self._color_image.copy()
                self._color_image = None
            else:
                self._color_image = self.image.copy()
                self._sync_gray()
        elif effect == "Invert Colors":
            if r:
                region = self.image.copy(r)
                region.invertPixels()
                p = QPainter(self.image)
                p.drawImage(r.topLeft(), region)
                p.end()
                if self._color_image:
                    region_c = self._color_image.copy(r)
                    region_c.invertPixels()
                    p = QPainter(self._color_image)
                    p.drawImage(r.topLeft(), region_c)
                    p.end()
                    self._sync_gray()
            else:
                self._color_image = None
                self.image.invertPixels()
        elif effect == "Smooth":
            if r:
                region = self.image.copy(r)
                factor = max(2, smooth_radius + 1)
                rw, rh = region.width(), region.height()
                small = region.scaled(max(1, rw // factor), max(1, rh // factor), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                smoothed = small.scaled(rw, rh, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                p = QPainter(self.image)
                p.drawImage(r.topLeft(), smoothed)
                p.end()
                if self._color_image:
                    region_c = self._color_image.copy(r)
                    small_c = region_c.scaled(max(1, rw // factor), max(1, rh // factor), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                    smoothed_c = small_c.scaled(rw, rh, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                    p = QPainter(self._color_image)
                    p.drawImage(r.topLeft(), smoothed_c)
                    p.end()
                    self._sync_gray()
            else:
                self._color_image = None
                w, h = self.image.width(), self.image.height()
                factor = max(2, smooth_radius + 1)
                small = self.image.scaled(max(1, w // factor), max(1, h // factor), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                self.image = small.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self._mod()
        self.update()

    def apply_brightness_contrast(self, brightness, contrast):
        self._apply_to_target(self._apply_bc_to_image, brightness, contrast)

    def apply_saturation(self, value):
        self._apply_to_target(self._apply_sat_to_image, value)

    def apply_noise(self, value):
        self._apply_to_target(self._apply_noise_to_image, value)

    def apply_pixelate(self, value):
        block = max(2, value)
        self._apply_to_target(self._apply_pixelate_to_image, block)

    def apply_colorfade(self, color_a, color_b, orient):
        self._apply_to_target(self._apply_fade_to_image, color_a, color_b, orient)

    @staticmethod
    def _apply_fade_to_image(img, color_a, color_b, orient):
        w, h = img.width(), img.height()
        ar, ag, ab = color_a.red(), color_a.green(), color_a.blue()
        br, bg, bb = color_b.red(), color_b.green(), color_b.blue()
        cx, cy = w / 2.0, h / 2.0
        max_dist = math.hypot(cx, cy)
        for y in range(h):
            for x in range(w):
                if orient == 0:    t = y / (h - 1) if h > 1 else 0
                elif orient == 1:  t = 1 - y / (h - 1) if h > 1 else 0
                elif orient == 2:  t = x / (w - 1) if w > 1 else 0
                elif orient == 3:  t = 1 - x / (w - 1) if w > 1 else 0
                elif orient == 4:  t = min(math.hypot(x - cx, y - cy) / max_dist, 1.0)
                elif orient == 5:  t = 1.0 - min(math.hypot(x - cx, y - cy) / max_dist, 1.0)
                elif orient == 6:  t = (x / (w - 1) + y / (h - 1)) / 2 if w > 1 and h > 1 else 0
                elif orient == 7:  t = 1 - (x / (w - 1) + y / (h - 1)) / 2 if w > 1 and h > 1 else 0
                elif orient == 8:  t = ((w - 1 - x) / (w - 1) + y / (h - 1)) / 2 if w > 1 and h > 1 else 0
                else:              t = 1 - ((w - 1 - x) / (w - 1) + y / (h - 1)) / 2 if w > 1 and h > 1 else 0
                r = int(ar + (br - ar) * t)
                g = int(ag + (bg - ag) * t)
                b = int(ab + (bb - ab) * t)
                orig = QColor(img.pixel(x, y))
                img.setPixel(x, y, QColor(r, g, b, orig.alpha()).rgb())

    def _apply_to_target(self, fn, *args):
        if self._cut_pixmap:
            img = self._cut_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
            fn(img, *args)
            new_pix = QPixmap.fromImage(img)
            if self._cut_pixmap.mask():
                new_pix.setMask(self._cut_pixmap.mask())
            self._cut_pixmap = new_pix
            self._cut_pixmap_base = self._cut_pixmap
        else:
            r = self._selection_rect
            if r:
                def _apply_with_mask(target_img):
                    region = target_img.copy(r).convertToFormat(QImage.Format_ARGB32)
                    original = region.copy()
                    fn(region, *args)
                    mask_img = QImage(r.size(), QImage.Format_ARGB32)
                    mask_img.fill(Qt.transparent)
                    mp = QPainter(mask_img)
                    mp.setRenderHint(QPainter.Antialiasing, False)
                    mp.setBrush(Qt.white)
                    mp.setPen(Qt.NoPen)
                    if self.cut_mode == 'wand' and self._wand_mask_img:
                        mp.drawImage(0, 0, self._wand_mask_img)
                    elif self.cut_mode == 'lasso' and self._copy_lasso_pts:
                        pts = [QPoint(int(p[0]) - r.x(), int(p[1]) - r.y()) for p in self._copy_lasso_pts]
                        mp.drawPolygon(QPolygon(pts))
                    elif self.cut_mode in ('circle', 'ellipse'):
                        mp.drawEllipse(QRect(0, 0, r.width(), r.height()))
                    else:
                        mp.end()
                        p = QPainter(target_img)
                        p.drawImage(r.topLeft(), region)
                        p.end()
                        return
                    mp.end()
                    effect_masked = QImage(r.size(), QImage.Format_ARGB32)
                    effect_masked.fill(Qt.transparent)
                    ep = QPainter(effect_masked)
                    ep.drawImage(0, 0, region)
                    ep.setCompositionMode(QPainter.CompositionMode_DestinationIn)
                    ep.drawImage(0, 0, mask_img)
                    ep.end()
                    result = original.copy()
                    rp = QPainter(result)
                    rp.setCompositionMode(QPainter.CompositionMode_SourceOver)
                    rp.drawImage(0, 0, effect_masked)
                    rp.end()
                    p = QPainter(target_img)
                    p.drawImage(r.topLeft(), result)
                    p.end()
                _apply_with_mask(self.image)
                if self._color_image:
                    _apply_with_mask(self._color_image)
                    self._sync_gray()
            else:
                fn(self.image, *args)
                if self._color_image:
                    fn(self._color_image, *args)
                    self._sync_gray()
        self._mod()
        self.update()

    @staticmethod
    def _apply_bc_to_image(img, brightness, contrast):
        bf = brightness / 100.0
        cf = contrast / 100.0
        ptr = img.bits()
        ptr.setsize(img.byteCount())
        arr = bytearray(ptr)
        for i in range(0, len(arr), 4):
            for j in range(3):
                v = arr[i + j] / 255.0
                # brightness
                v = v + bf if bf >= 0 else v * (1 + bf)
                # contrast: scale around 0.5
                if cf >= 0:
                    v = (v - 0.5) * (1 + cf * 3) + 0.5
                else:
                    v = (v - 0.5) * (1 + cf) + 0.5
                arr[i + j] = max(0, min(255, int(v * 255)))
        ptr.setsize(img.byteCount())
        for i in range(len(arr)):
            ptr[i] = arr[i:i+1]

    @staticmethod
    def _apply_sat_to_image(img, value):
        factor = 1.0 + value / 100.0
        ptr = img.bits()
        ptr.setsize(img.byteCount())
        arr = bytearray(ptr)
        for i in range(0, len(arr), 4):
            b, g, r = arr[i] / 255.0, arr[i+1] / 255.0, arr[i+2] / 255.0
            gray = 0.299 * r + 0.587 * g + 0.114 * b
            arr[i]   = max(0, min(255, int((gray + (b - gray) * factor) * 255)))
            arr[i+1] = max(0, min(255, int((gray + (g - gray) * factor) * 255)))
            arr[i+2] = max(0, min(255, int((gray + (r - gray) * factor) * 255)))
        ptr.setsize(img.byteCount())
        for i in range(len(arr)):
            ptr[i] = arr[i:i+1]

    @staticmethod
    def _apply_noise_to_image(img, value):
        ptr = img.bits()
        ptr.setsize(img.byteCount())
        arr = bytearray(ptr)
        for i in range(0, len(arr), 4):
            n = random.randint(-value, value)
            arr[i]   = max(0, min(255, arr[i]   + n))
            arr[i+1] = max(0, min(255, arr[i+1] + n))
            arr[i+2] = max(0, min(255, arr[i+2] + n))
        ptr.setsize(img.byteCount())
        for i in range(len(arr)):
            ptr[i] = arr[i:i+1]

    @staticmethod
    def _apply_pixelate_to_image(img, block):
        w, h = img.width(), img.height()
        for y in range(0, h, block):
            for x in range(0, w, block):
                # sample top-left pixel of block
                c = QColor(img.pixel(x, y))
                r, g, b = c.red(), c.green(), c.blue()
                for by in range(y, min(y + block, h)):
                    for bx in range(x, min(x + block, w)):
                        img.setPixel(bx, by, QColor(r, g, b).rgb())

    @staticmethod
    def _apply_sharpen_to_image(img):
        w, h = img.width(), img.height()
        src = img.copy()
        kernel = [0, -1, 0, -1, 5, -1, 0, -1, 0]
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                r = g = b = 0
                ki = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        c = QColor(src.pixel(x + dx, y + dy))
                        k = kernel[ki]; ki += 1
                        r += c.red()   * k
                        g += c.green() * k
                        b += c.blue()  * k
                img.setPixel(x, y, QColor(max(0,min(255,r)), max(0,min(255,g)), max(0,min(255,b))).rgb())

    @staticmethod
    def _apply_posterize_to_image(img, levels):
        step = 255 / (levels - 1)
        ptr = img.bits(); ptr.setsize(img.byteCount())
        arr = bytearray(ptr)
        lut = [int(round(round(v / step) * step)) for v in range(256)]
        for i in range(0, len(arr), 4):
            arr[i]   = lut[arr[i]]
            arr[i+1] = lut[arr[i+1]]
            arr[i+2] = lut[arr[i+2]]
        ptr.setsize(img.byteCount())
        for i in range(len(arr)): ptr[i] = arr[i:i+1]

    def apply_posterize(self, levels):
        self._apply_to_target(self._apply_posterize_to_image, max(2, levels))

    @staticmethod
    def _apply_emboss_to_image(img):
        w, h = img.width(), img.height()
        src = img.copy()
        kernel = [-2, -1, 0, -1, 1, 1, 0, 1, 2]
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                r = g = b = 0
                ki = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        c = QColor(src.pixel(x + dx, y + dy))
                        k = kernel[ki]; ki += 1
                        r += c.red() * k; g += c.green() * k; b += c.blue() * k
                img.setPixel(x, y, QColor(max(0,min(255,r+128)), max(0,min(255,g+128)), max(0,min(255,b+128))).rgb())

    def apply_emboss(self):
        self._apply_to_target(self._apply_emboss_to_image)

    @staticmethod
    def _apply_vignette_to_image(img, strength):
        w, h = img.width(), img.height()
        cx, cy = w / 2.0, h / 2.0
        max_d = math.hypot(cx, cy)
        s = strength / 100.0
        for y in range(h):
            for x in range(w):
                t = math.hypot(x - cx, y - cy) / max_d
                factor = max(0.0, 1.0 - t * t * s)
                c = QColor(img.pixel(x, y))
                img.setPixel(x, y, QColor(int(c.red()*factor), int(c.green()*factor), int(c.blue()*factor), c.alpha()).rgb())

    def apply_vignette(self, strength):
        self._apply_to_target(self._apply_vignette_to_image, strength)

    def apply_sharpen(self):
        self._apply_to_target(self._apply_sharpen_to_image)

    def _apply_effect_to_pixmap(self, effect, smooth_radius=1):
        img = self._cut_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        if effect == "Grayscale":
            img = img.convertToFormat(QImage.Format_Grayscale8).convertToFormat(QImage.Format_ARGB32)
        elif effect == "Invert Colors":
            img.invertPixels()
        elif effect == "Smooth":
            w, h = img.width(), img.height()
            factor = max(2, smooth_radius + 1)
            small = img.scaled(max(1, w // factor), max(1, h // factor), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            img = small.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        new_pix = QPixmap.fromImage(img)
        if self._cut_pixmap.mask():
            new_pix.setMask(self._cut_pixmap.mask())
        self._cut_pixmap = new_pix

    def flip_canvas(self, horizontal):
        self._push_undo()
        self.image = self.image.mirrored(not horizontal, horizontal)
        self._mod()
        self.update()
        if hasattr(self, "main_window"):
            axis = "horizontal" if horizontal else "vertical"
            self.main_window.recorder.record(f"canvas.apply_effect('flip_{axis}')")

    def rotate_canvas(self, clockwise):
        self._push_undo()
        self.image = self.image.transformed(QTransform().rotate(90 if clockwise else -90))
        self._mod()
        self.update()
        if hasattr(self, "main_window"):
            self.main_window.recorder.record(f"canvas.apply_effect('rotate_cw')" if clockwise else "canvas.apply_effect('rotate_ccw')")

    def _text_render_font(self):
        font = QFont(self.text_font)
        # Fixed pixel size so rendering doesn't depend on the image's DPI metadata
        if font.pointSizeF() > 0:
            screen_dpi = QApplication.primaryScreen().logicalDotsPerInch()
            font.setPixelSize(max(1, round(font.pointSizeF() * screen_dpi / 72.0)))
        return font

    def _text_rect(self, pos):
        rect = QFontMetrics(self._text_render_font()).boundingRect(self.text_str)
        m = self.text_box_margin if self.text_box else 0
        rect.adjust(-m, -m, m, m)
        rect.moveTo(pos)
        return rect

    def _draw_text_preview(self, painter, pos):
        # Normal screen font rendering; same pixel size and layout as the final text
        font = self._text_render_font()
        rect = self._text_rect(pos)
        m = self.text_box_margin if self.text_box else 0
        if not self.text_bg_transparent:
            painter.fillRect(rect, self.text_bg_color)
        if self.text_box:
            style = {"solid": Qt.SolidLine, "dashed": Qt.DashLine, "dotted": Qt.DotLine}.get(self.text_box_style, Qt.SolidLine)
            painter.setPen(QPen(self.text_box_color, self.text_box_width, style))
            painter.drawRect(rect)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setFont(font)
        painter.setPen(QPen(self.text_color))
        painter.drawText(QPointF(rect.left() + m, rect.top() + m + QFontMetrics(font).ascent()), self.text_str)

    def _draw_text_at(self, painter, pos, to_image=False):
        painter.setRenderHint(QPainter.Antialiasing, False)
        font = self._text_render_font()
        rect = self._text_rect(pos)
        m = self.text_box_margin if self.text_box else 0
        if not self.text_bg_transparent:
            painter.fillRect(rect, self.text_bg_color)
        if self.text_box:
            style = {"solid": Qt.SolidLine, "dashed": Qt.DashLine, "dotted": Qt.DotLine}.get(self.text_box_style, Qt.SolidLine)
            painter.setPen(QPen(self.text_box_color, self.text_box_width, style))
            painter.drawRect(rect)
        # Glyph outlines filled as a path keep the true font shape with or without AA
        path = QPainterPath()
        path.addText(QPointF(rect.left() + m, rect.top() + m + QFontMetrics(font).ascent()), font, self.text_str)
        painter.setRenderHint(QPainter.Antialiasing, self.text_antialias)
        painter.fillPath(path, self.text_color)

    def _make_march_pen(self, color=None):
        c = color if color is not None else self._sel_color
        pen = QPen(c, 1, Qt.CustomDashLine)
        pen.setDashPattern([4, 4])
        pen.setDashOffset(self._dash_offset)
        return pen

    def _make_march_pen2(self):
        pen = QPen(QColor(255 - self._sel_color.red(), 255 - self._sel_color.green(), 255 - self._sel_color.blue()), 1, Qt.CustomDashLine)
        pen.setDashPattern([4, 4])
        pen.setDashOffset((self._dash_offset + 4) % 8)
        return pen

    def _canvas_rect_to_widget(self, r):
        """Convert a canvas-pixel QRect to widget-pixel QRect for outline drawing."""
        x = int(r.x() * self._zoom + self._offset.x())
        y = int(r.y() * self._zoom + self._offset.y())
        w = int(r.width() * self._zoom)
        h = int(r.height() * self._zoom)
        return QRect(x, y, w, h)

    def _draw_sel_outline(self, painter, r, blink=False):
        painter.setBrush(Qt.NoBrush)
        inv = QColor(255 - self._sel_color.red(), 255 - self._sel_color.green(), 255 - self._sel_color.blue())
        color = inv if (blink and self._blink_phase) else self._sel_color
        if self.cut_mode == "lasso" and self._lasso_pts:
            pts = [QPoint(int(p[0] * self._zoom + self._offset.x()),
                          int(p[1] * self._zoom + self._offset.y())) for p in self._lasso_pts]
            poly = QPolygon(pts)
            painter.setPen(self._make_march_pen(QColor(Qt.black)))
            painter.drawPolygon(poly)
            painter.setPen(self._make_march_pen2())
            painter.drawPolygon(poly)
        elif self.cut_mode in ("circle", "ellipse"):
            wr = self._canvas_rect_to_widget(r)
            painter.setPen(self._make_march_pen(color))
            painter.drawEllipse(wr)
        else:
            wr = self._canvas_rect_to_widget(r)
            painter.setPen(self._make_march_pen(color))
            painter.drawRect(wr)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.translate(self._offset)
        painter.scale(self._zoom, self._zoom)
        painter.drawImage(0, 0, self.image)
        if self._preview_image:
            painter.drawImage(0, 0, self._preview_image)
        if self._grid_visible and self._grid_w > 0 and self._grid_h > 0:
            iw, ih = self.image.width(), self.image.height()
            grid_pen = QPen(QColor(180, 180, 255, 160), 1 / self._zoom)
            painter.setPen(grid_pen)
            x = 0
            while x <= iw:
                painter.drawLine(x, 0, x, ih)
                x += self._grid_w
            y = 0
            while y <= ih:
                painter.drawLine(0, y, iw, y)
                y += self._grid_h
        if self._cut_pixmap:
            painter.drawPixmap(self._cut_pos, self._cut_pixmap)
        if self.cut_mode == "wand" and self._wand_path:
            painter.setBrush(Qt.NoBrush)
            pen_color = self._wand_inv_color if self._blink_phase else self._wand_color
            painter.setPen(QPen(pen_color, 1 / self._zoom))
            painter.save()
            painter.translate(self._cut_pos if self._cut_pixmap else (self._selection_rect.topLeft() if self._selection_rect else self._cut_pos))
            painter.drawPath(self._wand_path)
            painter.restore()
            if self._cut_pixmap and self.cut_op == "copy" and self._selection_rect:
                inv = QColor(255 - self._wand_color.red(), 255 - self._wand_color.green(), 255 - self._wand_color.blue())
                blink_color = inv if self._blink_phase else self._wand_color
                painter.setPen(QPen(blink_color, 1 / self._zoom))
                painter.save()
                painter.translate(self._selection_rect.topLeft())
                painter.drawPath(self._wand_path)
                painter.restore()
        painter.resetTransform()
        if self._cut_pixmap and self.cut_mode not in ("wand", "lasso"):
            self._draw_sel_outline(painter, QRect(self._cut_pos, self._cut_pixmap.size()))
            if self.cut_op == "copy" and self._selection_rect:
                self._draw_sel_outline(painter, self._selection_rect, blink=True)
        if self._cut_pixmap and self.cut_mode == "lasso" and self._lasso_pts:
            dx = self._cut_pos.x() - self._lasso_origin.x()
            dy = self._cut_pos.y() - self._lasso_origin.y()
            float_pts = [QPoint(int((p[0] + dx) * self._zoom + self._offset.x()),
                                int((p[1] + dy) * self._zoom + self._offset.y())) for p in self._lasso_pts]
            float_poly = QPolygon(float_pts)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(self._make_march_pen(QColor(Qt.black)))
            painter.drawPolygon(float_poly)
            painter.setPen(self._make_march_pen2())
            painter.drawPolygon(float_poly)
            if self.cut_op == "copy" and self._copy_lasso_pts:
                orig_pts = [QPoint(int(p[0] * self._zoom + self._offset.x()),
                                   int(p[1] * self._zoom + self._offset.y())) for p in self._copy_lasso_pts]
                orig_poly = QPolygon(orig_pts)
                inv = QColor(255 - self._sel_color.red(), 255 - self._sel_color.green(), 255 - self._sel_color.blue())
                blink_color = inv if self._blink_phase else self._sel_color
                painter.setPen(self._make_march_pen(blink_color))
                painter.drawPolygon(orig_poly)
        if not self._cut_pixmap and self.cut_mode == "lasso" and self._copy_lasso_pts:
            pts = [QPoint(int(p[0] * self._zoom + self._offset.x()),
                          int(p[1] * self._zoom + self._offset.y())) for p in self._copy_lasso_pts]
            poly = QPolygon(pts)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(self._make_march_pen(QColor(Qt.black)))
            painter.drawPolygon(poly)
            painter.setPen(self._make_march_pen2())
            painter.drawPolygon(poly)
        if self.tool == "cut" and self.cut_mode == "lasso" and self._lasso_pts and not self._cut_pixmap:
            pts = [QPoint(int(p[0] * self._zoom + self._offset.x()),
                          int(p[1] * self._zoom + self._offset.y())) for p in self._lasso_pts]
            poly = QPolygon(pts)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(self._make_march_pen(QColor(Qt.black)))
            painter.drawPolyline(poly)
            painter.setPen(self._make_march_pen2())
            painter.drawPolyline(poly)
        elif self._start_pos is not None and self.tool == "cut" and self._drag_end_pos:
            wr = self._canvas_rect_to_widget(self._sel_rubber_rect(self._start_pos, self._drag_end_pos))
            painter.setBrush(Qt.NoBrush)
            painter.setPen(self._make_march_pen())
            if self.cut_mode in ("circle", "ellipse"):
                painter.drawEllipse(wr)
            else:
                painter.drawRect(wr)
        elif self._selection_rect and not self._cut_pixmap and self.cut_mode != "wand":
            self._draw_sel_outline(painter, self._selection_rect, blink=self.cut_op != "select")
        if self.tool == "text" and self._text_cursor_pos:
            painter.save()
            painter.translate(self._offset)
            painter.scale(self._zoom, self._zoom)
            self._draw_text_preview(painter, self._text_cursor_pos)
            painter.restore()
        if self.tool == "ruler" and self._ruler_start:
            p1 = QPoint(int(self._ruler_start.x() * self._zoom + self._offset.x()),
                        int(self._ruler_start.y() * self._zoom + self._offset.y()))
            if self._ruler_end:
                p2 = QPoint(int(self._ruler_end.x() * self._zoom + self._offset.x()),
                            int(self._ruler_end.y() * self._zoom + self._offset.y()))
                painter.setPen(QPen(QColor(255, 60, 60), 1, Qt.DashLine))
                painter.drawLine(p1, p2)
                painter.setPen(QPen(QColor(255, 60, 60), 1))
                for pt in (p1, p2):
                    painter.drawEllipse(pt, 3, 3)
        if self.selection_resize_enabled and self.cut_op == "select" and self.cut_mode not in ("lasso", "wand") and self._selection_rect and not self._cut_pixmap:
            r = self._selection_rect
            hs = 6
            cx, cy = r.center().x(), r.center().y()
            handle_rects = [
                QRect(r.left()-hs//2,  r.top()-hs//2,    hs, hs),
                QRect(cx-hs//2,         r.top()-hs//2,    hs, hs),
                QRect(r.right()-hs//2,  r.top()-hs//2,    hs, hs),
                QRect(r.left()-hs//2,   cy-hs//2,         hs, hs),
                QRect(r.right()-hs//2,  cy-hs//2,         hs, hs),
                QRect(r.left()-hs//2,   r.bottom()-hs//2, hs, hs),
                QRect(cx-hs//2,         r.bottom()-hs//2, hs, hs),
                QRect(r.right()-hs//2,  r.bottom()-hs//2, hs, hs),
            ]
            for rect in handle_rects:
                wr = self._canvas_rect_to_widget(rect)
                painter.fillRect(wr, QColor(255, 255, 255))
                painter.setPen(QPen(QColor(0, 80, 200), 1))
                painter.drawRect(wr)
        if self.selection_resize_enabled and self._cut_pixmap and self.cut_op in ("cut", "copy") and self.cut_mode not in ("lasso", "wand") and self._cut_rect:
            r = self._cut_rect
            hs = 6
            cx, cy = r.center().x(), r.center().y()
            cut_handle_rects = [
                QRect(r.left()-hs//2,  r.top()-hs//2,    hs, hs),
                QRect(cx-hs//2,         r.top()-hs//2,    hs, hs),
                QRect(r.right()-hs//2,  r.top()-hs//2,    hs, hs),
                QRect(r.left()-hs//2,   cy-hs//2,         hs, hs),
                QRect(r.right()-hs//2,  cy-hs//2,         hs, hs),
                QRect(r.left()-hs//2,   r.bottom()-hs//2, hs, hs),
                QRect(cx-hs//2,         r.bottom()-hs//2, hs, hs),
                QRect(r.right()-hs//2,  r.bottom()-hs//2, hs, hs),
            ]
            for rect in cut_handle_rects:
                wr = self._canvas_rect_to_widget(rect)
                painter.fillRect(wr, QColor(255, 255, 255))
                painter.setPen(QPen(QColor(200, 80, 0), 1))
                painter.drawRect(wr)

    def _make_pen(self, style=None, color=None):
        qt_style = {"solid": Qt.SolidLine, "dashed": Qt.DashLine, "dotted": Qt.DotLine, "dash-dotted": Qt.DashDotLine}.get(style or "solid", Qt.SolidLine)
        return QPen(color if color else self.pen_color, self.pen_width, qt_style, Qt.RoundCap, Qt.RoundJoin)

    def _make_form_pen(self):
        return self._make_pen(self.form_line_style)

    def _make_form_brush(self):
        return QBrush(Qt.NoBrush) if self.form_fill_transparent else QBrush(self.form_fill_color)

    def _hit_handle_rect(self, r, pos):
        hs = 6
        cx, cy = r.center().x(), r.center().y()
        handles = {
            'tl': QRect(r.left()-hs//2,  r.top()-hs//2,    hs, hs),
            'tc': QRect(cx-hs//2,         r.top()-hs//2,    hs, hs),
            'tr': QRect(r.right()-hs//2,  r.top()-hs//2,    hs, hs),
            'ml': QRect(r.left()-hs//2,   cy-hs//2,         hs, hs),
            'mr': QRect(r.right()-hs//2,  cy-hs//2,         hs, hs),
            'bl': QRect(r.left()-hs//2,   r.bottom()-hs//2, hs, hs),
            'bc': QRect(cx-hs//2,         r.bottom()-hs//2, hs, hs),
            'br': QRect(r.right()-hs//2,  r.bottom()-hs//2, hs, hs),
        }
        for name, rect in handles.items():
            if rect.contains(pos):
                return name
        return None

    def _update_eraser_cursor(self):
        size = max(int(self.eraser_width * self._zoom), 1)
        pix_size = size + 4
        pix = QPixmap(pix_size, pix_size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(self.bg_color))
        p.setPen(QPen(Qt.gray, 1))
        p.drawRect(2, 2, size, size)
        p.end()
        self.setCursor(QCursor(pix, pix_size // 2, pix_size // 2))

    def _update_pen_cursor(self):
        sz = 24
        pix = QPixmap(sz, sz)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        angle = math.radians(45)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        def pt(cx, cy, dx, dy):
            return QPoint(int(cx + dx * cos_a - dy * sin_a),
                          int(cy + dx * sin_a + dy * cos_a))
        bx, by = 17, 3
        body = QPolygon([pt(bx, by, 0, -2), pt(bx, by, 10, -2),
                         pt(bx, by, 10,  2), pt(bx, by, 0,  2)])
        p.setBrush(QColor(255, 220, 80))
        p.setPen(QPen(QColor(80, 60, 0), 1))
        p.drawPolygon(body)
        eraser = QPolygon([pt(bx, by, -1, -2), pt(bx, by, 2, -2),
                           pt(bx, by,  2,  2), pt(bx, by, -1, 2)])
        p.setBrush(QColor(255, 160, 160))
        p.drawPolygon(eraser)
        tip = QPolygon([pt(bx, by, 10, -2), pt(bx, by, 10, 2),
                        pt(bx, by, 13,  0)])
        p.setBrush(QColor(40, 30, 10))
        p.setPen(Qt.NoPen)
        p.drawPolygon(tip)
        tip_pt = pt(bx, by, 14, 0)
        p.setBrush(QBrush(self.pen_color))
        p.setPen(Qt.NoPen)
        p.drawEllipse(tip_pt, 2, 2)
        p.end()
        self.setCursor(QCursor(pix, tip_pt.x(), tip_pt.y()))

    def _replace_color(self, old_color, new_color):
        self._push_undo()
        old_rgb = old_color.rgb()
        new_rgb = new_color.rgb()
        w, h = self.image.width(), self.image.height()
        for y in range(h):
            for x in range(w):
                if self.image.pixel(x, y) == old_rgb:
                    self.image.setPixel(x, y, new_rgb)
        self.update()

    def _triangle_pts(self, start, end):
        if self.triangle_perpendicular:
            if self.triangle_orientation == "vertical":
                return [QPoint(start.x(), start.y()),
                        QPoint(end.x(),   start.y()),
                        QPoint(end.x(),   end.y())]
            else:
                return [QPoint(start.x(), start.y()),
                        QPoint(end.x(),   end.y()),
                        QPoint(start.x(), end.y())]
        if self.triangle_orientation == "vertical":
            dy = abs(end.y() - start.y())
            return [QPoint(start.x(), start.y()),
                    QPoint(end.x(), start.y() - dy),
                    QPoint(end.x(), start.y() + dy)]
        else:
            dx = abs(end.x() - start.x())
            return [QPoint(start.x(), start.y()),
                    QPoint(start.x() - dx, end.y()),
                    QPoint(start.x() + dx, end.y())]

    def _arrow_shape_pts(self, start, end):
        # start = tip; shape mirrors symmetrically around tip in the perpendicular axis
        d = self.arrow_direction
        tx, ty = start.x(), start.y()
        if d in ("right", "left"):
            # horizontal arrow: perpendicular spread is Y, depth is X
            dy = abs(end.y() - ty)          # half-height of the whole arrow
            dx = abs(end.x() - tx)          # depth (tip to tail)
            hs = min(self.arrow_head_size, dx)
            shaft_h = max(2, dy // 3 * 2)  # shaft thickness (symmetric around ty)
            sign = 1 if d == "right" else -1
            tail_x = tx - sign * dx
            neck_x = tx - sign * hs
            return [
                QPoint(tx,              ty),
                QPoint(neck_x,          ty - dy),
                QPoint(neck_x,          ty - shaft_h // 2),
                QPoint(tail_x,          ty - shaft_h // 2),
                QPoint(tail_x,          ty + shaft_h // 2),
                QPoint(neck_x,          ty + shaft_h // 2),
                QPoint(neck_x,          ty + dy),
            ]
        else:
            # vertical arrow: perpendicular spread is X, depth is Y
            dx = abs(end.x() - tx)
            dy = abs(end.y() - ty)
            hs = min(self.arrow_head_size, dy)
            shaft_w = max(2, dx // 3 * 2)
            sign = 1 if d == "down" else -1
            tail_y = ty - sign * dy
            neck_y = ty - sign * hs
            return [
                QPoint(tx,              ty),
                QPoint(tx + dx,         neck_y),
                QPoint(tx + shaft_w//2, neck_y),
                QPoint(tx + shaft_w//2, tail_y),
                QPoint(tx - shaft_w//2, tail_y),
                QPoint(tx - shaft_w//2, neck_y),
                QPoint(tx - dx,         neck_y),
            ]

    def _parallelogram_pts(self, start, end):
        r = QRect(start, end).normalized()
        if self.parallelogram_orientation == "vertical":
            offset = r.height() // 4
            return [
                QPoint(r.left(),  r.top() + offset),
                QPoint(r.right(), r.top()),
                QPoint(r.right(), r.bottom() - offset),
                QPoint(r.left(),  r.bottom()),
            ]
        else:
            offset = r.width() // 4
            return [
                QPoint(r.left() + offset, r.top()),
                QPoint(r.right(),         r.top()),
                QPoint(r.right() - offset, r.bottom()),
                QPoint(r.left(),          r.bottom()),
            ]

    def _callout_pts(self, start, end):
        r = QRect(start, end).normalized()
        tail_x = int(r.left() + r.width() * self.callout_tail_pos)
        tail_w = max(4, r.width() // 8)
        tail_depth = max(6, r.height() // 4)
        return [
            QPoint(r.left(),              r.top()),
            QPoint(r.right(),             r.top()),
            QPoint(r.right(),             r.bottom() - tail_depth),
            QPoint(min(tail_x + tail_w, r.right()), r.bottom() - tail_depth),
            QPoint(tail_x + tail_w // 2,  r.bottom()),
            QPoint(max(tail_x - tail_w, r.left()),  r.bottom() - tail_depth),
            QPoint(r.left(),              r.bottom() - tail_depth),
        ]

    def _trapezoid_pts(self, start, end):
        r = QRect(start, end).normalized()
        inset = r.width() // 4
        if self.trapezoid_flip:
            return [QPoint(r.left(), r.top()),
                    QPoint(r.right(), r.top()),
                    QPoint(r.right() - inset, r.bottom()),
                    QPoint(r.left() + inset, r.bottom())]
        return [QPoint(r.left() + inset, r.top()),
                QPoint(r.right() - inset, r.top()),
                QPoint(r.right(), r.bottom()),
                QPoint(r.left(), r.bottom())]

    def _star_pts(self, start, end):
        cx, cy = start.x(), start.y()
        r_outer = int(math.hypot(end.x() - cx, end.y() - cy))
        r_inner = r_outer // 2
        n = self.star_corners
        pts = []
        for i in range(n * 2):
            angle = math.pi / n * i - math.pi / 2
            r = r_outer if i % 2 == 0 else r_inner
            pts.append(QPoint(int(cx + r * math.cos(angle)), int(cy + r * math.sin(angle))))
        return pts

    def _heart_pts(self, start, end):
        r = QRect(start, end).normalized()
        l, t, ri, b = float(r.left()), float(r.top()), float(r.right()), float(r.bottom())
        cx = (l + ri) / 2.0
        w, h = ri - l, b - t
        # top-center dip sits at ~30% down
        dip_y = t + h * 0.30
        # each lobe peak is at 25% from center, at the top
        lobe_y = t
        path = QPainterPath()
        path.moveTo(cx, b)                          # bottom point
        # left half: bottom-point -> dip
        path.cubicTo(l  - w * 0.05, t + h * 0.65,  # ctrl1: far left, mid
                     l  - w * 0.05, dip_y,          # ctrl2: far left, dip level
                     cx, dip_y)                     # end: top-center dip
        # right half: dip -> bottom-point
        path.cubicTo(ri + w * 0.05, dip_y,          # ctrl1: far right, dip level
                     ri + w * 0.05, t + h * 0.65,   # ctrl2: far right, mid
                     cx, b)                         # end: bottom point
        path.closeSubpath()
        # Now carve the two lobes as a separate subpath using OddEvenFill
        # Actually, build the full outline in one continuous path:
        # Restart with proper lobe shape
        path2 = QPainterPath()
        path2.moveTo(cx, dip_y)
        # left lobe: dip -> left-peak -> bottom-left -> bottom-point
        path2.cubicTo(cx - w * 0.15, t - h * 0.05,
                      l  - w * 0.05, t - h * 0.05,
                      l  - w * 0.05, dip_y)
        path2.cubicTo(l  - w * 0.05, t + h * 0.65,
                      cx - w * 0.1,  t + h * 0.80,
                      cx, b)
        # right lobe: bottom-point -> bottom-right -> right-peak -> dip
        path2.cubicTo(cx + w * 0.1,  t + h * 0.80,
                      ri + w * 0.05, t + h * 0.65,
                      ri + w * 0.05, dip_y)
        path2.cubicTo(ri + w * 0.05, t - h * 0.05,
                      cx + w * 0.15, t - h * 0.05,
                      cx, dip_y)
        path2.closeSubpath()
        return path2

    def _lightning_pts(self, start, end):
        r = QRect(start, end).normalized()
        l, t, ri, b = r.left(), r.top(), r.right(), r.bottom()
        w, h = r.width(), r.height()
        def p(fx, fy): return QPoint(l + int(w * fx), t + int(h * fy))
        # Bolt with two zig-zags, no crossing sides.
        # Left edge:  top-left -> kink1-inner-left -> kink1-outer-left
        #             -> kink2-inner-left -> kink2-outer-left -> tip
        # Right edge: tip -> kink2-outer-right -> kink2-inner-right
        #             -> kink1-outer-right -> kink1-inner-right -> top-right
        return [
            p(0.62, 0.12),  # top-right
            p(0.28, 0.00),  # top-left
            p(0.46, 0.33),  # kink1 inner-left
            p(0.30, 0.33),  # kink1 outer-left
            p(0.54, 0.58),  # kink2 inner-left
            p(0.38, 0.58),  # kink2 outer-left
            p(0.72, 1.00),  # bottom tip
            p(0.62, 0.68),  # kink2 outer-right
            p(0.70, 0.68),  # kink2 inner-right
            p(0.54, 0.43),  # kink1 outer-right
            p(0.62, 0.43),  # kink1 inner-right
        ]

    def _cross_pts(self, start, end):
        r = QRect(start, end).normalized()
        w3, h3 = r.width() // 3, r.height() // 3
        l, t, ri, b = r.left(), r.top(), r.right(), r.bottom()
        return [
            QPoint(l + w3, t),       QPoint(ri - w3, t),
            QPoint(ri - w3, t + h3), QPoint(ri, t + h3),
            QPoint(ri, b - h3),      QPoint(ri - w3, b - h3),
            QPoint(ri - w3, b),      QPoint(l + w3, b),
            QPoint(l + w3, b - h3),  QPoint(l, b - h3),
            QPoint(l, t + h3),       QPoint(l + w3, t + h3),
        ]

    def _snap_to_grid(self, pos, is_end=False):
        if self._grid_snap and self._grid_visible and self._grid_w > 0 and self._grid_h > 0:
            x = round(pos.x() / self._grid_w) * self._grid_w
            y = round(pos.y() / self._grid_h) * self._grid_h
            if is_end:
                x = max(0, x - 1)
                y = max(0, y - 1)
            return QPoint(x, y)
        return pos

    def _ngon_pts(self, start, end):
        cx, cy = start.x(), start.y()
        r = int(math.hypot(end.x() - cx, end.y() - cy))
        n = self.ngon_edges
        pts = []
        for i in range(n):
            angle = 2 * math.pi / n * i - math.pi / 2
            pts.append(QPoint(int(cx + r * math.cos(angle)), int(cy + r * math.sin(angle))))
        return pts

    def _march_ants(self):
        if self.cut_mode == "wand":
            pass
        else:
            step = -1 if self.cut_op == "copy" else (1 if self.cut_op == "cut" else 0)
            self._dash_offset = (self._dash_offset + step) % 8
        self.update()

    def _do_blink(self):
        self._blink_phase = not self._blink_phase
        self.update()

    def _sel_rubber_rect(self, start, end):
        if self.cut_mode == "circle":
            rad = int(math.hypot(end.x() - start.x(), end.y() - start.y()))
            return QRect(start.x() - rad, start.y() - rad, rad * 2, rad * 2)
        return QRect(start, end).normalized()

    def _magic_wand_select(self, pos):
        self._push_undo()
        x0, y0 = pos.x(), pos.y()
        w, h = self.image.width(), self.image.height()
        if not (0 <= x0 < w and 0 <= y0 < h):
            return
        target = self.image.pixel(x0, y0)
        visited = set()
        stack = [(x0, y0)]
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited or not (0 <= cx < w and 0 <= cy < h):
                continue
            if self.image.pixel(cx, cy) != target:
                continue
            visited.add((cx, cy))
            stack += [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]
        if not visited:
            return
        xs = [p[0] for p in visited]
        ys = [p[1] for p in visited]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        rect = QRect(x1, y1, x2 - x1 + 1, y2 - y1 + 1)
        mask_img = QImage(rect.size(), QImage.Format_ARGB32)
        mask_img.fill(Qt.transparent)
        for (px, py) in visited:
            mask_img.setPixel(px - x1, py - y1, 0xFF000000)
        mask_pix = QPixmap.fromImage(mask_img)
        self._wand_mask_img = mask_img.copy()
        self._cut_pixmap = QPixmap.fromImage(self.image.copy(rect))
        self._cut_pixmap.setMask(mask_pix.createMaskFromColor(Qt.transparent))
        self._cut_pixmap_base = self._cut_pixmap
        self._cut_rect = rect
        self._selection_rect = rect
        self._cut_pos = rect.topLeft()
        # boundary path in local coords (origin = rect.topLeft)
        path = QPainterPath()
        for (px, py) in visited:
            lx, ly = px - x1, py - y1
            if (px, py - 1) not in visited:
                path.moveTo(lx, ly);     path.lineTo(lx + 1, ly)
            if (px, py + 1) not in visited:
                path.moveTo(lx, ly + 1); path.lineTo(lx + 1, ly + 1)
            if (px - 1, py) not in visited:
                path.moveTo(lx, ly);     path.lineTo(lx, ly + 1)
            if (px + 1, py) not in visited:
                path.moveTo(lx + 1, ly); path.lineTo(lx + 1, ly + 1)
        self._wand_path = path
        self._wand_click_pos = (x0, y0)
        tc = QColor(target)
        self._wand_color = tc
        self._wand_inv_color = QColor(255 - tc.red(), 255 - tc.green(), 255 - tc.blue())
        self._sel_color = self._wand_inv_color
        self._blink_phase = False
        if self.cut_op == "cut":
            for img in ([self.image, self._color_image] if self._color_image else [self.image]):
                p = QPainter(img)
                for (px, py) in visited:
                    p.fillRect(px, py, 1, 1, self.bg_color)
                p.end()
            if self._color_image:
                self._sync_gray()
        elif self.cut_op == "copy":
            self._copy_source_pixmap = self._cut_pixmap.copy()
        elif self.cut_op == "select":
            self._cut_pixmap = None
            self._cut_pixmap_base = None
        self._march_timer.start(100)
        self._blink_timer.start(500)
        self.update()
        if hasattr(self, "main_window") and self.cut_op == "select":
            self.main_window.recorder.record(
                f"canvas.set_selection('wand', {x0}, {y0}, {rect.width()}, {rect.height()})")

    def _lasso_freeform_select(self):
        if len(self._lasso_pts) < 3:
            self._lasso_pts = []
            return
        xs = [p[0] for p in self._lasso_pts]
        ys = [p[1] for p in self._lasso_pts]
        x1, y1 = max(0, min(xs)), max(0, min(ys))
        x2, y2 = min(self.image.width() - 1, max(xs)), min(self.image.height() - 1, max(ys))
        if x2 <= x1 or y2 <= y1:
            self._lasso_pts = []
            return
        rect = QRect(x1, y1, x2 - x1 + 1, y2 - y1 + 1)
        poly = QPolygon([QPoint(p[0], p[1]) for p in self._lasso_pts])
        mask_img = QImage(rect.size(), QImage.Format_ARGB32)
        mask_img.fill(Qt.transparent)
        mp = QPainter(mask_img)
        mp.setRenderHint(QPainter.Antialiasing, False)
        mp.translate(-x1, -y1)
        mp.setBrush(Qt.black)
        mp.setPen(Qt.NoPen)
        mp.drawPolygon(poly)
        mp.end()
        mask_pix = QPixmap.fromImage(mask_img)
        self._cut_pixmap = QPixmap.fromImage(self.image.copy(rect))
        self._cut_pixmap.setMask(mask_pix.createMaskFromColor(Qt.transparent))
        self._cut_pixmap_base = self._cut_pixmap
        self._cut_rect = rect
        self._selection_rect = rect
        self._cut_pos = rect.topLeft()
        self._lasso_origin = rect.topLeft()
        if self.cut_op == "copy":
            self._copy_source_pixmap = self._cut_pixmap.copy()
            self._copy_lasso_pts = list(self._lasso_pts)
        else:
            self._copy_lasso_pts = list(self._lasso_pts)
        if self.cut_op == "select":
            self._cut_pixmap = None
            self._cut_pixmap_base = None
        self._push_undo()
        self._lasso_pending_blink = True
        self._march_timer.start(100)
        self.update()

    def _cancel_cut(self):
        if self._cut_pixmap and self._cut_rect:
            self._cut_pos = self._cut_rect.topLeft()
        self._commit_cut()
        self._selection_rect = None
        self._copy_source_pixmap = None
        self._start_pos = None
        self._drag_end_pos = None
        self._lasso_pts = []
        self._copy_lasso_pts = []
        self._wand_path = None
        self._wand_mask_img = None
        self._wand_click_pos = None
        self._blink_phase = False
        self._resizing_cut = False
        self._resize_cut_handle = None
        self._resize_cut_origin_rect = None
        self._resize_cut_origin_pixmap = None
        self._march_timer.stop()
        self._blink_timer.stop()
        self.update()

    def _erase_at(self, pos, clip_rect=None):
        ex = pos.x() - self.eraser_width // 2
        ey = pos.y() - self.eraser_width // 2
        for img in ([self.image, self._color_image] if self._color_image else [self.image]):
            p = QPainter(img)
            if clip_rect:
                p.setClipRect(clip_rect)
            p.fillRect(ex, ey, self.eraser_width, self.eraser_width, self.bg_color)
            p.end()
        if self._color_image:
            self._sync_gray()
        self._mod()
        self.update()

    def _draw_dot(self, pos, color):
        cx, cy = pos.x(), pos.y()
        is_left = (color is self.pen_color)
        pw = self.pen_width if is_left else self.pen_width2
        r = pw // 2
        smooth_pct = self.pen_smooth_pct1 if is_left else self.pen_smooth_pct2
        use_smooth = (self.pen_smooth1 if is_left else self.pen_smooth2)
        pen_type = self.pen_type1 if is_left else self.pen_type2
        intensity = (self.pen_intensity1 if is_left else self.pen_intensity2) / 100.0
        targets = [self.image, self._color_image] if self._color_image else [self.image]
        w, h = self.image.width(), self.image.height()
        tr, tg, tb = color.red(), color.green(), color.blue()
        if pen_type == "chalk":
            sr = max(r, 2)
            for _ in range(max(1, pw * 3)):
                ox = random.randint(-sr, sr)
                oy = random.randint(-sr, sr)
                if math.hypot(ox, oy) > sr:
                    continue
                px, py = cx + ox, cy + oy
                if not (0 <= px < w and 0 <= py < h):
                    continue
                alpha = random.uniform(0.2, 0.7) * intensity
                for img in targets:
                    existing = QColor(img.pixel(px, py))
                    nr = int(existing.red()   * (1 - alpha) + tr * alpha)
                    ng = int(existing.green() * (1 - alpha) + tg * alpha)
                    nb = int(existing.blue()  * (1 - alpha) + tb * alpha)
                    img.setPixel(px, py, QColor(nr, ng, nb).rgb())
        elif pen_type == "charcoal":
            sr = max(r + 2, 4)
            for dy in range(-sr, sr + 1):
                for dx in range(-sr, sr + 1):
                    dist = math.hypot(dx, dy)
                    if dist > sr:
                        continue
                    px, py = cx + dx, cy + dy
                    if not (0 <= px < w and 0 <= py < h):
                        continue
                    alpha = max(0.0, (1.0 - dist / sr) * 0.6) * random.uniform(0.5, 1.0) * intensity
                    for img in targets:
                        existing = QColor(img.pixel(px, py))
                        nr = int(existing.red()   * (1 - alpha) + tr * alpha)
                        ng = int(existing.green() * (1 - alpha) + tg * alpha)
                        nb = int(existing.blue()  * (1 - alpha) + tb * alpha)
                        img.setPixel(px, py, QColor(nr, ng, nb).rgb())
        elif pen_type == "calligraphy":
            # flat angled nib: wide on one axis, thin on the other
            nib_w = max(pw, 2)
            nib_h = max(pw // 3, 1)
            alpha = intensity
            for dy in range(-nib_h, nib_h + 1):
                for dx in range(-nib_w, nib_w + 1):
                    # rotate nib 45 degrees
                    rx = int(dx * 0.707 - dy * 0.707)
                    ry = int(dx * 0.707 + dy * 0.707)
                    px, py = cx + rx, cy + ry
                    if not (0 <= px < w and 0 <= py < h):
                        continue
                    edge = max(abs(dx) / nib_w, abs(dy) / max(nib_h, 1))
                    a = max(0.0, (1.0 - edge) * alpha)
                    for img in targets:
                        existing = QColor(img.pixel(px, py))
                        nr = int(existing.red()   * (1 - a) + tr * a)
                        ng = int(existing.green() * (1 - a) + tg * a)
                        nb = int(existing.blue()  * (1 - a) + tb * a)
                        img.setPixel(px, py, QColor(nr, ng, nb).rgb())
        elif pen_type == "watercolor":
            sr = max(r + 1, 3)
            for dy in range(-sr, sr + 1):
                for dx in range(-sr, sr + 1):
                    dist = math.hypot(dx, dy)
                    if dist > sr:
                        continue
                    px, py = cx + dx, cy + dy
                    if not (0 <= px < w and 0 <= py < h):
                        continue
                    edge = dist / sr
                    alpha = max(0.0, (1.0 - edge ** 1.5) * 0.35) * random.uniform(0.6, 1.0) * intensity
                    for img in targets:
                        existing = QColor(img.pixel(px, py))
                        nr = int(existing.red()   * (1 - alpha) + tr * alpha)
                        ng = int(existing.green() * (1 - alpha) + tg * alpha)
                        nb = int(existing.blue()  * (1 - alpha) + tb * alpha)
                        img.setPixel(px, py, QColor(nr, ng, nb).rgb())
        elif pen_type == "oil":
            sr = max(r, 1)
            for dy in range(-sr, sr + 1):
                for dx in range(-sr, sr + 1):
                    dist = math.hypot(dx, dy)
                    if dist > sr:
                        continue
                    px, py = cx + dx, cy + dy
                    if not (0 <= px < w and 0 <= py < h):
                        continue
                    t = 1.0 - dist / sr
                    for img in targets:
                        existing = QColor(img.pixel(px, py))
                        mix = 0.5 * t * intensity
                        nr = int(existing.red()   * (1 - mix) + tr * mix)
                        ng = int(existing.green() * (1 - mix) + tg * mix)
                        nb = int(existing.blue()  * (1 - mix) + tb * mix)
                        img.setPixel(px, py, QColor(nr, ng, nb).rgb())
        elif pen_type == "glow":
            sr = max(r * 3, 6)
            for dy in range(-sr, sr + 1):
                for dx in range(-sr, sr + 1):
                    dist = math.hypot(dx, dy)
                    if dist > sr:
                        continue
                    px, py = cx + dx, cy + dy
                    if not (0 <= px < w and 0 <= py < h):
                        continue
                    alpha = max(0.0, 1.0 - (dist / sr) ** 1.5) * (1.0 if dist <= r else 0.4) * intensity
                    for img in targets:
                        existing = QColor(img.pixel(px, py))
                        nr = min(255, int(existing.red()   * (1 - alpha) + tr * alpha))
                        ng = min(255, int(existing.green() * (1 - alpha) + tg * alpha))
                        nb = min(255, int(existing.blue()  * (1 - alpha) + tb * alpha))
                        img.setPixel(px, py, QColor(nr, ng, nb).rgb())
        elif pen_type == "neon":
            core_r = max(r, 1)
            bloom_r = max(r * 4, 8)
            for dy in range(-bloom_r, bloom_r + 1):
                for dx in range(-bloom_r, bloom_r + 1):
                    dist = math.hypot(dx, dy)
                    if dist > bloom_r:
                        continue
                    px, py = cx + dx, cy + dy
                    if not (0 <= px < w and 0 <= py < h):
                        continue
                    if dist <= core_r:
                        wr = min(255, tr + 80)
                        wg = min(255, tg + 80)
                        wb = min(255, tb + 80)
                        alpha = intensity
                        for img in targets:
                            existing = QColor(img.pixel(px, py))
                            nr = min(255, int(existing.red()   * (1 - alpha) + wr * alpha))
                            ng = min(255, int(existing.green() * (1 - alpha) + wg * alpha))
                            nb = min(255, int(existing.blue()  * (1 - alpha) + wb * alpha))
                            img.setPixel(px, py, QColor(nr, ng, nb).rgb())
                    else:
                        alpha = max(0.0, (1.0 - dist / bloom_r) ** 2) * 0.6 * intensity
                        for img in targets:
                            existing = QColor(img.pixel(px, py))
                            nr = min(255, int(existing.red()   * (1 - alpha) + tr * alpha))
                            ng = min(255, int(existing.green() * (1 - alpha) + tg * alpha))
                            nb = min(255, int(existing.blue()  * (1 - alpha) + tb * alpha))
                            img.setPixel(px, py, QColor(nr, ng, nb).rgb())
        else:  # normal
            if not use_smooth:
                if intensity >= 1.0:
                    if pw == 1:
                        for img in targets:
                            if 0 <= cx < img.width() and 0 <= cy < img.height():
                                img.setPixel(cx, cy, color.rgb())
                    else:
                        for img in targets:
                            p = QPainter(img)
                            p.setBrush(QBrush(color))
                            p.setPen(Qt.NoPen)
                            p.drawRect(cx - r, cy - r, pw, pw)
                            p.end()
                else:
                    pts = [(cx, cy)] if pw == 1 else [(cx + dx, cy + dy) for dy in range(-r, r + 1) for dx in range(-r, r + 1)]
                    for px, py in pts:
                        if not (0 <= px < w and 0 <= py < h):
                            continue
                        for img in targets:
                            existing = QColor(img.pixel(px, py))
                            nr = int(existing.red()   * (1 - intensity) + tr * intensity)
                            ng = int(existing.green() * (1 - intensity) + tg * intensity)
                            nb = int(existing.blue()  * (1 - intensity) + tb * intensity)
                            img.setPixel(px, py, QColor(nr, ng, nb).rgb())
            else:
                sr = max(r, 1)
                strength = smooth_pct / 100.0
                for dy in range(-sr, sr + 1):
                    for dx in range(-sr, sr + 1):
                        dist = math.hypot(dx, dy)
                        if dist > sr:
                            continue
                        px, py = cx + dx, cy + dy
                        if not (0 <= px < w and 0 <= py < h):
                            continue
                        t = (1.0 - (dist / sr) * strength) * intensity
                        for img in targets:
                            existing = QColor(img.pixel(px, py))
                            nr = int(existing.red()   * (1 - t) + tr * t)
                            ng = int(existing.green() * (1 - t) + tg * t)
                            nb = int(existing.blue()  * (1 - t) + tb * t)
                            img.setPixel(px, py, QColor(nr, ng, nb).rgb())
        if self._color_image:
            self._sync_gray()
        self.update()

    def _spray_tick(self):
        if self._spray_pos is None or self._spray_color is None:
            return
        pos, color = self._spray_pos, self._spray_color
        is_left = (color is self.pen_color)
        density = self.spray_density  if is_left else self.spray_density2
        r       = self.spray_radius   if is_left else self.spray_radius2
        targets = [self.image, self._color_image] if self._color_image else [self.image]
        sel = self._selection_rect
        for _ in range(density):
            angle = random.uniform(0, 2 * math.pi)
            dist  = random.uniform(0, r)
            px = int(pos.x() + dist * math.cos(angle))
            py = int(pos.y() + dist * math.sin(angle))
            if sel and not sel.contains(px, py):
                continue
            for img in targets:
                if 0 <= px < img.width() and 0 <= py < img.height():
                    img.setPixel(px, py, color.rgb())
        if self._color_image:
            self._sync_gray()
        self._mod()
        self.update()

    def _draw_dot_symmetric(self, pos, color):
        w, h = self.image.width(), self.image.height()
        pts = [pos]
        if self.symmetry_h:
            pts.append(QPoint(w - 1 - pos.x(), pos.y()))
        if self.symmetry_v:
            pts.append(QPoint(pos.x(), h - 1 - pos.y()))
        if self.symmetry_h and self.symmetry_v:
            pts.append(QPoint(w - 1 - pos.x(), h - 1 - pos.y()))
        for p in pts:
            self._draw_dot(p, color)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Alt and self.tool != "picker":
            self._prev_tool = self.tool
            self.tool = "picker"
            self.setCursor(Qt.CrossCursor)
            if hasattr(self, "main_window"):
                self.main_window._highlight_tool("picker")
        elif event.key() == Qt.Key_Escape:
            if self.tool == "cut":
                if hasattr(self, "main_window"):
                    self.main_window.recorder.cancel_last_selection()
                self._cancel_cut()
            elif self.tool == "ruler":
                self._ruler_start = None
                self._ruler_end = None
                if hasattr(self, 'main_window'):
                    mw = self.main_window
                    mw._ruler_dx_label.setText("ΔX: —")
                    mw._ruler_dy_label.setText("ΔY: —")
                    mw._ruler_len_label.setText("Length: —")
                    mw._ruler_angle_label.setText("Angle: —")
                self.update()
        elif event.key() == Qt.Key_Delete:
            if self.tool == "cut" and (self._selection_rect or self._cut_pixmap):
                self._push_undo()
                r = self._cut_rect if (self._cut_pixmap and self._cut_rect) else self._selection_rect
                lasso_pts = self._lasso_pts or self._copy_lasso_pts
                if r:
                    for img in ([self.image, self._color_image] if self._color_image else [self.image]):
                        p = QPainter(img)
                        p.setBrush(self.bg_color)
                        p.setPen(Qt.NoPen)
                        if self.cut_mode == "lasso" and lasso_pts:
                            p.drawPolygon(QPolygon([QPoint(pt[0], pt[1]) for pt in lasso_pts]))
                        elif self.cut_mode in ("circle", "ellipse"):
                            p.drawEllipse(r)
                        elif self.cut_mode == "wand" and self._wand_mask_img:
                            ox, oy = r.x(), r.y()
                            for wy in range(self._wand_mask_img.height()):
                                for wx in range(self._wand_mask_img.width()):
                                    if self._wand_mask_img.pixel(wx, wy) & 0xFF000000:
                                        p.fillRect(ox + wx, oy + wy, 1, 1, self.bg_color)
                        else:
                            p.fillRect(r, self.bg_color)
                        p.end()
                if self._color_image:
                    self._sync_gray()
                # discard the floating pixmap so _cancel_cut/_commit_cut won't draw it back
                self._cut_pixmap = None
                self._cut_pixmap_base = None
                self._cancel_cut()
                self._mod()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Alt and self._prev_tool is not None:
            self.tool = self._prev_tool
            self._prev_tool = None
            self.unsetCursor()
            if hasattr(self, "main_window"):
                self.main_window._highlight_tool(self.tool)
        else:
            super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.SizeAllCursor)
            return
        pos = self._to_canvas_pos(event.pos())
        if event.button() == Qt.RightButton and self.tool == "ruler":
            self._ruler_start = None
            self._ruler_end = None
            if hasattr(self, 'main_window'):
                mw = self.main_window
                mw._ruler_dx_label.setText("ΔX: —")
                mw._ruler_dy_label.setText("ΔY: —")
                mw._ruler_len_label.setText("Length: —")
                mw._ruler_angle_label.setText("Angle: —")
            self.update()
            return
        if event.button() == Qt.RightButton and self.tool in ("pencil", "spray"):
            if self.tool == "spray":
                self._push_undo()
                self._spray_pos = pos
                self._spray_pts = [pos]
                self._spray_color = self.pen_color2
                self._spray_tick()
                self._spray_timer.start(50)
                self._mod()
                return
            self._push_undo()
            self._stroke_pts2 = [pos]
            self._draw_dot_symmetric(pos, self.pen_color2)
            self._mod()
            return
        if event.button() == Qt.RightButton and self.tool == "picker":
            if 0 <= pos.x() < self.image.width() and 0 <= pos.y() < self.image.height():
                r = self.picker_sample_radius2
                if r == 0:
                    self._picked_color2.emit(QColor(self.image.pixel(pos.x(), pos.y())))
                else:
                    w, h = self.image.width(), self.image.height()
                    rs, gs, bs, n = 0, 0, 0, 0
                    for dy in range(-r, r+1):
                        for dx in range(-r, r+1):
                            px, py = pos.x()+dx, pos.y()+dy
                            if 0 <= px < w and 0 <= py < h:
                                c = QColor(self.image.pixel(px, py))
                                rs += c.red(); gs += c.green(); bs += c.blue(); n += 1
                    if n: self._picked_color2.emit(QColor(rs//n, gs//n, bs//n))
            return
        if event.button() == Qt.RightButton and self.tool == "fill":
            self._push_undo()
            self._flood_fill(pos, self.fill_color2, self._selection_rect, tolerance=self.fill_tolerance2)
            self._mod()
            self.update()
            if hasattr(self, "main_window"):
                fc = self.fill_color2.name()
                if self.cut_mode == 'wand' and self._selection_rect and hasattr(self, '_wand_click_pos') and self._wand_click_pos:
                    wx, wy = self._wand_click_pos
                    r = self._selection_rect
                    self.main_window.recorder.record(
                        f"canvas.set_selection('wand', {wx}, {wy}, {r.width()}, {r.height()})")
                self.main_window.recorder.record(
                    f"canvas.fill(({pos.x()},{pos.y()}), color=__{fc}__, tolerance={self.fill_tolerance2})")
            return
        if event.button() == Qt.LeftButton:
            if self.tool == "ruler":
                self._ruler_start = pos
                self._ruler_end = None
                self.update()
                return
            if self.tool == "picker":
                if 0 <= pos.x() < self.image.width() and 0 <= pos.y() < self.image.height():
                    r = self.picker_sample_radius
                    if r == 0:
                        self._picked_color.emit(QColor(self.image.pixel(pos.x(), pos.y())))
                    else:
                        w, h = self.image.width(), self.image.height()
                        rs, gs, bs, n = 0, 0, 0, 0
                        for dy in range(-r, r+1):
                            for dx in range(-r, r+1):
                                px, py = pos.x()+dx, pos.y()+dy
                                if 0 <= px < w and 0 <= py < h:
                                    c = QColor(self.image.pixel(px, py))
                                    rs += c.red(); gs += c.green(); bs += c.blue(); n += 1
                        if n: self._picked_color.emit(QColor(rs//n, gs//n, bs//n))
                return
            if self.tool == "eraser":
                self._push_undo()
                self._erase_at(pos, self._selection_rect)
                self._mod()
                return
            if self.tool == "text":
                self._push_undo()
                for img in ([self.image, self._color_image] if self._color_image else [self.image]):
                    p = QPainter(img)
                    self._draw_text_at(p, pos, to_image=True)
                    p.end()
                if self._color_image:
                    self._sync_gray()
                self._mod()
                self.update()
                if hasattr(self, "main_window"):
                    f = self.text_font; tc = self.text_color.name()
                    bg = self.text_bg_color.name(); bgt = self.text_bg_transparent
                    self.main_window.recorder.record(
                        f"canvas.draw_text({self.text_str!r}, ({pos.x()},{pos.y()}), "
                        f"font={f.family()!r}, size={f.pointSize()}, bold={f.bold()}, "
                        f"italic={f.italic()}, underline={f.underline()}, "
                        f"color=__{tc}__, bg_color=__{bg}__, bg_transparent={bgt}, "
                        f"box={self.text_box}, box_style={self.text_box_style!r}, "
                        f"box_width={self.text_box_width})")
                return
            if self.tool == "pencil":
                self._push_undo()
                self._stroke_pts = [pos]
                self._draw_dot_symmetric(pos, self.pen_color)
                self._mod()
            elif self.tool == "spray":
                self._push_undo()
                self._spray_pos = pos
                self._spray_pts = [pos]
                self._spray_color = self.pen_color
                self._spray_tick()
                self._spray_timer.start(50)
                self._mod()
            elif self.tool == "forms":
                self._start_pos = self._snap_to_grid(pos)
                self._last_pos = self._start_pos
                self._preview_image = self.image.copy()
            elif self.tool == "fill":
                self._push_undo()
                self._flood_fill(pos, self.fill_color, self._selection_rect)
                self._mod()
                self.update()
                if hasattr(self, "main_window"):
                    fc = self.fill_color.name()
                    if self.cut_mode == 'wand' and self._selection_rect and hasattr(self, '_wand_click_pos') and self._wand_click_pos:
                        wx, wy = self._wand_click_pos
                        r = self._selection_rect
                        self.main_window.recorder.record(
                            f"canvas.set_selection('wand', {wx}, {wy}, {r.width()}, {r.height()})")
                    self.main_window.recorder.record(
                        f"canvas.fill(({pos.x()},{pos.y()}), color=__{fc}__, tolerance={self.fill_tolerance})")
            elif self.tool == "cut":
                if self.selection_resize_enabled and self._selection_rect and not self._cut_pixmap and self.cut_op == "select" and self.cut_mode not in ("lasso", "wand") and not self._dragging_cut:
                    h = self._hit_handle_rect(self._selection_rect, pos)
                    if h:
                        self._resize_handle = h
                        self._resize_origin_rect = QRect(self._selection_rect)
                        return
                if self.selection_resize_enabled and self._cut_pixmap and self._cut_rect and self.cut_op in ("cut", "copy") and self.cut_mode not in ("lasso", "wand"):
                    h = self._hit_handle_rect(self._cut_rect, pos)
                    if h:
                        self._resizing_cut = True
                        self._resize_cut_handle = h
                        self._resize_cut_origin_rect = QRect(self._cut_rect)
                        self._resize_cut_origin_pixmap = self._cut_pixmap_base
                        return
                if self._cut_pixmap and self._cut_rect:
                    # copy mode: click on origin spawns a new copy (takes priority)
                    if self.cut_op == "copy" and self._copy_source_pixmap and self._selection_rect and self._selection_rect.contains(pos):
                        self._commit_cut()
                        self._push_undo()
                        rect = self._selection_rect
                        self._cut_rect = rect
                        self._cut_pos = rect.topLeft()
                        self._cut_pixmap = self._copy_source_pixmap.copy()
                        if self.cut_mode == "lasso" and self._copy_lasso_pts:
                            self._lasso_pts = list(self._copy_lasso_pts)
                            self._lasso_origin = rect.topLeft()
                        elif self.cut_mode in ("circle", "ellipse"):
                            mask = QPixmap(rect.size())
                            mask.fill(Qt.transparent)
                            mp = QPainter(mask)
                            mp.setRenderHint(QPainter.Antialiasing)
                            mp.setBrush(Qt.black)
                            mp.setPen(Qt.NoPen)
                            mp.drawEllipse(mask.rect())
                            mp.end()
                            self._cut_pixmap.setMask(mask.createMaskFromColor(Qt.transparent))
                        self._cut_pixmap_base = self._cut_pixmap
                        self._dragging_cut = True
                        self._drag_offset = pos - rect.topLeft()
                        self._march_timer.start(100)
                        self._blink_timer.start(500)
                        self.update()
                    elif self._cut_rect.contains(pos):
                        if self.cut_op == "cut" and self.cut_mode == "lasso" and self._lasso_pts:
                            for img in ([self.image, self._color_image] if self._color_image else [self.image]):
                                p = QPainter(img)
                                p.setBrush(self.bg_color)
                                p.setPen(Qt.NoPen)
                                p.drawPolygon(QPolygon([QPoint(pt[0], pt[1]) for pt in self._lasso_pts]))
                                p.end()
                            if self._color_image:
                                self._sync_gray()
                        self._dragging_cut = True
                        self._drag_offset = pos - self._cut_rect.topLeft()
                elif not self._cut_pixmap and self._selection_rect and self._selection_rect.contains(pos) and self.cut_op != "select":
                    self._push_undo()
                    rect = self._selection_rect
                    if 0 <= pos.x() < self.image.width() and 0 <= pos.y() < self.image.height():
                        c = QColor(self.image.pixel(pos.x(), pos.y()))
                        self._sel_color = QColor(255 - c.red(), 255 - c.green(), 255 - c.blue())
                    src = self._copy_source_pixmap if (self.cut_op == "copy" and self._copy_source_pixmap) else QPixmap.fromImage(self.image.copy(rect))
                    self._cut_rect = rect
                    self._cut_pos = rect.topLeft()
                    self._cut_pixmap = src.copy()
                    if self.cut_mode == "lasso" and self._copy_lasso_pts:
                        self._lasso_pts = list(self._copy_lasso_pts)
                        self._lasso_origin = rect.topLeft()
                    elif self.cut_mode in ("circle", "ellipse"):
                        mask = QPixmap(rect.size())
                        mask.fill(Qt.transparent)
                        mp = QPainter(mask)
                        mp.setRenderHint(QPainter.Antialiasing)
                        mp.setBrush(Qt.black)
                        mp.setPen(Qt.NoPen)
                        mp.drawEllipse(mask.rect())
                        mp.end()
                        self._cut_pixmap.setMask(mask.createMaskFromColor(Qt.transparent))
                    self._cut_pixmap_base = self._cut_pixmap
                    if self.cut_op == "cut":
                        for img in ([self.image, self._color_image] if self._color_image else [self.image]):
                            p = QPainter(img)
                            if self.cut_mode in ("circle", "ellipse"):
                                p.setBrush(self.bg_color)
                                p.setPen(Qt.NoPen)
                                p.drawEllipse(rect)
                            else:
                                p.fillRect(rect, self.bg_color)
                            p.end()
                        if self._color_image:
                            self._sync_gray()
                    self._dragging_cut = True
                    self._drag_offset = pos - rect.topLeft()
                    self._march_timer.start(100)
                    self._blink_timer.start(500)
                    self.update()
                elif self.cut_mode == "wand":
                    self._commit_cut()
                    self._magic_wand_select(pos)
                elif self.cut_mode == "lasso":
                    self._commit_cut()
                    self._selection_rect = None
                    self._lasso_pts = [(pos.x(), pos.y())]
                    if 0 <= pos.x() < self.image.width() and 0 <= pos.y() < self.image.height():
                        c = QColor(self.image.pixel(pos.x(), pos.y()))
                        self._sel_color = QColor(255 - c.red(), 255 - c.green(), 255 - c.blue())
                    self._march_timer.start(100)
                else:
                    self._commit_cut()
                    self._selection_rect = None
                    self._start_pos = pos
                    self._drag_end_pos = None
                    if 0 <= pos.x() < self.image.width() and 0 <= pos.y() < self.image.height():
                        c = QColor(self.image.pixel(pos.x(), pos.y()))
                        self._sel_color = QColor(255 - c.red(), 255 - c.green(), 255 - c.blue())

    def _draw_arrow(self, painter, tip, angle, size):
        a1 = angle + math.radians(150)
        a2 = angle - math.radians(150)
        p1 = QPoint(int(tip.x() + size * math.cos(a1)), int(tip.y() + size * math.sin(a1)))
        p2 = QPoint(int(tip.x() + size * math.cos(a2)), int(tip.y() + size * math.sin(a2)))
        painter.setBrush(QBrush(self.pen_color))
        painter.drawPolygon(QPolygon([tip, p1, p2]))

    def _draw_form(self, painter, start, end):
        def _fts(draw_fn):
            """Fill then stroke: draw fill inset by hw, then stroke with NoBrush inset by hw."""
            hw = self.pen_width / 2.0
            if not self.form_fill_transparent:
                painter.setRenderHint(QPainter.Antialiasing, False)
                painter.setPen(Qt.NoPen)
                painter.setBrush(self._make_form_brush())
                draw_fn(hw)
            painter.setRenderHint(QPainter.Antialiasing, self.form_antialias)
            painter.setPen(self._make_form_pen())
            painter.setBrush(Qt.NoBrush)
            draw_fn(hw)

        painter.setRenderHint(QPainter.Antialiasing, self.form_antialias)
        painter.setPen(self._make_form_pen())
        painter.setBrush(self._make_form_brush())
        if self.form_mode == "line":
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            angle = math.atan2(dy, dx)
            size = max(self.pen_width * 4, 10)
            length = math.hypot(dx, dy)
            line_start, line_end = start, end
            if length > 0:
                ux, uy = dx / length, dy / length
                if self.line_arrow_end and not self.line_arrow_inward:
                    line_end = QPoint(int(end.x() - ux * size * 0.6), int(end.y() - uy * size * 0.6))
                if self.line_arrow_start and not self.line_arrow_inward:
                    line_start = QPoint(int(start.x() + ux * size * 0.6), int(start.y() + uy * size * 0.6))
            painter.drawLine(line_start, line_end)
            painter.setPen(Qt.NoPen)
            if self.line_arrow_end:
                if self.line_arrow_inward:
                    self._draw_arrow(painter, start, angle, size)
                else:
                    self._draw_arrow(painter, end, angle, size)
            if self.line_arrow_start:
                if self.line_arrow_inward:
                    self._draw_arrow(painter, end, angle + math.pi, size)
                else:
                    self._draw_arrow(painter, start, angle + math.pi, size)
        elif self.form_mode == "circle":
            r = int(math.hypot(end.x() - start.x(), end.y() - start.y()))
            if self.circle_donut and r > self.donut_gap:
                r_inner = r - self.donut_gap
                cx, cy = float(start.x()), float(start.y())
                if self.circle_span_angle >= 360:
                    path = QPainterPath()
                    path.setFillRule(Qt.OddEvenFill)
                    path.addEllipse(QPointF(start), r, r)
                    path.addEllipse(QPointF(start), r_inner, r_inner)
                    painter.drawPath(path)
                else:
                    start_a = 90.0 - self.circle_start_angle
                    span_a  = -float(self.circle_span_angle)
                    outer = QRectF(cx - r, cy - r, r * 2, r * 2)
                    inner = QRectF(cx - r_inner, cy - r_inner, r_inner * 2, r_inner * 2)
                    path = QPainterPath()
                    path.arcMoveTo(outer, start_a)
                    path.arcTo(outer, start_a, span_a)
                    path.arcTo(inner, start_a + span_a, -span_a)
                    path.closeSubpath()
                    painter.drawPath(path)
            elif self.circle_span_angle >= 360:
                def _draw_circle(hw):
                    painter.drawEllipse(QPointF(start), r - hw, r - hw)
                _fts(_draw_circle)
            else:
                rect = QRect(start.x() - r, start.y() - r, r * 2, r * 2)
                start_a = (90 - self.circle_start_angle) * 16
                span_a  = -self.circle_span_angle * 16
                if self.circle_pie_mode:
                    painter.drawPie(rect, start_a, span_a)
                else:
                    painter.drawArc(rect, start_a, span_a)
        elif self.form_mode == "ellipse":
            r = QRectF(QRect(start, end).normalized())
            def _draw_ellipse(hw):
                painter.drawEllipse(r.adjusted(hw, hw, -hw, -hw))
            _fts(_draw_ellipse)
        elif self.form_mode == "triangle":
            def _draw_tri(hw): painter.drawPolygon(QPolygon(self._triangle_pts(start, end)))
            _fts(_draw_tri)
        elif self.form_mode == "trapezoid":
            def _draw_trap(hw): painter.drawPolygon(QPolygon(self._trapezoid_pts(start, end)))
            _fts(_draw_trap)
        elif self.form_mode == "arrow":
            def _draw_arrow2(hw): painter.drawPolygon(QPolygon(self._arrow_shape_pts(start, end)))
            _fts(_draw_arrow2)
        elif self.form_mode == "parallelogram":
            def _draw_para(hw): painter.drawPolygon(QPolygon(self._parallelogram_pts(start, end)))
            _fts(_draw_para)
        elif self.form_mode == "callout":
            def _draw_call(hw): painter.drawPolygon(QPolygon(self._callout_pts(start, end)))
            _fts(_draw_call)
        elif self.form_mode == "star":
            def _draw_star(hw): painter.drawPolygon(QPolygon(self._star_pts(start, end)))
            _fts(_draw_star)
        elif self.form_mode == "cross":
            def _draw_cross(hw): painter.drawPolygon(QPolygon(self._cross_pts(start, end)))
            _fts(_draw_cross)
        elif self.form_mode == "heart":
            def _draw_heart(hw): painter.drawPath(self._heart_pts(start, end))
            _fts(_draw_heart)
        elif self.form_mode == "lightning":
            def _draw_lightning(hw): painter.drawPolygon(QPolygon(self._lightning_pts(start, end)))
            _fts(_draw_lightning)
        elif self.form_mode == "ngon":
            def _draw_ngon(hw): painter.drawPolygon(QPolygon(self._ngon_pts(start, end)))
            _fts(_draw_ngon)
        else:
            r = QRectF(QRect(start, end).normalized())
            cr = self.rect_corner_radius
            def _draw_rect(hw):
                ri = r.adjusted(hw, hw, -hw, -hw)
                if cr > 0:
                    painter.drawRoundedRect(ri, cr, cr)
                else:
                    painter.drawRect(ri)
            _fts(_draw_rect)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.pos() - self._pan_start
            self._offset += delta
            self._pan_start = event.pos()
            self.update()
            return
        pos = self._to_canvas_pos(event.pos())
        if 0 <= pos.x() < self.image.width() and 0 <= pos.y() < self.image.height():
            self.mouse_moved.emit(pos.x(), pos.y())
        if self.tool == "eraser":
            self._update_eraser_cursor()
            if event.buttons() & Qt.LeftButton:
                self._erase_at(pos, self._selection_rect)
            return
        elif self.tool == "ruler":
            self.setCursor(Qt.ArrowCursor)
            if event.buttons() & Qt.LeftButton and self._ruler_start:
                self._ruler_end = pos
                dx = pos.x() - self._ruler_start.x()
                dy = pos.y() - self._ruler_start.y()
                dist = math.hypot(dx, dy)
                angle = math.degrees(math.atan2(dy, dx))
                if hasattr(self, 'main_window'):
                    mw = self.main_window
                    mw._ruler_dx_label.setText(f"ΔX: {dx} px")
                    mw._ruler_dy_label.setText(f"ΔY: {dy} px")
                    mw._ruler_len_label.setText(f"Length: {dist:.1f} px")
                    mw._ruler_angle_label.setText(f"Angle: {angle:.1f}°")
                self.update()
            return
        elif self.tool == "text":
            self._text_cursor_pos = pos
            self.setCursor(Qt.BlankCursor)
            self.update()
            return
        elif self.tool == "pencil":
            self._pencil_cursor_pos = pos
            self._update_pen_cursor()
            if event.buttons() & Qt.LeftButton:
                self._pencil_active_btn = "left"
                self._stroke_pts.append(pos)
                self._draw_dot_symmetric(pos, self.pen_color)
            elif event.buttons() & Qt.RightButton:
                self._pencil_active_btn = "right"
                self._stroke_pts2.append(pos)
                self._draw_dot_symmetric(pos, self.pen_color2)
            else:
                self._pencil_active_btn = None
                self.update()
            return
        elif self.tool == "spray":
            self.setCursor(Qt.CrossCursor)
            if event.buttons() & Qt.LeftButton:
                self._spray_pos = pos
                self._spray_pts.append(pos)
                self._spray_color = self.pen_color
            elif event.buttons() & Qt.RightButton:
                self._spray_pos = pos
                self._spray_pts.append(pos)
                self._spray_color = self.pen_color2
            return
        elif self.tool == "forms":
            self._update_pen_cursor()
        elif self.tool == "picker":
            self.setCursor(Qt.CrossCursor)
        elif self.tool == "cut":
            if self._resize_handle:
                self.setCursor(Qt.SizeFDiagCursor)
            elif self._resizing_cut:
                self.setCursor(Qt.SizeFDiagCursor)
            elif self._dragging_cut:
                self.setCursor(Qt.ClosedHandCursor)
            elif self.selection_resize_enabled and self.cut_op == "select" and self.cut_mode not in ("lasso", "wand") and self._selection_rect and self._hit_handle_rect(self._selection_rect, pos):
                self.setCursor(Qt.SizeFDiagCursor)
            elif self.selection_resize_enabled and self._cut_pixmap and self._cut_rect and self.cut_op in ("cut", "copy") and self.cut_mode not in ("lasso", "wand") and self._hit_handle_rect(self._cut_rect, pos):
                h = self._hit_handle_rect(self._cut_rect, pos)
                if h in ("tl", "br", "tr", "bl"): self.setCursor(Qt.SizeFDiagCursor)
                elif h in ("tc", "bc"): self.setCursor(Qt.SizeVerCursor)
                else: self.setCursor(Qt.SizeHorCursor)
            elif self._cut_pixmap and self._cut_rect and self._cut_rect.contains(pos):
                self.setCursor(Qt.OpenHandCursor)
            elif self.cut_op == "copy" and self._selection_rect and self._selection_rect.contains(pos) and not (self._cut_rect and self._cut_rect.contains(pos)):
                self.setCursor(Qt.DragCopyCursor)
            else:
                self.unsetCursor()
        else:
            self.unsetCursor()
        if event.buttons() & Qt.LeftButton:
            if self._resize_handle and self._resize_origin_rect:
                orig = self._resize_origin_rect
                h = self._resize_handle
                new_r = QRect(orig)
                if 'l' in h: new_r.setLeft(pos.x())
                if 'r' in h: new_r.setRight(pos.x())
                if 't' in h: new_r.setTop(pos.y())
                if 'b' in h: new_r.setBottom(pos.y())
                new_r = new_r.normalized()
                if new_r.width() > 4 and new_r.height() > 4:
                    self._selection_rect = new_r
                    self.update()
                return
            if self.tool == "forms" and self._start_pos is not None:
                snapped = self._snap_to_grid(pos, is_end=True)
                self._preview_image = self.image.copy()
                p = QPainter(self._preview_image)
                self._draw_form(p, self._start_pos, snapped)
                p.end()
                self.update()
                self.main_window._update_form_dim(self._start_pos, snapped)
            elif self.tool == "cut":
                if self._resizing_cut and self._resize_cut_origin_rect and self._resize_cut_origin_pixmap:
                    orig = self._resize_cut_origin_rect
                    h = self._resize_cut_handle
                    new_r = QRect(orig)
                    if "l" in h: new_r.setLeft(pos.x())
                    if "r" in h: new_r.setRight(pos.x())
                    if "t" in h: new_r.setTop(pos.y())
                    if "b" in h: new_r.setBottom(pos.y())
                    new_r = new_r.normalized()
                    if new_r.width() > 4 and new_r.height() > 4:
                        scaled = self._resize_cut_origin_pixmap.scaled(
                            new_r.width(), new_r.height(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                        self._cut_pixmap = scaled
                        self._cut_rect = QRect(new_r.topLeft(), scaled.size())
                        self._cut_pos = new_r.topLeft()
                        if self.cut_op != "copy":
                            self._selection_rect = QRect(self._cut_rect)
                    self.update()
                elif self._dragging_cut:
                    new_tl = pos - self._drag_offset
                    self._cut_rect = QRect(new_tl, self._cut_pixmap.size())
                    self._cut_pos = new_tl
                    # cut mode: keep _selection_rect in sync so commit erases correct area
                    # copy mode: _selection_rect stays at origin
                    if self.cut_op != "copy":
                        self._selection_rect = QRect(self._cut_rect)
                    self.update()
                elif self.cut_mode == "lasso" and self._lasso_pts:
                    last = self._lasso_pts[-1]
                    lx, ly = last
                    cx, cy = pos.x(), pos.y()
                    start = self._lasso_pts[0]
                    close_dist = math.hypot(cx - start[0], cy - start[1])
                    if len(self._lasso_pts) > 10 and close_dist <= max(8, 8 / self._zoom):
                        self._lasso_pts.append(start)
                        self._lasso_freeform_select()
                    else:
                        dist = math.hypot(cx - lx, cy - ly)
                        steps = max(1, int(dist))
                        for i in range(1, steps + 1):
                            ix = int(lx + (cx - lx) * i / steps)
                            iy = int(ly + (cy - ly) * i / steps)
                            self._lasso_pts.append((ix, iy))
                        self.update()
                elif self._start_pos is not None:
                    self._drag_end_pos = pos
                    self.update()
                    if hasattr(self, 'main_window'):
                        self.main_window._update_sel_dim(self._start_pos, pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._panning = False
            self.unsetCursor()
            return
        if event.button() in (Qt.LeftButton, Qt.RightButton) and self.tool == "spray":
            self._spray_timer.stop()
            if hasattr(self, "main_window") and self._spray_pts:
                is_left = (event.button() == Qt.LeftButton)
                sc = self.pen_color.name() if is_left else self.pen_color2.name()
                pts = [(p.x(), p.y()) for p in self._spray_pts]
                r = self.spray_radius if is_left else self.spray_radius2
                d = self.spray_density if is_left else self.spray_density2
                self.main_window.recorder.record(
                    f"canvas.spray({pts!r}, radius={r}, density={d}, color=__{sc}__)")
            self._spray_pts = []
            self._spray_pos = None
            return
        if event.button() == Qt.LeftButton and self.tool == "pencil" and len(self._stroke_pts) > 2:
            if self.pencil_bezier:
                self._apply_stroke_smoothing(75, self._stroke_pts, self.pen_color, self.pen_width)
            elif self._pencil_line_smooth > 0:
                self._apply_stroke_smoothing(self._pencil_line_smooth, self._stroke_pts, self.pen_color, self.pen_width)
            if hasattr(self, "main_window"):
                pc = self.pen_color.name()
                pts = [(p.x(), p.y()) for p in self._stroke_pts]
                _pt = self.pen_type1
                _pi = self.pen_intensity1
                self.main_window.recorder.record(
                    f"canvas.draw_stroke({pts!r}, width={self.pen_width}, color=__{pc}__, pen_type={_pt!r}, intensity={_pi})")
            self._stroke_pts = []
        if event.button() == Qt.RightButton and self.tool == "pencil" and len(self._stroke_pts2) > 2:
            if self.pencil_bezier2:
                self._apply_stroke_smoothing(75, self._stroke_pts2, self.pen_color2, self.pen_width2)
            if hasattr(self, "main_window"):
                pc = self.pen_color2.name()
                pts = [(p.x(), p.y()) for p in self._stroke_pts2]
                _pt = self.pen_type2
                _pi = self.pen_intensity2
                self.main_window.recorder.record(
                    f"canvas.draw_stroke({pts!r}, width={self.pen_width2}, color=__{pc}__, pen_type={_pt!r}, intensity={_pi})")
            self._stroke_pts2 = []
        if event.button() == Qt.LeftButton and self._resize_handle:
            self._resize_handle = None
            self._resize_origin_rect = None
            return
        if event.button() == Qt.LeftButton and self._resizing_cut:
            self._resizing_cut = False
            self._resize_cut_handle = None
            self._resize_cut_origin_rect = None
            self._resize_cut_origin_pixmap = None
            return
        if event.button() == Qt.RightButton:
            if self.tool in ("cut", "eraser"):
                if self.tool == "cut" and hasattr(self, "main_window"):
                    self.main_window.recorder.cancel_last_selection()
                self._cancel_cut()
                return
            if self.tool == "forms" and self._start_pos is not None:
                self._preview_image = None
                self._start_pos = None
                self._last_pos = None
                if hasattr(self, 'main_window'):
                    self.main_window._form_dim_label.setText("")
                self.update()
                return
        if event.button() == Qt.LeftButton:
            pos = self._to_canvas_pos(event.pos())
            if self.tool == "forms":
                if self._start_pos is not None:
                    pos = self._snap_to_grid(pos, is_end=True)
                    self._push_undo()
                    for img in ([self.image, self._color_image] if self._color_image else [self.image]):
                        p = QPainter(img)
                        self._draw_form(p, self._start_pos, pos)
                        p.end()
                    if self._color_image:
                        self._sync_gray()
                    self._preview_image = None
                    self._mod()
                    self.update()
                    if hasattr(self, "main_window"):
                        sp, ep = self._start_pos, pos
                        pc = self.pen_color.name(); fc = self.form_fill_color.name()
                        if self.form_mode == "circle":
                            import math as _m
                            _r = int(_m.hypot(ep.x()-sp.x(), ep.y()-sp.y()))
                            _pos2 = str(_r)
                        else:
                            _pos2 = f"({ep.x()},{ep.y()})"
                        _extra = ""
                        if self.form_mode == "star":
                            _extra = f", corners={self.star_corners}"
                        elif self.form_mode == "ngon":
                            _extra = f", edges={self.ngon_edges}"
                        self.main_window.recorder.record(
                            f"canvas.draw_form({self.form_mode!r}, ({sp.x()},{sp.y()}), {_pos2}, "
                            f"width={self.pen_width}, color=__{pc}__, fill_color=__{fc}__, "
                            f"transparent={self.form_fill_transparent}, antialias={self.form_antialias}{_extra})")
                self._start_pos = None
                self._last_pos = None
                if hasattr(self, 'main_window'):
                    self.main_window._form_dim_label.setText("")
            elif self.tool == "cut":
                if self._dragging_cut:
                    self._dragging_cut = False
                    self.update()
                elif self._lasso_pending_blink:
                    self._lasso_pending_blink = False
                    self._blink_timer.start(500)
                elif self._start_pos is not None:
                    rect = self._sel_rubber_rect(self._start_pos, self._drag_end_pos) if self._drag_end_pos else QRect()
                    if rect.width() > 2 and rect.height() > 2:
                        self._selection_rect = rect
                        if self.cut_op != "select":
                            self._push_undo()
                            self._cut_rect = rect
                            self._cut_pos = rect.topLeft()
                            self._cut_pixmap = QPixmap.fromImage(self.image.copy(rect))
                            self._cut_pixmap_base = self._cut_pixmap
                            if self.cut_mode in ("circle", "ellipse"):
                                mask = QPixmap(rect.size())
                                mask.fill(Qt.transparent)
                                mp = QPainter(mask)
                                mp.setRenderHint(QPainter.Antialiasing)
                                mp.setBrush(Qt.black)
                                mp.setPen(Qt.NoPen)
                                mp.drawEllipse(mask.rect())
                                mp.end()
                                self._cut_pixmap.setMask(mask.createMaskFromColor(Qt.transparent))
                            elif self.cut_mode == "wand" and self._wand_mask_img:
                                mask_pix = QPixmap.fromImage(self._wand_mask_img)
                                self._cut_pixmap.setMask(mask_pix.createMaskFromColor(Qt.transparent))
                            if self.cut_op == "copy":
                                self._copy_source_pixmap = self._cut_pixmap.copy()
                            else:
                                self._copy_source_pixmap = None
                            if self.cut_op == "cut":
                                for img in ([self.image, self._color_image] if self._color_image else [self.image]):
                                    p = QPainter(img)
                                    if self.cut_mode in ("circle", "ellipse"):
                                        p.setBrush(self.bg_color)
                                        p.setPen(Qt.NoPen)
                                        p.drawEllipse(rect)
                                    else:
                                        p.fillRect(rect, self.bg_color)
                                    p.end()
                                if self._color_image:
                                    self._sync_gray()
                            self._mod()
                        self._march_timer.start(100)
                        if self.cut_op != "select":
                            self._blink_timer.start(500)
                        self.update()
                        if hasattr(self, "main_window") and self.cut_op == "select":
                            self.main_window.recorder.record(
                                f"canvas.set_selection({self.cut_mode!r}, {rect.x()}, {rect.y()}, {rect.width()}, {rect.height()})")
                    self._start_pos = None
                    self._drag_end_pos = None
                    if hasattr(self, 'main_window'):
                        self.main_window._cut_dim_label.setText("")

    def _apply_stroke_smoothing(self, pct, pts=None, color=None, width=None):
        if pts is None: pts = self._stroke_pts
        if color is None: color = self.pen_color
        if width is None: width = self.pen_width
        if len(pts) < 3:
            return
        coords = [(p.x(), p.y()) for p in pts]
        passes = max(1, int(pct / 100.0 * 4))
        for _ in range(passes):
            new_coords = [coords[0]]
            for i in range(len(coords) - 1):
                x0, y0 = coords[i]
                x1, y1 = coords[i + 1]
                new_coords.append((x0 * 0.75 + x1 * 0.25, y0 * 0.75 + y1 * 0.25))
                new_coords.append((x0 * 0.25 + x1 * 0.75, y0 * 0.25 + y1 * 0.75))
            new_coords.append(coords[-1])
            coords = new_coords
        targets = [self.image, self._color_image] if self._color_image else [self.image]
        for img in targets:
            p = QPainter(img)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            for i in range(1, len(coords)):
                p.drawLine(QPointF(*coords[i-1]), QPointF(*coords[i]))
            p.end()
        if self._color_image:
            self._sync_gray()
        self._mod()
        self.update()

    def _flip_cut(self, horizontal):
        if self._cut_pixmap:
            self._cut_pixmap = self._cut_pixmap.transformed(
                QTransform().scale(-1 if horizontal else 1, 1 if horizontal else -1)
            )
            self._cut_pixmap_base = self._cut_pixmap
            self._cut_rect = QRect(self._cut_pos, self._cut_pixmap.size())
            self.update()

    def _rotate_cut(self, angle):
        if self._cut_pixmap_base:
            self._cut_pixmap = self._cut_pixmap_base.transformed(
                QTransform().rotate(angle), Qt.SmoothTransformation
            )
            self._cut_rect = QRect(self._cut_pos, self._cut_pixmap.size())
            self.update()

    def _commit_cut(self):
        if self._cut_pixmap:
            if self.cut_op == "cut":
                lasso = self._lasso_pts
                orig_pos = self._cut_rect.topLeft() if self._cut_rect else self._cut_pos
                for img in ([self.image, self._color_image] if self._color_image else [self.image]):
                    p = QPainter(img)
                    p.setBrush(self.bg_color)
                    p.setPen(Qt.NoPen)
                    if lasso and not self._dragging_cut:
                        p.drawPolygon(QPolygon([QPoint(pt[0], pt[1]) for pt in lasso]))
                    elif self.cut_mode in ("circle", "ellipse"):
                        p.drawEllipse(QRect(orig_pos, self._cut_pixmap.size()))
                    elif self.cut_mode == "wand" and self._wand_mask_img:
                        ox, oy = orig_pos.x(), orig_pos.y()
                        for wy in range(self._wand_mask_img.height()):
                            for wx in range(self._wand_mask_img.width()):
                                if self._wand_mask_img.pixel(wx, wy) & 0xFF000000:
                                    p.fillRect(ox + wx, oy + wy, 1, 1, self.bg_color)
                    elif self.cut_mode != "lasso":
                        p.fillRect(QRect(orig_pos, self._cut_pixmap.size()), self.bg_color)
                    p.end()
                if self._color_image:
                    self._sync_gray()
            for img in ([self.image, self._color_image] if self._color_image else [self.image]):
                p = QPainter(img)
                p.drawPixmap(self._cut_pos, self._cut_pixmap)
                p.end()
            if self._color_image:
                self._sync_gray()
            self._mod()
            self._cut_pixmap = None
            self._cut_pixmap_base = None
            self._cut_rect = None
            self._drag_end_pos = None
            self._lasso_pts = []
            self._blink_phase = False
            self._dragging_cut = False
            if self.cut_op == "copy" and self._selection_rect:
                pass  # keep _copy_lasso_pts, _wand_path and timers alive for origin outline
            else:
                self._selection_rect = None
                self._copy_lasso_pts = []
                self._wand_path = None
                self._march_timer.stop()
                self._blink_timer.stop()
            self.update()

    def _flatten_selection(self):
        """Commit floating pixmap back to image but keep _selection_rect for clipping."""
        if self._cut_pixmap:
            for img in ([self.image, self._color_image] if self._color_image else [self.image]):
                p = QPainter(img)
                p.drawPixmap(self._cut_pos, self._cut_pixmap)
                p.end()
            if self._color_image:
                self._sync_gray()
            self._cut_pixmap = None
            self._cut_pixmap_base = None
            self._cut_rect = None
            self._drag_end_pos = None
            self._wand_path = None
            self._lasso_pts = []
            self._blink_phase = False
            self.update()
        # keep _copy_lasso_pts alive so fill/eraser/spray can clip to lasso shape
        if self._selection_rect and not self._march_timer.isActive():
            self._march_timer.start(100)
            self._blink_timer.start(500)

    def _flood_fill(self, pos, new_color, clip_rect=None, tolerance=None):
        x, y = pos.x(), pos.y()
        if not (0 <= x < self.image.width() and 0 <= y < self.image.height()):
            return
        if clip_rect:
            if not clip_rect.contains(pos):
                return
            if self.cut_mode == "lasso" and self._copy_lasso_pts:
                from PyQt5.QtGui import QPolygonF
                poly = QPolygonF([QPointF(p[0], p[1]) for p in self._copy_lasso_pts])
                if not poly.containsPoint(QPointF(x, y), Qt.OddEvenFill):
                    return
                def in_clip(px, py):
                    return poly.containsPoint(QPointF(px, py), Qt.OddEvenFill)
            elif self.cut_mode in ("circle", "ellipse"):
                cx = clip_rect.x() + clip_rect.width() / 2
                cy = clip_rect.y() + clip_rect.height() / 2
                rx, ry = clip_rect.width() / 2, clip_rect.height() / 2
                def in_clip(px, py):
                    return ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 <= 1.0
            else:
                x1, y1, x2, y2 = clip_rect.left(), clip_rect.top(), clip_rect.right(), clip_rect.bottom()
                def in_clip(px, py):
                    return x1 <= px <= x2 and y1 <= py <= y2
        else:
            w, h = self.image.width(), self.image.height()
            def in_clip(px, py):
                return 0 <= px < w and 0 <= py < h
        target = self.image.pixel(x, y)
        fill = new_color.rgb()
        tol = self.fill_tolerance if tolerance is None else tolerance
        if target == fill and tol == 0:
            return
        if tol > 0:
            tc = QColor(target)
            def _match(px, py):
                c = QColor(self.image.pixel(px, py))
                return (abs(c.red()-tc.red()) + abs(c.green()-tc.green()) + abs(c.blue()-tc.blue())) <= tol * 3
        else:
            def _match(px, py): return self.image.pixel(px, py) == target
        stack = [(x, y)]
        iw, ih = self.image.width(), self.image.height()
        visited = set()
        while stack:
            cx2, cy2 = stack.pop()
            if (cx2, cy2) in visited:
                continue
            if not (0 <= cx2 < iw and 0 <= cy2 < ih):
                continue
            if not in_clip(cx2, cy2):
                continue
            if not _match(cx2, cy2):
                continue
            visited.add((cx2, cy2))
            self.image.setPixel(cx2, cy2, fill)
            if self._color_image:
                self._color_image.setPixel(cx2, cy2, fill)
            stack += [(cx2+1, cy2), (cx2-1, cy2), (cx2, cy2+1), (cx2, cy2-1)]
        if self._color_image:
            self._sync_gray()


def _build_palette(bit_depth):
    if bit_depth == 1:
        return [QColor(0, 0, 0), QColor(255, 255, 255)]
    elif bit_depth == 2:
        return [QColor(v, v, v) for v in [0, 85, 170, 255]]
    elif bit_depth == 4:
        return [QColor(v, v, v) for v in [round(i * 255 / 15) for i in range(16)]]
    elif bit_depth == 8:
        colors = []
        for r in range(8):
            for g in range(8):
                for b in range(4):
                    colors.append(QColor(round(r*255/7), round(g*255/7), round(b*255/3)))
        return colors
    elif bit_depth == 16:
        return None  # too many colors for swatches, use full color dialog
    return None  # 24-bit: use full color dialog


class PaletteDialog(QDialog):
    def __init__(self, colors, current, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pick Color")
        self.selected = current

        outer = QVBoxLayout(self)
        outer.setSpacing(4)
        outer.setContentsMargins(4, 4, 4, 4)

        self._rgb_label = QLabel()
        self._rgb_label.setFixedWidth(160)
        self._set_rgb(current)
        outer.addWidget(self._rgb_label)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(2)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        cols = 16 if len(colors) > 16 else len(colors)
        for i, color in enumerate(colors):
            btn = QPushButton()
            btn.setFixedSize(20, 20)
            btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #555;")
            btn.clicked.connect(lambda _, c=color: self._pick(c))
            btn.enterEvent = lambda _, c=color: self._set_rgb(c)
            grid.addWidget(btn, i // cols, i % cols)
        outer.addWidget(grid_widget)

    def _set_rgb(self, color):
        self._rgb_label.setText(f"RGB: {color.red():3d}, {color.green():3d}, {color.blue():3d}")

    def _pick(self, color):
        self.selected = color
        self._set_rgb(color)
        self.accept()


class _SliderDialog(QDialog):
    """Base dialog with one or more named sliders and Apply/OK/Cancel."""
    def __init__(self, title, sliders, apply_cb, parent=None):
        # sliders: list of (label, min, max, initial)
        super().__init__(parent)
        self.setWindowTitle(title)
        self._apply_cb = apply_cb
        layout = QVBoxLayout(self)
        self._sliders = []
        for lbl, lo, hi, val in sliders:
            row = QHBoxLayout()
            row.addWidget(QLabel(lbl))
            s = QSlider(Qt.Horizontal)
            s.setRange(lo, hi)
            s.setValue(val)
            s.setTickInterval((hi - lo) // 4)
            s.setTickPosition(QSlider.TicksBelow)
            vl = QLabel(f"{val:+d}")
            vl.setFixedWidth(36)
            vl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            s.valueChanged.connect(lambda v, l=vl: l.setText(f"{v:+d}"))
            row.addWidget(s)
            row.addWidget(vl)
            layout.addLayout(row)
            self._sliders.append(s)
        self._committed = [s.value() for s in self._sliders]
        btns = QDialogButtonBox()
        self._apply_btn  = btns.addButton("Apply", QDialogButtonBox.ApplyRole)
        self._ok_btn     = btns.addButton(QDialogButtonBox.Ok)
        self._cancel_btn = btns.addButton(QDialogButtonBox.Cancel)
        self._apply_btn.clicked.connect(self._on_apply)
        self._ok_btn.clicked.connect(self._on_ok)
        self._cancel_btn.clicked.connect(self.reject)
        layout.addWidget(btns)

    def _values(self):
        return [s.value() for s in self._sliders]

    def _on_apply(self):
        self._apply_cb(*self._values())
        self._committed = self._values()

    def _on_ok(self):
        self._apply_cb(*self._values())
        self._committed = self._values()
        self.accept()

    def committed(self):
        return self._committed


class _ColorFadeDialog(QDialog):
    def __init__(self, apply_cb, pick_color_fn, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Color Fade")
        self._apply_cb = apply_cb
        self._pick_color_fn = pick_color_fn
        layout = QFormLayout(self)
        self._color_a = QColor(Qt.black)
        self._color_b = QColor(Qt.white)
        self._btn_a = QPushButton()
        self._btn_a.setFixedSize(40, 20)
        self._btn_a.clicked.connect(self._pick_a)
        self._btn_b = QPushButton()
        self._btn_b.setFixedSize(40, 20)
        self._btn_b.clicked.connect(self._pick_b)
        self._set_btn(self._btn_a, self._color_a)
        self._set_btn(self._btn_b, self._color_b)
        layout.addRow("Start color:", self._btn_a)
        layout.addRow("End color:",   self._btn_b)
        self._orient_cb = QComboBox()
        self._orient_cb.addItems(["Top → Bottom", "Bottom → Top", "Left → Right", "Right → Left", "Center → Border", "Border → Center", "Top-Left → Bottom-Right", "Bottom-Right → Top-Left", "Bottom-Left → Top-Right", "Top-Right → Bottom-Left"])
        layout.addRow("Direction:", self._orient_cb)
        btns = QDialogButtonBox()
        self._apply_btn  = btns.addButton("Apply", QDialogButtonBox.ApplyRole)
        self._ok_btn     = btns.addButton(QDialogButtonBox.Ok)
        self._cancel_btn = btns.addButton(QDialogButtonBox.Cancel)
        self._apply_btn.clicked.connect(self._on_apply)
        self._ok_btn.clicked.connect(self._on_ok)
        self._cancel_btn.clicked.connect(self.reject)
        layout.addRow(btns)
        self._committed = None

    def _set_btn(self, btn, color):
        btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")

    def _pick_a(self):
        c = self._pick_color_fn(self._color_a)
        if c:
            self._color_a = c
            self._set_btn(self._btn_a, c)

    def _pick_b(self):
        c = self._pick_color_fn(self._color_b)
        if c:
            self._color_b = c
            self._set_btn(self._btn_b, c)

    def _values(self):
        return self._color_a, self._color_b, self._orient_cb.currentIndex()

    def _on_apply(self):
        self._apply_cb(*self._values())
        self._committed = self._values()

    def _on_ok(self):
        self._apply_cb(*self._values())
        self._committed = self._values()
        self.accept()

    def committed(self):
        return self._committed


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        import os as _os
        if getattr(sys, 'frozen', False):
            _ico = _os.path.join(sys._MEIPASS, 'simpledraw.ico')
        else:
            _ico = _os.path.join(_app_dir(), 'simpledraw.ico')
        if _os.path.exists(_ico):
            self.setWindowIcon(QIcon(_ico))
        self.current_file = "new_picture.bmp"
        self._modified = False
        self.bit_depth = 32
        self._last_bc_value     = (0, 0)
        self._last_sat_value    = 0
        self._last_noise_value  = 0
        self._last_pix_value    = 2
        self._last_smooth_value = 1
        self._last_posterize_value = 4
        self._last_vignette_value  = 100
        self._effect_origin_image = None
        self._effect_origin_cut   = None
        self._effect_origin_color = None
        self._effect_dialog_open  = False
        self._recent_files = []
        self._autosave_interval = 0  # 0 = disabled
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._autosave)
        self.canvas = Canvas()
        self.setCentralWidget(self.canvas)
        self.canvas.main_window = self
        self._build_menu()
        self._build_quickbar()
        self._update_undo_redo_state()
        self.recorder = MacroRecorder()
        self._build_toolbar()
        self._build_optionbar()
        self._build_statusbar()
        self.canvas._picked_color.connect(self._on_color_picked)
        self.canvas._picked_color2.connect(self._on_color_picked2)
        self.canvas.modified.connect(self._mark_modified)
        self._update_title()
        self.resize(900, 700)
        self._load_settings()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self._open_path(path)
                break

    def _open_path(self, path):
        if not self._ask_save_if_needed():
            return
        img = QImage(path)
        if not img.isNull():
            self.canvas._cancel_cut()
            self.canvas._emit_modified = False
            self.canvas.image = img.convertToFormat(QImage.Format_ARGB32)
            self._fit_canvas()
            self.canvas.update()
            self.canvas._emit_modified = True
            self.current_file = path
            self._modified = False
            self._update_title()
            self._update_size_label()
            self._add_recent(path)

    def showEvent(self, event):
        super().showEvent(event)
        self._fit_canvas()
        self.canvas.update()

    def _add_recent(self, path):
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._recent_files.insert(0, path)
        self._recent_files = self._recent_files[:10]
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self):
        self._recent_menu.clear()
        for path in self._recent_files:
            import os
            a = QAction(os.path.basename(path), self)
            a.setData(path)
            a.triggered.connect(lambda _, p=path: self._open_recent(p))
            self._recent_menu.addAction(a)
        self._recent_menu.setEnabled(bool(self._recent_files))

    def _open_recent(self, path):
        if not self._ask_save_if_needed():
            return
        img = QImage(path)
        if not img.isNull():
            self._open_path(path)

    def _update_title(self):
        import os
        name = os.path.basename(self.current_file)
        self.setWindowTitle(f"SimpleDraw - {name} *" if self._modified else f"SimpleDraw - {name}")

    def _update_undo_redo_state(self):
        if hasattr(self, "_undo_action"):
            n = len(self.canvas._undo_stack)
            self._undo_action.setEnabled(bool(n))
            self._undo_action.setToolTip(f"Undo ({n})" if n else "Undo")
        if hasattr(self, "_redo_action"):
            n = len(self.canvas._redo_stack)
            self._redo_action.setEnabled(bool(n))
            self._redo_action.setToolTip(f"Redo ({n})" if n else "Redo")

    def _mark_modified(self):
        if not self._modified:
            self._modified = True
            self._update_title()
        if not self._effect_dialog_open:
            self._effect_origin_image = None
            self._effect_origin_cut   = None
            self._effect_origin_color = None

    def _ask_save_if_needed(self):
        if not self._modified:
            return True
        import os
        name = os.path.basename(self.current_file)
        r = QMessageBox.question(self, "Unsaved Changes",
            f"{name} has unsaved changes. Save now?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if r == QMessageBox.Yes:
            return self._save_file()
        return r != QMessageBox.Cancel

    def _build_statusbar(self):
        sb = self.statusBar()
        self._pos_label = QLabel("X: 0  Y: 0")
        self._pos_label.setFixedWidth(110)
        self._size_label = QLabel()
        self._zoom_label = QLabel("100%")
        self._update_size_label()
        sb.addWidget(self._pos_label)
        sb.addWidget(self._color_history_widget)
        sb.addPermanentWidget(self._zoom_label)
        sb.addPermanentWidget(self._size_label)
        self.canvas.mouse_moved.connect(self._on_canvas_mouse_moved)
        self.canvas.wheelEvent = self._canvas_wheel_event

    def _canvas_wheel_event(self, event):
        cx = self.canvas.width() / 2
        cy = self.canvas.height() / 2
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        mx, my = event.pos().x(), event.pos().y()
        self._apply_zoom(factor, mx, my)

    def _apply_zoom(self, factor, cx=None, cy=None):
        new_zoom = max(self.canvas._zoom_base * 0.1, min(self.canvas._zoom_base * 32.0, self.canvas._zoom * factor))
        if cx is None:
            cx = self.canvas.width() / 2
        if cy is None:
            cy = self.canvas.height() / 2
        self.canvas._offset = QPoint(
            int(cx - (cx - self.canvas._offset.x()) * new_zoom / self.canvas._zoom),
            int(cy - (cy - self.canvas._offset.y()) * new_zoom / self.canvas._zoom)
        )
        self.canvas._zoom = new_zoom
        pct = int(new_zoom / self.canvas._zoom_base * 100)
        self._zoom_label.setText(f"{pct}%")
        self.canvas.update()

    def _zoom_reset(self):
        self._fit_canvas()
        self.canvas.update()

    def _fit_canvas(self):
        iw, ih = self.canvas.image.width(), self.canvas.image.height()
        cw, ch = self.canvas.width(), self.canvas.height()
        self.canvas._zoom_base = min(cw / iw, ch / ih) if iw and ih else 1.0
        self.canvas._zoom = self.canvas._zoom_base
        self._zoom_label.setText("100%")
        self._center_canvas()

    def _center_canvas(self):
        iw = int(self.canvas.image.width() * self.canvas._zoom)
        ih = int(self.canvas.image.height() * self.canvas._zoom)
        ox = max((self.canvas.width() - iw) // 2, 0)
        oy = max((self.canvas.height() - ih) // 2, 0)
        self.canvas._offset = QPoint(ox, oy)

    def _update_size_label(self):
        w, h = self.canvas.image.width(), self.canvas.image.height()
        self._size_label.setText(f"{w} x {h} px")

    def _on_canvas_mouse_moved(self, x, y):
        self._pos_label.setText(f"X: {x}  Y: {y}")

    def _si(self, sp):
        return self.style().standardIcon(sp)

    def _emoji_icon(self, emoji, size=16):
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setFont(QFont("Segoe UI Emoji", size - 4))
        p.drawText(pix.rect(), Qt.AlignCenter, emoji)
        p.end()
        return QIcon(pix)

    def _drawn_icon(self, fn, size=16):
        """Icon from a painter callback fn(QPainter, size)."""
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        fn(p, size)
        p.end()
        return QIcon(pix)

    def _printer_icon(self, size=16):
        def draw(p, s):
            m = s // 8
            # paper tray top
            p.setPen(QPen(QColor(60, 60, 60), 1))
            p.setBrush(QColor(220, 220, 220))
            p.drawRect(m + 2, m, s - 2*m - 4, s // 4)
            # printer body
            p.setBrush(QColor(100, 100, 100))
            p.drawRoundedRect(m, s // 4, s - 2*m, s // 2, 2, 2)
            # output paper
            p.setBrush(QColor(240, 240, 240))
            p.drawRect(m + 2, s // 4 + s // 4, s - 2*m - 4, s // 4)
            # button dot
            p.setBrush(QColor(80, 180, 80))
            p.setPen(Qt.NoPen)
            p.drawEllipse(s - m - 4, s // 4 + 3, 3, 3)
        return self._drawn_icon(draw, size)

    def _save_as_icon(self, size=16):
        base = self._si(__import__('PyQt5.QtWidgets', fromlist=['QStyle']).QStyle.SP_DialogSaveButton).pixmap(size, size)
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.drawPixmap(0, 0, base)
        # green "+" badge bottom-right
        p.setPen(QPen(QColor(0, 160, 0), 2.0, Qt.SolidLine, Qt.RoundCap))
        cx, cy = size - 3, size - 3
        p.drawLine(cx - 2, cy, cx + 2, cy)
        p.drawLine(cx, cy - 2, cx, cy + 2)
        p.end()
        return QIcon(pix)

    def _zoom_reset_icon(self, size=16):
        def draw(p, s):
            # magnifying glass circle
            r = s // 2 - 2
            cx, cy = s // 2 - 1, s // 2 - 1
            p.setPen(QPen(QColor(60, 60, 60), 1.5))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
            # handle
            p.setPen(QPen(QColor(60, 60, 60), 2.0, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(cx + r - 1, cy + r - 1, s - 2, s - 2)
            # "1:1" bar inside lens
            p.setPen(QPen(QColor(60, 60, 60), 1.2))
            p.drawLine(cx - 2, cy, cx + 2, cy)
        return self._drawn_icon(draw, size)

    def _record_icon(self, size=16, recording=False):
        def draw(p, s):
            p.setRenderHint(QPainter.Antialiasing)
            color = QColor(200, 0, 0) if recording else QColor(160, 160, 160)
            p.setBrush(color)
            p.setPen(Qt.NoPen)
            p.drawEllipse(2, 2, s - 4, s - 4)
        return self._drawn_icon(draw, size)

    def _toggle_record(self):
        if self.recorder.active:
            self.recorder.stop()
            self._record_action.setIcon(self._record_icon(self.qb_icon_size))
            self._record_action.setToolTip("Record")
            import os, time
            scripts_dir = os.path.join(_app_dir(), "scripts")
            os.makedirs(scripts_dir, exist_ok=True)
            name = f"recorded_{time.strftime('%Y%m%d_%H%M%S')}.py"
            path = os.path.join(scripts_dir, name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.recorder.script())
            if hasattr(self, "_script_window") and self._script_window.isVisible():
                self._script_window._refresh()
        else:
            img = self.canvas.image
            bg = self.canvas.bg_color
            self.recorder.start(img.width(), img.height(), (bg.red(), bg.green(), bg.blue()))
            self._record_action.setIcon(self._record_icon(self.qb_icon_size, recording=True))
            self._record_action.setToolTip("Stop Recording")

    def _scripts_icon(self, size=16):
        def draw(p, s):
            p.setPen(QPen(QColor(40, 40, 180), 1.5))
            p.setBrush(Qt.NoBrush)
            # scroll/document outline
            p.drawRoundedRect(2, 1, s - 4, s - 2, 2, 2)
            # three lines representing code
            p.setPen(QPen(QColor(40, 40, 180), 1))
            for y in (5, 8, 11):
                p.drawLine(5, y, s - 5, y)
            # play triangle bottom-right
            p.setBrush(QColor(0, 160, 0))
            p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygon([QPoint(s - 6, s - 6), QPoint(s - 1, s - 3), QPoint(s - 6, s)]))
        return self._drawn_icon(draw, size)

    def _export_icon(self, size=16):
        def draw(p, s):
            m = s // 8
            # box (bottom portion)
            p.setPen(QPen(QColor(60, 60, 60), 1.2))
            p.setBrush(Qt.NoBrush)
            p.drawRect(m, s // 2, s - 2*m, s // 2 - m)
            # arrow shaft
            cx = s // 2
            p.setPen(QPen(QColor(60, 60, 60), 1.5, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(cx, s // 2 - 1, cx, m + 3)
            # arrowhead
            p.setBrush(QColor(60, 60, 60))
            p.setPen(Qt.NoPen)
            tip = QPolygon([QPoint(cx, m), QPoint(cx - 3, m + 4), QPoint(cx + 3, m + 4)])
            p.drawPolygon(tip)
        return self._drawn_icon(draw, size)

    def _forms_icon(self, size=16):
        def draw(p, s):
            m = 1
            p.setPen(QPen(QColor(60, 60, 60), 1.2))
            p.setBrush(Qt.NoBrush)
            p.drawRect(m, m + 3, s // 2 - 2, s - 2*m - 4)
            p.drawEllipse(s // 2 + 1, m, s // 2 - m - 1, s // 2 - m - 1)
            p.drawLine(s // 2 + 1, s // 2 + 2, s - m - 1, s - m - 1)
        return self._drawn_icon(draw, size)

    def _spray_icon(self, size=16):
        def draw(p, s):
            rng = random.Random(42)
            blue = QColor(30, 100, 220)
            for _ in range(18):
                x = rng.randint(1, s - 2)
                y = rng.randint(1, s - 2)
                p.setPen(Qt.NoPen)
                p.setBrush(blue)
                p.drawRect(x, y, 1, 1)
        return self._drawn_icon(draw, size)

    def _pipette_icon(self, size=16):
        def draw(p, s):
            p.setPen(QPen(QColor(60, 60, 60), 1.5, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(s - 3, 2, 3, s - 5)
            p.setPen(QPen(QColor(60, 60, 60), 1))
            p.setBrush(QColor(180, 80, 80))
            tip = QPolygon([QPoint(2, s - 4), QPoint(5, s - 2), QPoint(4, s - 6)])
            p.drawPolygon(tip)
            p.setBrush(QColor(160, 160, 200))
            p.setPen(QPen(QColor(60, 60, 60), 1))
            p.drawEllipse(s - 6, 1, 5, 5)
        return self._drawn_icon(draw, size)

    def _menu_action(self, menu, label, slot, shortcut=None, icon=None):
        a = QAction(label, self)
        if icon:
            a.setIcon(icon)
        if shortcut:
            a.setShortcut(shortcut)
        a.triggered.connect(slot)
        menu.addAction(a)
        return a

    def _build_menu(self):
        from PyQt5.QtWidgets import QStyle
        mb = self.menuBar()

        # File menu
        file_menu = mb.addMenu("File")
        self._menu_action(file_menu, "New File",  self._new_file,   "Ctrl+N", self._si(QStyle.SP_FileIcon))
        self._menu_action(file_menu, "Open",       self._open_file,  "Ctrl+O", self._si(QStyle.SP_DialogOpenButton))
        self._menu_action(file_menu, "Save",       self._save_file,  "Ctrl+S", self._si(QStyle.SP_DialogSaveButton))
        self._menu_action(file_menu, "Save As",    self._save_as,    None,     self._save_as_icon())
        file_menu.addSeparator()
        self._recent_menu = file_menu.addMenu("Recent Files")
        self._recent_menu.setEnabled(False)
        file_menu.addSeparator()
        self._menu_action(file_menu, "Print",      self._print_file, "Ctrl+P", self._printer_icon())
        export_menu = file_menu.addMenu("Export")
        export_menu.setIcon(self._export_icon())
        self._menu_action(export_menu, "Export Image",   self._export_file,    None, self._export_icon())
        self._menu_action(export_menu, "Export to Code", self._export_to_code, None, self._emoji_icon("</>"))
        file_menu.addSeparator()
        self._menu_action(file_menu, "Exit", self.close, "Ctrl+Q", self._si(QStyle.SP_DialogCloseButton))

        # Edit menu
        edit_menu = mb.addMenu("Edit")
        self._menu_action(edit_menu, "Undo", self.canvas.undo, "Ctrl+Z", self._si(QStyle.SP_ArrowBack))
        self._menu_action(edit_menu, "Redo", self.canvas.redo, "Ctrl+Y", self._si(QStyle.SP_ArrowForward))
        self._menu_action(edit_menu, "Paste from Clipboard", self._paste_from_clipboard, "Ctrl+V", self._emoji_icon("📋"))
        self._menu_action(edit_menu, "Copy to Clipboard",    self._copy_canvas_to_clipboard, "Ctrl+C", self._emoji_icon("📄"))
        self._menu_action(edit_menu, "Copy Selection", self._copy_selection_to_clipboard, "Ctrl+Shift+C", self._emoji_icon("⧉"))
        edit_menu.addSeparator()
        self._menu_action(edit_menu, "Flip Horizontal",       lambda: self.canvas.flip_canvas(True),  None, self._emoji_icon("⇔"))
        self._menu_action(edit_menu, "Flip Vertical",         lambda: self.canvas.flip_canvas(False), None, self._emoji_icon("⇕"))
        self._menu_action(edit_menu, "Rotate Clockwise",      lambda: (self.canvas.rotate_canvas(True),  self._update_size_label()), None, self._emoji_icon("↻"))
        self._menu_action(edit_menu, "Rotate Counter-Clockwise", lambda: (self.canvas.rotate_canvas(False), self._update_size_label()), None, self._emoji_icon("↺"))
        edit_menu.addSeparator()
        self._menu_action(edit_menu, "Size", self._edit_size, None, self._si(QStyle.SP_DesktopIcon))
        effects_menu = edit_menu.addMenu("Effects")
        effects_menu.setIcon(self._emoji_icon("✨"))
        self._menu_action(effects_menu, "Grayscale", self._toggle_grayscale, None, self._emoji_icon("◑"))

        self._menu_action(effects_menu, "Invert",    lambda: (self.canvas.apply_effect("Invert Colors"), self.recorder.record("canvas.apply_effect('invert')")), None, self._emoji_icon("🔄"))
        self._menu_action(effects_menu, "Smooth",    self._smooth_with_dialog, None, self._emoji_icon("💧"))
        self._menu_action(effects_menu, "Brightness/Contrast", lambda: self._effect_with_dialog(
            "Brightness/Contrast",
            [("Brightness", -100, 100, self._last_bc_value[0]),
             ("Contrast",   -100, 100, self._last_bc_value[1])],
            lambda b, c: self.canvas.apply_brightness_contrast(b, c),
            "_last_bc_value"
        ), None, self._emoji_icon("☀"))
        self._menu_action(effects_menu, "Saturation", lambda: self._effect_with_dialog(
            "Saturation",
            [("Saturation", -100, 100, self._last_sat_value)],
            lambda v: self.canvas.apply_saturation(v),
            "_last_sat_value"
        ), None, self._emoji_icon("🎨"))
        self._menu_action(effects_menu, "Noise", lambda: self._effect_with_dialog(
            "Noise",
            [("Amount", 0, 100, self._last_noise_value)],
            lambda v: self.canvas.apply_noise(v),
            "_last_noise_value"
        ), None, self._emoji_icon("🌫"))
        self._menu_action(effects_menu, "Pixelate", lambda: self._effect_with_dialog(
            "Pixelate",
            [("Block size", 2, 64, self._last_pix_value)],
            lambda v: self.canvas.apply_pixelate(v),
            "_last_pix_value"
        ), None, self._emoji_icon("🔲"))
        self._menu_action(effects_menu, "Color Fade", self._colorfade_with_dialog, None, self._emoji_icon("🌈"))
        self._menu_action(effects_menu, "Sharpen", lambda: (self.canvas.apply_sharpen(), self.recorder.record("canvas.apply_effect('sharpen')")), None, self._emoji_icon("🔪"))
        self._menu_action(effects_menu, "Posterize", lambda: self._effect_with_dialog(
            "Posterize",
            [("Levels", 2, 16, 4)],
            lambda v: self.canvas.apply_posterize(v),
            "_last_posterize_value"
        ), None, self._emoji_icon("🎭"))
        self._menu_action(effects_menu, "Emboss", lambda: (self.canvas.apply_emboss(), self.recorder.record("canvas.apply_effect('emboss')")), None, self._emoji_icon("🗿"))
        self._menu_action(effects_menu, "Vignette", lambda: self._effect_with_dialog(
            "Vignette",
            [("Strength", 0, 200, 100)],
            lambda v: self.canvas.apply_vignette(v),
            "_last_vignette_value"
        ), None, self._emoji_icon("🌑"))

        # View menu
        view_menu = mb.addMenu("View")
        self._grid_action = QAction(self._emoji_icon("⊞"), "Show Grid", self)
        self._grid_action.setCheckable(True)
        self._grid_action.triggered.connect(self._toggle_grid)
        view_menu.addAction(self._grid_action)
        self._menu_action(view_menu, "Grid Settings", self._grid_settings, None, self._emoji_icon("⊞"))

        # Info menu
        info_menu = mb.addMenu("Info")
        self._menu_action(info_menu, "Preferences", self._show_preferences,  None, self._emoji_icon("⚙"))
        self._menu_action(info_menu, "Help",        self._show_help,         None, self._emoji_icon("❓"))
        self._menu_action(info_menu, "About",       self._show_about,        None, self._emoji_icon("ℹ"))
        self._shortcut_actions = {
            "New File":        self._menu_action(QMenu(), "New File",  self._new_file,  "Ctrl+N"),
            "Open":            self._menu_action(QMenu(), "Open",      self._open_file, "Ctrl+O"),
            "Save":            self._menu_action(QMenu(), "Save",      self._save_file, "Ctrl+S"),
            "Print":           self._menu_action(QMenu(), "Print",     self._print_file,"Ctrl+P"),
            "Undo":            self._menu_action(QMenu(), "Undo",      self.canvas.undo,"Ctrl+Z"),
            "Redo":            self._menu_action(QMenu(), "Redo",      self.canvas.redo,"Ctrl+Y"),
            "Copy Canvas":     self._menu_action(QMenu(), "Copy",      self._copy_canvas_to_clipboard, "Ctrl+C"),
            "Paste":           self._menu_action(QMenu(), "Paste",     self._paste_from_clipboard,     "Ctrl+V"),
            "Copy Selection":  self._menu_action(QMenu(), "Copy Sel",  self._copy_selection_to_clipboard, "Ctrl+Shift+C"),
            "Exit":            self._menu_action(QMenu(), "Exit",      self.close,      "Ctrl+Q"),
        }
    def _apply_theme(self, mode):
        import qtmodern.styles
        self._theme = mode
        app = QApplication.instance()
        if mode == "dark":
            qtmodern.styles.dark(app)
        else:
            qtmodern.styles.light(app)

    def _show_preferences(self):
        from PyQt5.QtWidgets import QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QKeySequenceEdit
        from PyQt5.QtGui import QKeySequence
        dlg = QDialog(self)
        dlg.setWindowTitle("Preferences")
        dlg.setMinimumWidth(480)
        dlg.setMinimumHeight(360)
        outer = QVBoxLayout(dlg)

        tabs = QTabWidget()
        outer.addWidget(tabs)

        # --- Theme tab ---
        theme_widget = QWidget()
        theme_layout = QVBoxLayout(theme_widget)
        theme_layout.setAlignment(Qt.AlignTop)
        theme_layout.addWidget(QLabel("Application Theme:"))
        _tog = "QPushButton:checked{background:#3a6ea8;color:#fff;border:1px solid #5599dd;}"
        btn_row = QHBoxLayout()
        light_btn = QPushButton("☀  Light")
        light_btn.setCheckable(True)
        light_btn.setFixedHeight(28)
        light_btn.setStyleSheet(_tog)
        dark_btn = QPushButton("🌙  Dark")
        dark_btn.setCheckable(True)
        dark_btn.setFixedHeight(28)
        dark_btn.setStyleSheet(_tog)
        light_btn.setFixedWidth(light_btn.sizeHint().width())
        dark_btn.setFixedWidth(light_btn.sizeHint().width())
        current_theme = getattr(self, '_theme', 'light')
        light_btn.setChecked(current_theme == 'light')
        dark_btn.setChecked(current_theme == 'dark')
        def _pick_light():
            light_btn.setChecked(True)
            dark_btn.setChecked(False)
        def _pick_dark():
            dark_btn.setChecked(True)
            light_btn.setChecked(False)
        light_btn.clicked.connect(_pick_light)
        dark_btn.clicked.connect(_pick_dark)
        btn_row.addWidget(light_btn)
        btn_row.addWidget(dark_btn)
        btn_row.addStretch()
        theme_layout.addLayout(btn_row)
        tabs.addTab(theme_widget, "Theme")

        # --- Shortcuts tab ---
        sc_widget = QWidget()
        sc_layout = QVBoxLayout(sc_widget)
        sc_layout.addWidget(QLabel("Double-click a shortcut cell to edit. Press the key combination, then click Apply."))
        actions = getattr(self, '_shortcut_actions', {})
        table = QTableWidget(len(actions), 2)
        table.setHorizontalHeaderLabels(["Action", "Shortcut"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        sc_editors = {}  # row -> QKeySequenceEdit
        for row, (name, action) in enumerate(actions.items()):
            table.setItem(row, 0, QTableWidgetItem(name))
            kse = QKeySequenceEdit(action.shortcut())
            kse.setFixedHeight(24)
            table.setCellWidget(row, 1, kse)
            sc_editors[row] = (name, kse)
        sc_layout.addWidget(table)
        tabs.addTab(sc_widget, "Shortcuts")

        # --- Auto-save tab ---
        as_widget = QWidget()
        as_layout = QVBoxLayout(as_widget)
        as_layout.setAlignment(Qt.AlignTop)
        as_row = QHBoxLayout()
        as_row.addWidget(QLabel("Auto-save interval (minutes, 0 = disabled):"))
        as_spin = QSpinBox()
        as_spin.setRange(0, 60)
        as_spin.setValue(self._autosave_interval)
        as_spin.setFixedWidth(60)
        as_row.addWidget(as_spin)
        as_row.addStretch()
        as_layout.addLayout(as_row)
        as_layout.addWidget(QLabel("Auto-save writes to a file named '<original>_autosave.bmp'."))
        tabs.addTab(as_widget, "Auto-save")

        # --- Buttons ---
        btns = QDialogButtonBox()
        apply_btn  = btns.addButton("Apply",  QDialogButtonBox.ApplyRole)
        ok_btn     = btns.addButton(QDialogButtonBox.Ok)
        cancel_btn = btns.addButton(QDialogButtonBox.Cancel)
        outer.addWidget(btns)

        def _apply():
            theme = 'dark' if dark_btn.isChecked() else 'light'
            self._apply_theme(theme)
            for row, (name, kse) in sc_editors.items():
                actions[name].setShortcut(kse.keySequence())
            interval = as_spin.value()
            self._autosave_interval = interval
            if interval > 0:
                self._autosave_timer.start(interval * 60 * 1000)
            else:
                self._autosave_timer.stop()
            self._save_settings()

        apply_btn.clicked.connect(_apply)
        ok_btn.clicked.connect(lambda: (_apply(), dlg.accept()))
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec_()

    def _autosave(self):
        if not self._modified:
            return
        import os
        base, ext = os.path.splitext(self.current_file)
        path = base + '_autosave' + (ext or '.bmp')
        try:
            self.canvas.image.save(path)
        except Exception:
            pass

    def _show_help(self):
        import os, subprocess
        doc = os.path.join(_app_dir(), 'docs', 'index.html')
        if os.path.exists(doc):
            import webbrowser
            webbrowser.open(doc)
        else:
            QMessageBox.warning(self, "Help", f"Documentation not found:\n{doc}")

    def _show_about(self):
        import sys
        from PyQt5.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("About SimpleDraw")
        dlg.setMinimumWidth(380)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(6)
        for text, bold in [
            ("SimpleDraw", True),
            (f"Version {APP_VERSION}", False),
            ("", False),
            ("Runtime", True),
            (f"Python {sys.version.split()[0]}", False),
            (f"PyQt5 {PYQT_VERSION_STR}", False),
            (f"Qt {QT_VERSION_STR}", False),
            ("", False),
            ("Open Source Licenses", True),
            ("Qt is used under the GNU Lesser General Public License (LGPL) v3.", False),
            ("PyQt5 is used under the GNU General Public License (GPL) v3.", False),
            ("", False),
            ("Qt is a trademark of The Qt Company Ltd.", False),
            ("PyQt5 is developed by Riverbank Computing Limited.", False),
        ]:
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            if bold:
                f = lbl.font()
                f.setBold(True)
                lbl.setFont(f)
            layout.addWidget(lbl)
        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(dlg.accept)
        layout.addWidget(btns)
        dlg.exec_()

    def _build_quickbar(self):
        from PyQt5.QtWidgets import QStyle
        qb = QToolBar("Quick Access", self)
        qb.setMovable(False)
        self.addToolBar(qb)
        s = qb.iconSize().width()
        for icon, tip, slot in [
            (self._si(QStyle.SP_FileIcon),                "New File",   self._new_file),
            (self._si(QStyle.SP_DialogOpenButton),        "Open",       self._open_file),
            (self._si(QStyle.SP_DialogSaveButton),        "Save",       self._save_file),
            (self._save_as_icon(s),                       "Save As",    self._save_as),
            (self._printer_icon(s),                       "Print",      self._print_file),
            (self._export_icon(s),                        "Export",     self._export_file),
            (self._si(QStyle.SP_ArrowBack),               "Undo",       self.canvas.undo),
            (self._si(QStyle.SP_ArrowForward),            "Redo",       self.canvas.redo),
            (self._emoji_icon("🔍"),                      "Zoom In",    lambda: self._apply_zoom(1.25)),
            (self._emoji_icon("🔎"),                      "Zoom Out",   lambda: self._apply_zoom(1 / 1.25)),
            (self._zoom_reset_icon(s),                    "Reset Zoom", self._zoom_reset),
            (self._scripts_icon(s),                       "Scripts",    self._open_scripts),
        ]:
            a = QAction(icon, tip, self)
            a.setToolTip(tip)
            a.triggered.connect(slot)
            qb.addAction(a)
            if tip == "Undo": self._undo_action = a
            if tip == "Redo": self._redo_action = a
        self.qb_icon_size = s
        self._record_action = QAction(self._record_icon(s), "Record", self)
        self._record_action.setToolTip("Record")
        self._record_action.triggered.connect(self._toggle_record)
        qb.addAction(self._record_action)

    def _print_file(self):
        from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
        printer = QPrinter(QPrinter.HighResolution)
        def do_print(p):
            painter = QPainter(p)
            painter.drawImage(0, 0, self.canvas.image.scaled(
                p.pageRect().size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            painter.end()
        dlg = QPrintPreviewDialog(printer, self)
        dlg.paintRequested.connect(do_print)
        dlg.exec_()

    def _export_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export", "",
            "PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp);;TIFF (*.tiff);;WebP (*.webp)")
        if path:
            if not self.canvas.image.save(path):
                QMessageBox.warning(self, "Export Failed", f"Could not export to {path}")

    def _export_to_code(self):
        import os
        from PyQt5.QtWidgets import QRadioButton
        dlg = QDialog(self)
        dlg.setWindowTitle("Export to Code")
        layout = QVBoxLayout(dlg)
        rb_c = QRadioButton("C")
        rb_py = QRadioButton("Python")
        rb_c.setChecked(True)
        layout.addWidget(rb_c)
        layout.addWidget(rb_py)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        if not dlg.exec_():
            return
        use_c = rb_c.isChecked()
        ext = ".c" if use_c else ".py"
        base = os.path.splitext(self.current_file)[0]
        path, _ = QFileDialog.getSaveFileName(self, "Export to Code", base + ext,
            "C Source (*.c)" if use_c else "Python Source (*.py)")
        if not path:
            return
        bd = self.bit_depth
        img = self.canvas.image
        w, h = img.width(), img.height()
        arr_name = os.path.splitext(os.path.basename(path))[0]
        # collect pixel values per bit depth
        values = []
        if bd == 1:
            for y in range(h):
                byte, bit = 0, 7
                for x in range(w):
                    lum = QColor(img.pixel(x, y)).lightness()
                    if lum < 128:
                        byte |= (1 << bit)
                    bit -= 1
                    if bit < 0:
                        values.append(byte)
                        byte, bit = 0, 7
                if bit < 7:
                    values.append(byte)
        elif bd == 2:
            for y in range(h):
                byte, shift = 0, 6
                for x in range(w):
                    lum = QColor(img.pixel(x, y)).lightness()
                    v = min(lum * 3 // 255, 3)
                    byte |= (v << shift)
                    shift -= 2
                    if shift < 0:
                        values.append(byte)
                        byte, shift = 0, 6
                if shift < 6:
                    values.append(byte)
        elif bd == 4:
            for y in range(h):
                byte, hi = 0, True
                for x in range(w):
                    lum = QColor(img.pixel(x, y)).lightness()
                    v = min(lum * 15 // 255, 15)
                    if hi:
                        byte = v << 4
                    else:
                        byte |= v
                        values.append(byte)
                        byte = 0
                    hi = not hi
                if not hi:
                    values.append(byte)
        elif bd == 8:
            for y in range(h):
                for x in range(w):
                    lum = QColor(img.pixel(x, y)).lightness()
                    values.append(lum & 0xFF)
        elif bd == 16:
            for y in range(h):
                for x in range(w):
                    c = QColor(img.pixel(x, y))
                    v = ((c.red() >> 3) << 11) | ((c.green() >> 2) << 5) | (c.blue() >> 3)
                    values.append(v & 0xFFFF)
        elif bd == 24:
            for y in range(h):
                for x in range(w):
                    c = QColor(img.pixel(x, y))
                    values.append((c.red() << 16) | (c.green() << 8) | c.blue())
        else:  # 32
            for y in range(h):
                for x in range(w):
                    c = QColor(img.pixel(x, y))
                    values.append((c.alpha() << 24) | (c.red() << 16) | (c.green() << 8) | c.blue())
        if bd <= 8:
            dtype, fmt = "uint8_t", "0x{:02X}"
        elif bd == 16:
            dtype, fmt = "uint16_t", "0x{:04X}"
        elif bd == 24:
            dtype, fmt = "uint32_t", "0x{:06X}"
        else:
            dtype, fmt = "uint32_t", "0x{:08X}"
        if bd == 1:
            bytes_per_row = (w + 7) // 8
        elif bd == 2:
            bytes_per_row = (w + 3) // 4
        elif bd == 4:
            bytes_per_row = (w + 1) // 2
        else:
            bytes_per_row = w  # one element per pixel for 8/16/24/32
        chunks = [fmt.format(v) for v in values]
        rows = [', '.join(chunks[i:i+bytes_per_row]) for i in range(0, len(chunks), bytes_per_row)]
        data_str = ',\n    '.join(rows)
        if use_c:
            if bd == 24:
                typedef = (
                    f"typedef union _{arr_name}_pixel\n"
                    f"{{\n"
                    f"    struct\n"
                    f"    {{\n"
                    f"        uint8_t B;\n"
                    f"        uint8_t G;\n"
                    f"        uint8_t R;\n"
                    f"    }};\n"
                    f"    uint8_t raw[3];\n"
                    f"}} {arr_name}_pixel_t;\n\n"
                )
            elif bd == 32:
                typedef = (
                    f"typedef union _{arr_name}_pixel\n"
                    f"{{\n"
                    f"    struct\n"
                    f"    {{\n"
                    f"        uint8_t B;\n"
                    f"        uint8_t G;\n"
                    f"        uint8_t R;\n"
                    f"        uint8_t A;\n"
                    f"    }};\n"
                    f"    uint32_t raw;\n"
                    f"    uint8_t raw8[4];\n"
                    f"}} {arr_name}_pixel_t;\n\n"
                )
            else:
                typedef = ""
            code = (f"{typedef}"
                    f"#define {arr_name.upper()}_WIDTH       {w}\n"
                    f"#define {arr_name.upper()}_HEIGHT      {h}\n"
                    f"#define {arr_name.upper()}_ROW_BYTES   {bytes_per_row}\n\n"
                    f"const {dtype} {arr_name}[{arr_name.upper()}_HEIGHT][{arr_name.upper()}_ROW_BYTES] = {{\n"
                    f"    {data_str}\n}};\n")
        else:
            code = (f"# {w}x{h}, {bd}-bit\n"
                    f"{arr_name} = (\n"
                    f"    {data_str}\n)\n"
                    f"{arr_name}_width = {w}\n"
                    f"{arr_name}_height = {h}\n")
        try:
            with open(path, 'w') as f:
                f.write(code)
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", str(e))

    def _build_toolbar(self):
        self.addToolBarBreak()
        tb = QToolBar("Tools", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        def _tool_action(icon, label, tool, shortcut=None):
            a = QAction(icon, label, self)
            a.setToolTip(label)
            a.setCheckable(True)
            if shortcut:
                a.setShortcut(shortcut)
            a.triggered.connect(lambda: self._set_tool(tool))
            tb.addAction(a)
            return a

        pencil_action  = _tool_action(self._emoji_icon("🖌"),  "Pencil",    "pencil", "P")
        pencil_action.setChecked(True)
        spray_action   = _tool_action(self._spray_icon(),              "Spray",     "spray",  "S")
        forms_action   = _tool_action(self._forms_icon(),              "Forms",     "forms",  "F")
        fill_action    = _tool_action(self._emoji_icon("🪣"),   "Fill",      "fill",   "G")
        eraser_action  = _tool_action(self._emoji_icon("🧹"),   "Eraser",    "eraser", "E")
        cut_action     = _tool_action(self._emoji_icon("⬚"),       "Selection", "cut",    "C")
        text_action    = _tool_action(self._emoji_icon("𝐓"),   "Text",      "text",   "T")
        picker_action  = _tool_action(self._pipette_icon(),             "Picker",    "picker", "I")
        ruler_action   = _tool_action(self._emoji_icon("📏"),   "Ruler",     "ruler",  "R")
        tb.addSeparator()

        bg_action = QAction(self._emoji_icon("🖼"), "Background Color", self)
        bg_action.setToolTip("Background Color")
        bg_action.setShortcut("B")
        bg_action.triggered.connect(self._pick_bg_color)
        tb.addAction(bg_action)
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setFixedSize(20, 20)
        self.bg_color_btn.clicked.connect(self._pick_bg_color)
        self._set_color_btn(self.bg_color_btn, self.canvas.bg_color)
        tb.addWidget(self.bg_color_btn)

        tb.addSeparator()

        tb.addWidget(QLabel(" Palette:"))
        self.depth_cb = QComboBox()
        self.depth_cb.addItems(list(BIT_DEPTHS.keys()))
        self.depth_cb.setCurrentText("24-bit")
        self.depth_cb.currentTextChanged.connect(self._depth_changed)
        tb.addWidget(self.depth_cb)

        tb.addSeparator()

        self._grayscale_action = QAction(self._emoji_icon("◑"), "Grayscale", self)
        self._grayscale_action.setToolTip("Grayscale")
        self._grayscale_action.triggered.connect(self._toggle_grayscale)
        tb.addAction(self._grayscale_action)

        def _fx_action(icon, label, slot):
            a = QAction(icon, label, self)
            a.setToolTip(label)
            a.triggered.connect(slot)
            tb.addAction(a)

        _fx_action(self._emoji_icon("🔄"), "Invert",
            lambda: (self.canvas.apply_effect("Invert Colors"), self.recorder.record("canvas.apply_effect('invert')")))
        _fx_action(self._emoji_icon("💧"),  "Smooth", self._smooth_with_dialog)
        _fx_action(self._emoji_icon("☀"),  "Brightness/Contrast",
            lambda: self._effect_with_dialog(
                "Brightness/Contrast",
                [("Brightness", -100, 100, self._last_bc_value[0]),
                 ("Contrast",   -100, 100, self._last_bc_value[1])],
                lambda b, c: self.canvas.apply_brightness_contrast(b, c),
                "_last_bc_value"))
        _fx_action(self._emoji_icon("🎨"), "Saturation",
            lambda: self._effect_with_dialog(
                "Saturation",
                [("Saturation", -100, 100, self._last_sat_value)],
                lambda v: self.canvas.apply_saturation(v),
                "_last_sat_value"))
        _fx_action(self._emoji_icon("🌫"),  "Noise",
            lambda: self._effect_with_dialog(
                "Noise",
                [("Amount", 0, 100, self._last_noise_value)],
                lambda v: self.canvas.apply_noise(v),
                "_last_noise_value"))
        _fx_action(self._emoji_icon("🔲"),  "Pixelate",
            lambda: self._effect_with_dialog(
                "Pixelate",
                [("Block size", 2, 64, self._last_pix_value)],
                lambda v: self.canvas.apply_pixelate(v),
                "_last_pix_value"))
        _fx_action(self._emoji_icon("🌈"), "Color Fade", self._colorfade_with_dialog)
        _fx_action(self._emoji_icon("🔪"),  "Sharpen", lambda: (self.canvas.apply_sharpen(), self.recorder.record("canvas.apply_effect('sharpen')")))
        _fx_action(self._emoji_icon("🎭"),  "Posterize",
            lambda: self._effect_with_dialog(
                "Posterize",
                [("Levels", 2, 16, self._last_posterize_value)],
                lambda v: self.canvas.apply_posterize(v),
                "_last_posterize_value"))
        _fx_action(self._emoji_icon("🗿"),  "Emboss", lambda: (self.canvas.apply_emboss(), self.recorder.record("canvas.apply_effect('emboss')")))
        _fx_action(self._emoji_icon("🌑"),  "Vignette",
            lambda: self._effect_with_dialog(
                "Vignette",
                [("Strength", 0, 200, self._last_vignette_value)],
                lambda v: self.canvas.apply_vignette(v),
                "_last_vignette_value"))

        self._tool_actions = {
            "pencil": pencil_action,
            "spray":  spray_action,
            "forms":  forms_action,
            "fill":   fill_action,
            "eraser": eraser_action,
            "cut":    cut_action,
            "text":   text_action,
            "picker": picker_action,
            "ruler":  ruler_action,
        }
        self._shortcut_actions.update({
            "Tool: Pencil":    pencil_action,
            "Tool: Spray":     spray_action,
            "Tool: Forms":     forms_action,
            "Tool: Fill":      fill_action,
            "Tool: Eraser":    eraser_action,
            "Tool: Selection": cut_action,
            "Tool: Text":      text_action,
            "Tool: Picker":    picker_action,
            "Tool: Ruler":     ruler_action,
            "Tool: Bg Color":  bg_action,
        })

    def _make_option_panel(self, widgets):
        """Helper: create a QWidget with a horizontal layout containing label/widget pairs."""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)
        for item in widgets:
            layout.addWidget(item)
        layout.addStretch()
        return panel

    def _build_optionbar(self):
        ob = QToolBar("Options", self)
        ob.setMovable(False)
        self.addToolBarBreak()
        self.addToolBar(ob)

        self._option_stack = QStackedWidget()
        self._option_stack.setMaximumHeight(68)
        ob.addWidget(self._option_stack)

        # --- Pencil panel ---
        _tog = "QPushButton:checked{background:#b0c8ff;border:1px solid #3366cc;}"
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 50)
        self.width_spin.setValue(2)
        self.width_spin.valueChanged.connect(lambda v: setattr(self.canvas, "pen_width", v))
        self.pen_color_btn = QPushButton()
        self.pen_color_btn.setFixedSize(20, 20)
        self.pen_color_btn.clicked.connect(self._pick_pen_color)
        self._set_color_btn(self.pen_color_btn, self.canvas.pen_color)
        self.pen_smooth1_btn = QPushButton("Smooth")
        self.pen_smooth1_btn.setCheckable(True)
        self.pen_smooth1_btn.setFixedHeight(24)
        self.pen_smooth1_btn.setStyleSheet(_tog)
        self.pen_smooth1_btn.toggled.connect(self._on_pencil_smooth_toggled)
        self.pen_smooth_pct1_spin = QSpinBox()
        self.pen_smooth_pct1_spin.setRange(0, 100)
        self.pen_smooth_pct1_spin.setValue(50)
        self.pen_smooth_pct1_spin.setSuffix("%")
        self.pen_smooth_pct1_spin.setFixedWidth(58)
        self.pen_smooth_pct1_spin.valueChanged.connect(lambda v: setattr(self.canvas, "pen_smooth_pct1", v))
        self.width_spin2 = QSpinBox()
        self.width_spin2.setRange(1, 50)
        self.width_spin2.setValue(2)
        self.width_spin2.valueChanged.connect(lambda v: setattr(self.canvas, "pen_width2", v))
        self.pen_color2_btn = QPushButton()
        self.pen_color2_btn.setFixedSize(20, 20)
        self.pen_color2_btn.clicked.connect(self._pick_pen_color2)
        self._set_color_btn(self.pen_color2_btn, self.canvas.pen_color2)
        self.pen_smooth2_btn = QPushButton("Smooth")
        self.pen_smooth2_btn.setCheckable(True)
        self.pen_smooth2_btn.setFixedHeight(24)
        self.pen_smooth2_btn.setStyleSheet(_tog)
        self.pen_smooth2_btn.toggled.connect(self._on_pencil_smooth_toggled)
        self.pen_smooth_pct2_spin = QSpinBox()
        self.pen_smooth_pct2_spin.setRange(0, 100)
        self.pen_smooth_pct2_spin.setValue(50)
        self.pen_smooth_pct2_spin.setSuffix("%")
        self.pen_smooth_pct2_spin.setFixedWidth(58)
        self.pen_smooth_pct2_spin.valueChanged.connect(lambda v: setattr(self.canvas, "pen_smooth_pct2", v))
        self._line_smooth_label = QLabel("Line-Smooth:")
        self._line_smooth_spin = QSpinBox()
        self._line_smooth_spin.setRange(0, 100)
        self._line_smooth_spin.setValue(0)
        self._line_smooth_spin.setSuffix("%")
        self._line_smooth_spin.setFixedWidth(58)
        self._line_smooth_spin.valueChanged.connect(lambda v: setattr(self.canvas, "_pencil_line_smooth", v))
        _tog2 = "QPushButton:checked{background:#b0c8ff;border:1px solid #3366cc;}"
        self._sym_h_btn = QPushButton("Sym H")
        self._sym_h_btn.setCheckable(True)
        self._sym_h_btn.setFixedSize(46, 24)
        self._sym_h_btn.setStyleSheet(_tog2)
        self._sym_h_btn.toggled.connect(lambda v: setattr(self.canvas, "symmetry_h", v))
        self._sym_v_btn = QPushButton("Sym V")
        self._sym_v_btn.setCheckable(True)
        self._sym_v_btn.setFixedSize(46, 24)
        self._sym_v_btn.setStyleSheet(_tog2)
        self._sym_v_btn.toggled.connect(lambda v: setattr(self.canvas, "symmetry_v", v))
        self._color_history_btns = []
        color_history_widget = QWidget()
        ch_layout = QHBoxLayout(color_history_widget)
        ch_layout.setContentsMargins(0, 0, 0, 0)
        ch_layout.setSpacing(2)
        for _ in range(10):
            b = QPushButton()
            b.setFixedSize(16, 16)
            b.setStyleSheet("background-color: #ffffff; border: 1px solid #888;")
            b.setVisible(False)
            def _make_press(btn):
                def _press(e):
                    color = QColor(btn.styleSheet().split("background-color: ")[1].split(";")[0])
                    if e.button() == Qt.RightButton:
                        self._pick_history_color(btn, right=True)
                    else:
                        self._pick_history_color(btn, right=False)
                return _press
            b.mousePressEvent = _make_press(b)
            ch_layout.addWidget(b)
            self._color_history_btns.append(b)
        self._color_history_widget = color_history_widget
        self._bezier_btn = QPushButton("∿ Bezier")
        self._bezier_btn.setCheckable(True)
        self._bezier_btn.setFixedSize(62, 24)
        self._bezier_btn.setStyleSheet(_tog)
        self._bezier_btn.setToolTip("Auto-smooth stroke into bezier curve on release")
        self._bezier_btn.toggled.connect(lambda v: setattr(self.canvas, "pencil_bezier", v))
        self._bezier_btn2 = QPushButton("∿ Bezier")
        self._bezier_btn2.setCheckable(True)
        self._bezier_btn2.setFixedSize(62, 24)
        self._bezier_btn2.setStyleSheet(_tog)
        self._bezier_btn2.setToolTip("Auto-smooth right-click stroke into bezier curve on release")
        self._bezier_btn2.toggled.connect(lambda v: setattr(self.canvas, "pencil_bezier2", v))
        def _fixed_label(text, w=62):
            lbl = QLabel(text)
            lbl.setFixedWidth(w)
            return lbl
        _pen_types = ["normal", "chalk", "charcoal", "calligraphy", "watercolor", "oil", "glow", "neon"]
        self._pen_type1_cb = QComboBox()
        self._pen_type1_cb.addItems(_pen_types)
        self._pen_type1_cb.setFixedWidth(82)
        self._pen_type1_cb.currentTextChanged.connect(lambda v: setattr(self.canvas, "pen_type1", v))
        self._pen_type2_cb = QComboBox()
        self._pen_type2_cb.addItems(_pen_types)
        self._pen_type2_cb.setFixedWidth(82)
        self._pen_type2_cb.currentTextChanged.connect(lambda v: setattr(self.canvas, "pen_type2", v))
        self._pen_intensity1_spin = QSpinBox()
        self._pen_intensity1_spin.setRange(1, 100)
        self._pen_intensity1_spin.setValue(100)
        self._pen_intensity1_spin.setSuffix("%")
        self._pen_intensity1_spin.setFixedWidth(58)
        self._pen_intensity1_spin.setToolTip("Pen intensity (opacity/blend strength)")
        self._pen_intensity1_spin.valueChanged.connect(lambda v: setattr(self.canvas, "pen_intensity1", v))
        self._pen_intensity2_spin = QSpinBox()
        self._pen_intensity2_spin.setRange(1, 100)
        self._pen_intensity2_spin.setValue(100)
        self._pen_intensity2_spin.setSuffix("%")
        self._pen_intensity2_spin.setFixedWidth(58)
        self._pen_intensity2_spin.setToolTip("Pen intensity (opacity/blend strength)")
        self._pen_intensity2_spin.valueChanged.connect(lambda v: setattr(self.canvas, "pen_intensity2", v))
        pencil_row1 = self._make_option_panel([
            _fixed_label("L-Width:", 48), self.width_spin,
            _fixed_label("L-Color:", 44), self.pen_color_btn,
            self._pen_type1_cb,
            _fixed_label("Intens:", 46), self._pen_intensity1_spin,
            self._sym_h_btn,
            self._bezier_btn,
            self.pen_smooth1_btn, self.pen_smooth_pct1_spin,
        ])
        pencil_row2 = self._make_option_panel([
            _fixed_label("R-Width:", 48), self.width_spin2,
            _fixed_label("R-Color:", 44), self.pen_color2_btn,
            self._pen_type2_cb,
            _fixed_label("Intens:", 46), self._pen_intensity2_spin,
            self._sym_v_btn,
            self._bezier_btn2,
            self.pen_smooth2_btn, self.pen_smooth_pct2_spin,
        ])
        pencil_panel = QWidget()
        pl = QVBoxLayout(pencil_panel)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(0)
        pl.addWidget(pencil_row1)
        pl.addWidget(pencil_row2)
        self._option_stack.addWidget(pencil_panel)   # index 0

        # --- Forms panel ---
        _tog = "QPushButton:checked{background:#b0c8ff;border:1px solid #3366cc;}"
        self._form_btns = {}
        for name, label in [
            ("line","—  Line"), ("rectangle","▭  Rect"), ("circle","○  Circle"), ("ellipse","⬭  Ellipse"), ("triangle","△  Tri"),
            ("trapezoid","⏢  Trap"), ("star","★  Star"), ("ngon","⬡  Polygon"), ("arrow","➤  Arrow"), ("parallelogram","▱  Para"),
            ("callout","💬  Call"), ("cross", "✚  Cross"),
            ("heart", "♥  Heart"), ("lightning", "⚡  Bolt"),
        ]:
            if not name:
                self._form_btns[f"_spacer_{name}{label}"] = None
                continue
            b = QPushButton(label)
            b.setCheckable(True)
            b.setFixedSize(66, 24)
            b.setStyleSheet(_tog)
            b.clicked.connect(lambda _, m=name: self._set_form_mode(m))
            self._form_btns[name] = b
        self._form_btns["line"].setChecked(True)
        self._corners_label = QLabel("N:")
        self._corners_spin = QSpinBox()
        self._corners_spin.setRange(4, 20)
        self._corners_spin.setValue(4)
        self._corners_spin.setFixedWidth(44)
        self._corners_spin.valueChanged.connect(self._on_corners_changed)
        self._arrow_head_label = QLabel("  Head:")
        self._arrow_head_spin = QSpinBox()
        self._arrow_head_spin.setRange(4, 500)
        self._arrow_head_spin.setValue(30)
        self._arrow_head_spin.setFixedWidth(52)
        self._arrow_head_spin.valueChanged.connect(lambda v: setattr(self.canvas, "arrow_head_size", v))
        self._arrow_dir_label = QLabel("  Dir:")
        self._arrow_dir_btns = {}
        for d, lbl in [("right", "►"), ("left", "◄"), ("up", "▲"), ("down", "▼")]:
            b = QPushButton(lbl)
            b.setCheckable(True)
            b.setFixedSize(28, 24)
            b.setStyleSheet(_tog)
            b.clicked.connect(lambda _, v=d: self._set_arrow_dir(v))
            self._arrow_dir_btns[d] = b
        self._arrow_dir_btns["right"].setChecked(True)
        self._para_orient_label = QLabel("  Orient:")
        self._para_orient_btns = {}
        for o, lbl in [("horizontal", "↔"), ("vertical", "↕")]:
            b = QPushButton(lbl)
            b.setCheckable(True)
            b.setFixedSize(28, 24)
            b.setStyleSheet(_tog)
            b.clicked.connect(lambda _, v=o: self._set_para_orient(v))
            self._para_orient_btns[o] = b
        self._para_orient_btns["horizontal"].setChecked(True)
        self._callout_tail_label = QLabel("  Tail:")
        self._callout_tail_spin = QSpinBox()
        self._callout_tail_spin.setRange(0, 100)
        self._callout_tail_spin.setValue(30)
        self._callout_tail_spin.setSuffix("%")
        self._callout_tail_spin.setFixedWidth(58)
        self._callout_tail_spin.valueChanged.connect(lambda v: setattr(self.canvas, "callout_tail_pos", v / 100.0))
        self.form_width_spin = QSpinBox()
        self.form_width_spin.setRange(1, 50)
        self.form_width_spin.setValue(2)
        self.form_width_spin.valueChanged.connect(lambda v: setattr(self.canvas, "pen_width", v))
        self.form_pen_color_btn = QPushButton()
        self.form_pen_color_btn.setFixedSize(20, 20)
        self.form_pen_color_btn.clicked.connect(self._pick_pen_color)
        self._set_color_btn(self.form_pen_color_btn, self.canvas.pen_color)
        self.form_fill_color_btn = QPushButton()
        self.form_fill_color_btn.setFixedSize(20, 20)
        self.form_fill_color_btn.clicked.connect(self._pick_form_fill_color)
        self._set_color_btn(self.form_fill_color_btn, self.canvas.form_fill_color)
        self.form_fill_transp_btn = QPushButton()
        self.form_fill_transp_btn.setCheckable(True)
        self.form_fill_transp_btn.setFixedSize(20, 20)
        self.form_fill_transp_btn.setIcon(QIcon(self._make_checkerboard_icon()))
        self.form_fill_transp_btn.setIconSize(QSize(16, 16))
        self.form_fill_transp_btn.setStyleSheet("QPushButton:checked{border:2px solid #3366cc;}")
        self.form_fill_transp_btn.toggled.connect(lambda v: setattr(self.canvas, "form_fill_transparent", v))
        self._form_style_btns = {}
        _style_tips = {"solid": "Solid", "dashed": "Dashed", "dotted": "Dotted", "dash-dotted": "Dash-Dotted"}
        for style, label in [("solid","—"),("dashed","╌"),("dotted","···"),("dash-dotted","─·")]:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setFixedSize(28, 24)
            b.setStyleSheet(_tog)
            b.setToolTip(_style_tips[style])
            b.clicked.connect(lambda _, s=style: self._set_form_line_style(s))
            self._form_style_btns[style] = b
        self._form_style_btns["solid"].setChecked(True)
        self.tri_orient_label = QLabel("  Orient:")
        self._tri_orient_btns = {}
        for orient, label in [("horizontal", "↔"), ("vertical", "↕")]:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setFixedSize(28, 24)
            b.setStyleSheet(_tog)
            b.clicked.connect(lambda _, o=orient: self._set_tri_orient(o))
            self._tri_orient_btns[orient] = b
        self._tri_orient_btns["horizontal"].setChecked(True)
        self._tri_perp_btn = QPushButton("⊾ Perp")
        self._tri_perp_btn.setCheckable(True)
        self._tri_perp_btn.setFixedSize(52, 24)
        self._tri_perp_btn.setStyleSheet(_tog)
        self._tri_perp_btn.toggled.connect(lambda v: setattr(self.canvas, "triangle_perpendicular", v))
        self._trap_flip_btn = QPushButton("⇕ Flip")
        self._trap_flip_btn.setCheckable(True)
        self._trap_flip_btn.setFixedSize(52, 24)
        self._trap_flip_btn.setStyleSheet(_tog)
        self._trap_flip_btn.setToolTip("Flip trapezoid vertically")
        self._trap_flip_btn.toggled.connect(lambda v: setattr(self.canvas, "trapezoid_flip", v))
        self._line_arrow_label = QLabel("  Arrows:")
        self._line_arrow_start_btn = QPushButton("◄ Start")
        self._line_arrow_start_btn.setCheckable(True)
        self._line_arrow_start_btn.setFixedSize(58, 24)
        self._line_arrow_start_btn.setStyleSheet(_tog)
        self._line_arrow_start_btn.toggled.connect(lambda v: setattr(self.canvas, "line_arrow_start", v))
        self._line_arrow_end_btn = QPushButton("End ►")
        self._line_arrow_end_btn.setCheckable(True)
        self._line_arrow_end_btn.setFixedSize(58, 24)
        self._line_arrow_end_btn.setStyleSheet(_tog)
        self._line_arrow_end_btn.toggled.connect(lambda v: setattr(self.canvas, "line_arrow_end", v))
        self._line_arrow_inward_btn = QPushButton("◄►")
        self._line_arrow_inward_btn.setCheckable(True)
        self._line_arrow_inward_btn.setFixedSize(36, 24)
        self._line_arrow_inward_btn.setStyleSheet(_tog)
        self._line_arrow_inward_btn.setToolTip("Inward (checked) / Outward (unchecked)")
        self._line_arrow_inward_btn.toggled.connect(lambda v: setattr(self.canvas, "line_arrow_inward", v))
        self._form_aa_btn = QPushButton("AA")
        self._form_aa_btn.setCheckable(True)
        self._form_aa_btn.setChecked(True)
        self._form_aa_btn.setFixedSize(28, 24)
        self._form_aa_btn.setStyleSheet(_tog)
        self._form_aa_btn.setToolTip("Anti-Aliasing")
        self._form_aa_btn.toggled.connect(lambda v: setattr(self.canvas, "form_antialias", v))
        self._corner_radius_label = QLabel("  R:")
        self._corner_radius_spin = QSpinBox()
        self._corner_radius_spin.setRange(0, 500)
        self._corner_radius_spin.setValue(0)
        self._corner_radius_spin.setFixedWidth(48)
        self._corner_radius_spin.valueChanged.connect(lambda v: setattr(self.canvas, "rect_corner_radius", v))
        self._arc_start_label = QLabel("  From:")
        self._arc_start_spin = QSpinBox()
        self._arc_start_spin.setRange(0, 359)
        self._arc_start_spin.setValue(0)
        self._arc_start_spin.setSuffix("°")
        self._arc_start_spin.setFixedWidth(54)
        self._arc_start_spin.valueChanged.connect(lambda v: setattr(self.canvas, "circle_start_angle", v))
        self._arc_span_label = QLabel("  Span:")
        self._arc_span_spin = QSpinBox()
        self._arc_span_spin.setRange(1, 360)
        self._arc_span_spin.setValue(360)
        self._arc_span_spin.setSuffix("°")
        self._arc_span_spin.setFixedWidth(54)
        self._arc_span_spin.valueChanged.connect(lambda v: setattr(self.canvas, "circle_span_angle", v))
        self._arc_pie_btn = QPushButton("Pie")
        self._arc_pie_btn.setCheckable(True)
        self._arc_pie_btn.setFixedSize(36, 24)
        self._arc_pie_btn.setStyleSheet(_tog)
        self._arc_pie_btn.setToolTip("Pie (filled to center) vs Arc")
        self._arc_pie_btn.toggled.connect(lambda v: setattr(self.canvas, "circle_pie_mode", v))
        self._donut_btn = QPushButton("⊙ Donut")
        self._donut_btn.setCheckable(True)
        self._donut_btn.setFixedSize(62, 24)
        self._donut_btn.setStyleSheet(_tog)
        self._donut_btn.toggled.connect(lambda v: (
            setattr(self.canvas, "circle_donut", v),
            self._donut_gap_label.setVisible(v),
            self._donut_gap_spin.setVisible(v),
        ))
        self._donut_gap_label = QLabel("  Gap:")
        self._donut_gap_spin = QSpinBox()
        self._donut_gap_spin.setRange(1, 2000)
        self._donut_gap_spin.setValue(20)
        self._donut_gap_spin.setFixedWidth(52)
        self._donut_gap_spin.valueChanged.connect(lambda v: setattr(self.canvas, "donut_gap", v))
        self._form_dim_label = QLabel("")
        self._form_dim_label.setFixedWidth(110)
        forms_panel = QWidget()
        fl = QVBoxLayout(forms_panel)
        fl.setContentsMargins(2, 1, 2, 1)
        fl.setSpacing(1)
        # row 1: 6 shape buttons + color/width/style options
        row1_names = ["line", "rectangle", "circle", "ellipse", "triangle", "trapezoid", "heart"]
        # row 2: 7 shape buttons + shape-specific options
        row2_names = ["star", "ngon", "arrow", "parallelogram", "callout", "cross", "lightning"]
        self._grid_snap_btn = QPushButton("⊞ Snap")
        self._grid_snap_btn.setCheckable(True)
        self._grid_snap_btn.setFixedSize(58, 24)
        self._grid_snap_btn.setStyleSheet(_tog)
        self._grid_snap_btn.setToolTip("Snap to grid (requires grid visible)")
        self._grid_snap_btn.toggled.connect(lambda v: setattr(self.canvas, "_grid_snap", v))
        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(2)
        btn_row1.setContentsMargins(0, 0, 0, 0)
        for n in row1_names:
            btn_row1.addWidget(self._form_btns[n])
        btn_row1.addWidget(QLabel("  W:"))
        btn_row1.addWidget(self.form_width_spin)
        btn_row1.addWidget(QLabel("  Pen:"))
        btn_row1.addWidget(self.form_pen_color_btn)
        btn_row1.addWidget(QLabel("  Fill:"))
        btn_row1.addWidget(self.form_fill_color_btn)
        btn_row1.addWidget(self.form_fill_transp_btn)
        btn_row1.addWidget(QLabel("  Line:"))
        for b in self._form_style_btns.values():
            btn_row1.addWidget(b)
        btn_row1.addWidget(QLabel("  "))
        btn_row1.addWidget(self._form_aa_btn)
        btn_row1.addWidget(self._grid_snap_btn)
        btn_row1.addStretch()
        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(2)
        btn_row2.setContentsMargins(0, 0, 0, 0)
        for n in row2_names:
            btn_row2.addWidget(self._form_btns[n])
        btn_row2.addWidget(self._corner_radius_label)
        btn_row2.addWidget(self._corner_radius_spin)
        btn_row2.addWidget(self._arc_start_label)
        btn_row2.addWidget(self._arc_start_spin)
        btn_row2.addWidget(self._arc_span_label)
        btn_row2.addWidget(self._arc_span_spin)
        btn_row2.addWidget(self._arc_pie_btn)
        btn_row2.addWidget(self._donut_btn)
        btn_row2.addWidget(self._donut_gap_label)
        btn_row2.addWidget(self._donut_gap_spin)
        btn_row2.addWidget(self.tri_orient_label)
        for b in self._tri_orient_btns.values():
            btn_row2.addWidget(b)
        btn_row2.addWidget(self._tri_perp_btn)
        btn_row2.addWidget(self._trap_flip_btn)
        btn_row2.addWidget(self._line_arrow_label)
        btn_row2.addWidget(self._line_arrow_start_btn)
        btn_row2.addWidget(self._line_arrow_end_btn)
        btn_row2.addWidget(self._line_arrow_inward_btn)
        btn_row2.addWidget(self._corners_label)
        btn_row2.addWidget(self._corners_spin)
        btn_row2.addWidget(self._arrow_head_label)
        btn_row2.addWidget(self._arrow_head_spin)
        btn_row2.addWidget(self._arrow_dir_label)
        for b in self._arrow_dir_btns.values():
            btn_row2.addWidget(b)
        btn_row2.addWidget(self._para_orient_label)
        for b in self._para_orient_btns.values():
            btn_row2.addWidget(b)
        btn_row2.addWidget(self._callout_tail_label)
        btn_row2.addWidget(self._callout_tail_spin)
        btn_row2.addWidget(QLabel("  "))
        btn_row2.addWidget(self._form_dim_label)
        btn_row2.addStretch()
        fl.addLayout(btn_row1)
        fl.addLayout(btn_row2)
        self._option_stack.addWidget(forms_panel)    # index 1

        # --- Fill panel ---
        self.fill_color_btn = QPushButton()
        self.fill_color_btn.setFixedSize(20, 20)
        self.fill_color_btn.clicked.connect(self._pick_fill_color)
        self._set_color_btn(self.fill_color_btn, self.canvas.fill_color)
        self.fill_color2_btn = QPushButton()
        self.fill_color2_btn.setFixedSize(20, 20)
        self.fill_color2_btn.clicked.connect(self._pick_fill_color2)
        self._set_color_btn(self.fill_color2_btn, self.canvas.fill_color2)
        self._fill_tol_spin = QSpinBox()
        self._fill_tol_spin.setRange(0, 255)
        self._fill_tol_spin.setValue(0)
        self._fill_tol_spin.setFixedWidth(52)
        self._fill_tol_spin.setToolTip("Tolerance: 0 = exact match, higher = fill similar colors")
        self._fill_tol_spin.valueChanged.connect(lambda v: setattr(self.canvas, "fill_tolerance", v))
        def _fxl(t, w): l=QLabel(t); l.setFixedWidth(w); return l
        fill_row1 = self._make_option_panel([_fxl("L-Click:", 52), self.fill_color_btn, _fxl("Tolerance:", 64), self._fill_tol_spin])
        self._fill_tol2_spin = QSpinBox()
        self._fill_tol2_spin.setRange(0, 255)
        self._fill_tol2_spin.setValue(0)
        self._fill_tol2_spin.setFixedWidth(52)
        self._fill_tol2_spin.setToolTip("Tolerance: 0 = exact match, higher = fill similar colors")
        self._fill_tol2_spin.valueChanged.connect(lambda v: setattr(self.canvas, "fill_tolerance2", v))
        fill_row2 = self._make_option_panel([_fxl("R-Click:", 52), self.fill_color2_btn, _fxl("Tolerance:", 64), self._fill_tol2_spin])
        fill_panel = QWidget()
        _fl = QVBoxLayout(fill_panel)
        _fl.setContentsMargins(0, 0, 0, 0)
        _fl.setSpacing(0)
        _fl.addWidget(fill_row1)
        _fl.addWidget(fill_row2)
        self._option_stack.addWidget(fill_panel)     # index 2

        # --- Eraser panel ---
        self.eraser_spin = QSpinBox()
        self.eraser_spin.setRange(1, 200)
        self.eraser_spin.setValue(10)
        self.eraser_spin.valueChanged.connect(lambda v: setattr(self.canvas, "eraser_width", v))
        eraser_panel = self._make_option_panel([
            QLabel("Size:"), self.eraser_spin,
        ])
        self._option_stack.addWidget(eraser_panel)   # index 3

        # --- Cut panel ---
        self._cut_rect_btn = QPushButton("□ Rect")
        self._cut_rect_btn.setCheckable(True)
        self._cut_rect_btn.setChecked(True)
        self._cut_rect_btn.setFixedSize(54, 24)
        self._cut_circ_btn = QPushButton("○ Circle")
        self._cut_circ_btn.setCheckable(True)
        self._cut_circ_btn.setFixedSize(54, 24)
        self._cut_ellipse_btn = QPushButton("⬭ Ellipse")
        self._cut_ellipse_btn.setCheckable(True)
        self._cut_ellipse_btn.setFixedSize(60, 24)
        self._cut_lasso_btn = QPushButton("⬡ Lasso")
        self._cut_lasso_btn.setCheckable(True)
        self._cut_lasso_btn.setFixedSize(60, 24)
        self._cut_lasso_btn.clicked.connect(lambda: self._set_cut_mode("lasso"))
        self._cut_wand_btn = QPushButton("🪄 Wand")
        self._cut_wand_btn.setCheckable(True)
        self._cut_wand_btn.setFixedSize(60, 24)
        self._cut_rect_btn.clicked.connect(lambda: self._set_cut_mode("rectangle"))
        self._cut_circ_btn.clicked.connect(lambda: self._set_cut_mode("circle"))
        self._cut_ellipse_btn.clicked.connect(lambda: self._set_cut_mode("ellipse"))
        self._cut_wand_btn.clicked.connect(lambda: self._set_cut_mode("wand"))
        self._cut_op_cut_btn = QPushButton("✂ Cut")
        self._cut_op_cut_btn.setCheckable(True)
        self._cut_op_cut_btn.setFixedSize(54, 24)
        self._cut_op_copy_btn = QPushButton("⧉ Copy")
        self._cut_op_copy_btn.setCheckable(True)
        self._cut_op_copy_btn.setFixedSize(54, 24)
        self._cut_op_sel_btn = QPushButton("[ ] Sel")
        self._cut_op_sel_btn.setCheckable(True)
        self._cut_op_sel_btn.setChecked(True)
        self._cut_op_sel_btn.setFixedSize(54, 24)
        self._cut_op_cut_btn.clicked.connect(lambda: self._set_cut_op("cut"))
        self._cut_op_copy_btn.clicked.connect(lambda: self._set_cut_op("copy"))
        self._cut_op_sel_btn.clicked.connect(lambda: self._set_cut_op("select"))
        self._cut_resize_btn = QPushButton("⧂ Resize")
        self._cut_resize_btn.setCheckable(True)
        self._cut_resize_btn.setFixedSize(60, 24)
        self._cut_resize_btn.setToolTip("Enable resize handles on selection")
        self._cut_resize_btn.toggled.connect(lambda v: setattr(self.canvas, "selection_resize_enabled", v))
        self._cut_flip_h_btn = QPushButton("⇔ Flip H")
        self._cut_flip_h_btn.setFixedSize(60, 24)
        self._cut_flip_h_btn.clicked.connect(lambda: self.canvas._flip_cut(True))
        self._cut_flip_v_btn = QPushButton("⇕ Flip V")
        self._cut_flip_v_btn.setFixedSize(60, 24)
        self._cut_flip_v_btn.clicked.connect(lambda: self.canvas._flip_cut(False))
        self._cut_rotate_spin = QSpinBox()
        self._cut_rotate_spin.setRange(0, 359)
        self._cut_rotate_spin.setValue(0)
        self._cut_rotate_spin.setSuffix("°")
        self._cut_rotate_spin.setFixedWidth(58)
        self._cut_rotate_spin.setWrapping(True)
        self._cut_rotate_spin.valueChanged.connect(lambda v: self.canvas._rotate_cut(v))
        self._cut_delete_btn = QPushButton("❌ Del")
        self._cut_delete_btn.setFixedSize(54, 24)
        self._cut_delete_btn.setToolTip("Delete selection (fill with background color)")
        self._cut_delete_btn.setStyleSheet("QPushButton { color: #cc0000; font-weight: bold; }")
        self._cut_delete_btn.clicked.connect(self._on_cut_delete)
        self._cut_dim_label = QLabel("")
        self._cut_dim_label.setFixedWidth(90)
        cut_panel = QWidget()
        cut_vl = QVBoxLayout(cut_panel)
        cut_vl.setContentsMargins(2, 1, 2, 1)
        cut_vl.setSpacing(1)
        cut_row1 = QHBoxLayout()
        cut_row1.setSpacing(2)
        cut_row1.setContentsMargins(0, 0, 0, 0)
        _cut_lbl = QLabel("Shape:")
        _cut_lbl.setFixedWidth(36)
        cut_row1.addWidget(_cut_lbl)
        cut_row1.addWidget(self._cut_rect_btn)
        cut_row1.addWidget(self._cut_circ_btn)
        cut_row1.addWidget(self._cut_ellipse_btn)
        cut_row1.addWidget(self._cut_lasso_btn)
        cut_row1.addWidget(self._cut_wand_btn)
        cut_row1.addWidget(QLabel("  "))
        cut_row1.addWidget(self._cut_flip_h_btn)
        cut_row1.addWidget(self._cut_flip_v_btn)
        cut_row1.addWidget(QLabel("Rotate:"))
        cut_row1.addWidget(self._cut_rotate_spin)
        cut_row1.addStretch()
        cut_row2 = QHBoxLayout()
        cut_row2.setSpacing(2)
        cut_row2.setContentsMargins(0, 0, 0, 0)
        _op_lbl = QLabel("Op:")
        _op_lbl.setFixedWidth(36)
        cut_row2.addWidget(_op_lbl)
        cut_row2.addWidget(self._cut_op_sel_btn)
        cut_row2.addWidget(self._cut_op_cut_btn)
        cut_row2.addWidget(self._cut_op_copy_btn)
        cut_row2.addWidget(QLabel("  "))
        cut_row2.addWidget(self._cut_resize_btn)
        cut_row2.addWidget(self._cut_delete_btn)
        cut_row2.addWidget(QLabel("  "))
        cut_row2.addWidget(self._cut_dim_label)
        cut_row2.addStretch()
        cut_vl.addLayout(cut_row1)
        cut_vl.addLayout(cut_row2)
        self._option_stack.addWidget(cut_panel)      # index 4

        # --- Text panel ---
        _fmt_style = "QPushButton{font-weight:bold;} QPushButton:checked{background:#b0c8ff;border:1px solid #3366cc;}"
        self.font_cb = QFontComboBox()
        self.font_cb.setCurrentFont(QFont("Arial"))
        self.font_cb.setFixedWidth(140)
        self.font_cb.currentFontChanged.connect(self._update_text_font)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(4, 200)
        self.font_size_spin.setValue(12)
        self.font_size_spin.valueChanged.connect(self._update_text_font)
        self.bold_btn = QPushButton("\U0001d401")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setFixedSize(24, 24)
        self.bold_btn.setStyleSheet(_fmt_style)
        self.bold_btn.toggled.connect(self._update_text_font)
        self.italic_btn = QPushButton("I")
        self.italic_btn.setCheckable(True)
        self.italic_btn.setFixedSize(24, 24)
        self.italic_btn.setStyleSheet("QPushButton{font-family:'Times New Roman';font-style:italic;font-size:13px;} QPushButton:checked{background:#b0c8ff;border:1px solid #3366cc;}")
        self.italic_btn.toggled.connect(self._update_text_font)
        self.underline_btn = QPushButton("U\u0332")
        self.underline_btn.setCheckable(True)
        self.underline_btn.setFixedSize(24, 24)
        self.underline_btn.setStyleSheet(_fmt_style)
        self.underline_btn.toggled.connect(self._update_text_font)
        self._text_aa_btn = QPushButton("AA")
        self._text_aa_btn.setCheckable(True)
        self._text_aa_btn.setChecked(True)
        self._text_aa_btn.setFixedSize(28, 24)
        self._text_aa_btn.setStyleSheet("QPushButton:checked{background:#b0c8ff;border:1px solid #3366cc;}")
        self._text_aa_btn.setToolTip("Anti-Aliasing")
        self._text_aa_btn.toggled.connect(lambda v: setattr(self.canvas, "text_antialias", v))
        self.text_color_btn = QPushButton()
        self.text_color_btn.setFixedSize(20, 20)
        self.text_color_btn.clicked.connect(self._pick_text_color)
        self._set_color_btn(self.text_color_btn, self.canvas.text_color)
        self.text_bg_color_btn = QPushButton()
        self.text_bg_color_btn.setFixedSize(20, 20)
        self.text_bg_color_btn.clicked.connect(self._pick_text_bg_color)
        self._set_color_btn(self.text_bg_color_btn, self.canvas.text_bg_color)
        self.text_bg_transp_btn = QPushButton()
        self.text_bg_transp_btn.setCheckable(True)
        self.text_bg_transp_btn.setFixedSize(20, 20)
        self.text_bg_transp_btn.setIcon(QIcon(self._make_checkerboard_icon()))
        self.text_bg_transp_btn.setIconSize(QSize(16, 16))
        self.text_bg_transp_btn.setStyleSheet("QPushButton:checked{border:2px solid #3366cc;}")
        self.text_bg_transp_btn.toggled.connect(self._on_text_setting_changed)
        self.text_box_cb = QCheckBox("Box")
        self.text_box_cb.toggled.connect(self._on_text_box_toggled)
        self.text_box_color_btn = QPushButton()
        self.text_box_color_btn.setFixedSize(20, 20)
        self.text_box_color_btn.clicked.connect(self._pick_text_box_color)
        self._set_color_btn(self.text_box_color_btn, self.canvas.text_box_color)
        self.text_box_margin_label = QLabel("Margin:")
        self.text_box_margin_spin = QSpinBox()
        self.text_box_margin_spin.setRange(0, 50)
        self.text_box_margin_spin.setValue(4)
        self.text_box_margin_spin.setFixedWidth(48)
        self.text_box_margin_spin.valueChanged.connect(self._on_text_setting_changed)
        self.text_box_style_label = QLabel("Line:")
        self.text_box_style_cb = QComboBox()
        self.text_box_style_cb.addItems(["solid", "dashed", "dotted"])
        self.text_box_style_cb.setFixedWidth(70)
        self.text_box_style_cb.currentTextChanged.connect(self._on_text_setting_changed)
        self.text_box_width_label = QLabel("Width:")
        self.text_box_width_spin = QSpinBox()
        self.text_box_width_spin.setRange(1, 20)
        self.text_box_width_spin.setValue(1)
        self.text_box_width_spin.setFixedWidth(44)
        self.text_box_width_spin.valueChanged.connect(self._on_text_setting_changed)
        self.text_input = QLineEdit("Text")
        self.text_input.textChanged.connect(self._on_text_setting_changed)
        row1 = self._make_option_panel([
            QLabel("Font:"), self.font_cb,
            QLabel("  Size:"), self.font_size_spin,
            self.bold_btn, self.italic_btn, self.underline_btn, self._text_aa_btn,
            QLabel("  Color:"), self.text_color_btn,
            QLabel("  BG:"), self.text_bg_color_btn, self.text_bg_transp_btn,
            self.text_box_cb, self.text_box_color_btn,
            self.text_box_margin_label, self.text_box_margin_spin,
            self.text_box_style_label, self.text_box_style_cb,
            self.text_box_width_label, self.text_box_width_spin,
        ])
        row2 = self._make_option_panel([QLabel("Text:"), self.text_input])
        self.text_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        text_panel = QWidget()
        tl = QVBoxLayout(text_panel)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(0)
        tl.addWidget(row1)
        tl.addWidget(row2)
        self._option_stack.addWidget(text_panel)     # index 5

        # --- Picker panel ---
        self._picker_swatch = QLabel()
        self._picker_swatch.setFixedSize(20, 20)
        self._picker_swatch.setStyleSheet("background-color: #000000; border: 1px solid #888;")
        self._picker_rgb_label = QLabel("RGB: 0, 0, 0")
        self._picker_sample_spin = QSpinBox()
        self._picker_sample_spin.setRange(0, 50)
        self._picker_sample_spin.setValue(0)
        self._picker_sample_spin.setFixedWidth(48)
        self._picker_sample_spin.setToolTip("Sample radius (0 = single pixel)")
        self._picker_sample_spin.valueChanged.connect(lambda v: setattr(self.canvas, "picker_sample_radius", v))
        self._picker_swatch2 = QLabel()
        self._picker_swatch2.setFixedSize(20, 20)
        self._picker_swatch2.setStyleSheet("background-color: #ffffff; border: 1px solid #888;")
        self._picker_rgb_label2 = QLabel("RGB: 255, 255, 255")
        self._picker_sample_spin2 = QSpinBox()
        self._picker_sample_spin2.setRange(0, 50)
        self._picker_sample_spin2.setValue(0)
        self._picker_sample_spin2.setFixedWidth(48)
        self._picker_sample_spin2.setToolTip("Sample radius (0 = single pixel)")
        self._picker_sample_spin2.valueChanged.connect(lambda v: setattr(self.canvas, "picker_sample_radius2", v))
        def _pxl(t, w): l=QLabel(t); l.setFixedWidth(w); return l
        picker_row1 = self._make_option_panel([
            _pxl("L-Pick:", 52), self._picker_swatch, self._picker_rgb_label,
            _pxl("Radius:", 48), self._picker_sample_spin,
        ])
        picker_row2 = self._make_option_panel([
            _pxl("R-Pick:", 52), self._picker_swatch2, self._picker_rgb_label2,
            _pxl("Radius:", 48), self._picker_sample_spin2,
        ])
        picker_panel = QWidget()
        _pl = QVBoxLayout(picker_panel)
        _pl.setContentsMargins(0, 0, 0, 0)
        _pl.setSpacing(0)
        _pl.addWidget(picker_row1)
        _pl.addWidget(picker_row2)
        self._option_stack.addWidget(picker_panel)   # index 6

        # --- Spray panel ---
        self._spray_radius_spin = QSpinBox()
        self._spray_radius_spin.setRange(2, 200)
        self._spray_radius_spin.setValue(20)
        self._spray_radius_spin.valueChanged.connect(lambda v: setattr(self.canvas, "spray_radius", v))
        self._spray_density_spin = QSpinBox()
        self._spray_density_spin.setRange(1, 200)
        self._spray_density_spin.setValue(30)
        self._spray_density_spin.valueChanged.connect(lambda v: setattr(self.canvas, "spray_density", v))
        self._spray_color_btn = QPushButton()
        self._spray_color_btn.setFixedSize(20, 20)
        self._spray_color_btn.clicked.connect(self._pick_pen_color)
        self._set_color_btn(self._spray_color_btn, self.canvas.pen_color)
        self._spray_radius2_spin = QSpinBox()
        self._spray_radius2_spin.setRange(2, 200)
        self._spray_radius2_spin.setValue(20)
        self._spray_radius2_spin.valueChanged.connect(lambda v: setattr(self.canvas, "spray_radius2", v))
        self._spray_density2_spin = QSpinBox()
        self._spray_density2_spin.setRange(1, 200)
        self._spray_density2_spin.setValue(30)
        self._spray_density2_spin.valueChanged.connect(lambda v: setattr(self.canvas, "spray_density2", v))
        self._spray_color2_btn = QPushButton()
        self._spray_color2_btn.setFixedSize(20, 20)
        self._spray_color2_btn.clicked.connect(self._pick_pen_color2)
        self._set_color_btn(self._spray_color2_btn, self.canvas.pen_color2)
        def _sl(text, w=None):
            l = QLabel(text)
            if w: l.setFixedWidth(w)
            return l
        spray_row1 = self._make_option_panel([
            _sl("L-Radius:", 52), self._spray_radius_spin,
            _sl("L-Density:", 58), self._spray_density_spin,
            _sl("L-Color:", 44), self._spray_color_btn,
        ])
        spray_row2 = self._make_option_panel([
            _sl("R-Radius:", 52), self._spray_radius2_spin,
            _sl("R-Density:", 58), self._spray_density2_spin,
            _sl("R-Color:", 44), self._spray_color2_btn,
        ])
        spray_panel = QWidget()
        sl = QVBoxLayout(spray_panel)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)
        sl.addWidget(spray_row1)
        sl.addWidget(spray_row2)
        self._option_stack.addWidget(spray_panel)    # index 7

        # --- Ruler panel ---
        self._ruler_dx_label    = QLabel("ΔX: —")
        self._ruler_dy_label    = QLabel("ΔY: —")
        self._ruler_len_label   = QLabel("Length: —")
        self._ruler_angle_label = QLabel("Angle: —")
        ruler_panel = QWidget()
        ruler_layout = QHBoxLayout(ruler_panel)
        ruler_layout.setContentsMargins(4, 2, 4, 2)
        ruler_layout.setSpacing(12)
        col1 = QVBoxLayout()
        col1.setSpacing(1)
        col1.addWidget(self._ruler_dx_label)
        col1.addWidget(self._ruler_dy_label)
        col2 = QVBoxLayout()
        col2.setSpacing(1)
        col2.addWidget(self._ruler_len_label)
        col2.addWidget(self._ruler_angle_label)
        ruler_layout.addLayout(col1)
        ruler_layout.addLayout(col2)
        ruler_layout.addStretch()
        self._option_stack.addWidget(ruler_panel)     # index 8

        self._tool_option_index = {"pencil": 0, "forms": 1, "fill": 2, "eraser": 3, "cut": 4, "text": 5, "picker": 6, "spray": 7, "ruler": 8}
        self.pen_smooth_pct1_spin.setVisible(False)
        self.pen_smooth_pct2_spin.setVisible(False)
        self.tri_orient_label.setVisible(False)
        for b in self._tri_orient_btns.values():
            b.setVisible(False)
        self._tri_perp_btn.setVisible(False)
        self._trap_flip_btn.setVisible(False)
        self._line_arrow_label.setVisible(True)
        self._line_arrow_start_btn.setVisible(True)
        self._line_arrow_end_btn.setVisible(True)
        self._line_arrow_inward_btn.setVisible(True)
        self._corners_label.setVisible(False)
        self._corners_spin.setVisible(False)
        self._arrow_head_label.setVisible(False)
        self._arrow_head_spin.setVisible(False)
        self._arrow_dir_label.setVisible(False)
        for b in self._arrow_dir_btns.values():
            b.setVisible(False)
        self._para_orient_label.setVisible(False)
        for b in self._para_orient_btns.values():
            b.setVisible(False)
        self._callout_tail_label.setVisible(False)
        self._callout_tail_spin.setVisible(False)
        self._corner_radius_label.setVisible(False)
        self._corner_radius_spin.setVisible(False)
        self._arc_start_label.setVisible(False)
        self._arc_start_spin.setVisible(False)
        self._arc_span_label.setVisible(False)
        self._arc_span_spin.setVisible(False)
        self._arc_pie_btn.setVisible(False)
        self._donut_btn.setVisible(False)
        self._donut_gap_label.setVisible(False)
        self._donut_gap_spin.setVisible(False)
        # hide box-only widgets initially
        self.text_box_margin_label.setVisible(False)
        self.text_box_margin_spin.setVisible(False)
        self.text_box_style_label.setVisible(False)
        self.text_box_style_cb.setVisible(False)
        self.text_box_width_label.setVisible(False)
        self.text_box_width_spin.setVisible(False)

    def _pick_history_color(self, btn, right=False):
        color = QColor(btn.styleSheet().split("background-color: ")[1].split(";")[0])
        if right:
            self.canvas.pen_color2 = color
            self._set_color_btn(self.pen_color2_btn, color)
            self._set_color_btn(self._spray_color2_btn, color)
            self.canvas.form_fill_color = color
            self._set_color_btn(self.form_fill_color_btn, color)
            self.canvas.fill_color2 = color
            self._set_color_btn(self.fill_color2_btn, color)
        else:
            self.canvas.pen_color = color
            self._set_color_btn(self.pen_color_btn, color)
            self._set_color_btn(self.form_pen_color_btn, color)
            self._set_color_btn(self._spray_color_btn, color)
            self.canvas.text_color = color
            self._set_color_btn(self.text_color_btn, color)
            self.canvas.fill_color = color
            self._set_color_btn(self.fill_color_btn, color)
            self.canvas._update_pen_cursor()

    def _push_color_history(self, color):
        if color in self.canvas._color_history:
            self.canvas._color_history.remove(color)
        self.canvas._color_history.insert(0, color)
        self.canvas._color_history = self.canvas._color_history[:10]
        for i, btn in enumerate(self._color_history_btns):
            if i < len(self.canvas._color_history):
                c = self.canvas._color_history[i]
                btn.setStyleSheet(f"background-color: {c.name()}; border: 1px solid #888;")
                btn.setVisible(True)
            else:
                btn.setVisible(False)

    def _on_pencil_smooth_toggled(self, _):
        v1 = self.pen_smooth1_btn.isChecked()
        v2 = self.pen_smooth2_btn.isChecked()
        self.canvas.pen_smooth1 = v1
        self.canvas.pen_smooth2 = v2
        self.pen_smooth_pct1_spin.setVisible(v1)
        self.pen_smooth_pct2_spin.setVisible(v2)

    def _on_corners_changed(self, v):
        self.canvas.star_corners = v
        self.canvas.ngon_edges = v

    def _update_form_dim(self, start, end):
        mode = self.canvas.form_mode
        if mode in ("circle", "star", "ngon"):
            r = int(math.hypot(end.x() - start.x(), end.y() - start.y()))
            self._form_dim_label.setText(f"R: {r}")
        elif mode == "line":
            dx, dy = end.x() - start.x(), end.y() - start.y()
            self._form_dim_label.setText(f"dx:{dx}  dy:{dy}")
        else:
            r = QRect(start, end).normalized()
            self._form_dim_label.setText(f"W:{r.width()}  H:{r.height()}")

    def _set_form_mode(self, mode):
        self.canvas.form_mode = mode
        for m, b in self._form_btns.items():
            if b is not None:
                b.setChecked(m == mode)
        show_tri = mode == "triangle"
        self.tri_orient_label.setVisible(show_tri)
        for b in self._tri_orient_btns.values():
            b.setVisible(show_tri)
        self._tri_perp_btn.setVisible(show_tri)
        self._trap_flip_btn.setVisible(mode == "trapezoid")
        show_arrow = mode == "line"
        self._line_arrow_label.setVisible(show_arrow)
        self._line_arrow_start_btn.setVisible(show_arrow)
        self._line_arrow_end_btn.setVisible(show_arrow)
        self._line_arrow_inward_btn.setVisible(show_arrow)
        show_corners = mode in ("star", "ngon")
        self._corners_label.setVisible(show_corners)
        self._corners_spin.setVisible(show_corners)
        show_arrow_head = mode == "arrow"
        self._arrow_head_label.setVisible(show_arrow_head)
        self._arrow_head_spin.setVisible(show_arrow_head)
        self._arrow_dir_label.setVisible(show_arrow_head)
        for b in self._arrow_dir_btns.values():
            b.setVisible(show_arrow_head)
        show_para_orient = mode == "parallelogram"
        self._para_orient_label.setVisible(show_para_orient)
        for b in self._para_orient_btns.values():
            b.setVisible(show_para_orient)
        show_callout_tail = mode == "callout"
        self._callout_tail_label.setVisible(show_callout_tail)
        self._callout_tail_spin.setVisible(show_callout_tail)
        show_radius = mode == "rectangle"
        self._corner_radius_label.setVisible(show_radius)
        self._corner_radius_spin.setVisible(show_radius)
        show_arc = mode == "circle"
        self._arc_start_label.setVisible(show_arc)
        self._arc_start_spin.setVisible(show_arc)
        self._arc_span_label.setVisible(show_arc)
        self._arc_span_spin.setVisible(show_arc)
        self._arc_pie_btn.setVisible(show_arc)
        self._donut_btn.setVisible(show_arc)
        self._donut_gap_label.setVisible(show_arc and self._donut_btn.isChecked())
        self._donut_gap_spin.setVisible(show_arc and self._donut_btn.isChecked())
        if mode == "star":
            self._corners_spin.setRange(4, 20)
            self._corners_spin.setValue(self.canvas.star_corners)
        elif mode == "ngon":
            self._corners_spin.setRange(4, 20)
            self._corners_spin.setValue(self.canvas.ngon_edges)

    def _set_arrow_dir(self, d):
        self.canvas.arrow_direction = d
        for k, b in self._arrow_dir_btns.items():
            b.setChecked(k == d)

    def _set_para_orient(self, orient):
        self.canvas.parallelogram_orientation = orient
        for k, b in self._para_orient_btns.items():
            b.setChecked(k == orient)

    def _set_tri_orient(self, orient):
        self.canvas.triangle_orientation = orient
        for o, b in self._tri_orient_btns.items():
            b.setChecked(o == orient)

    def _set_form_line_style(self, style):
        self.canvas.form_line_style = style
        for s, b in self._form_style_btns.items():
            b.setChecked(s == style)

    def _set_color_btn(self, btn, color):
        btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")

    def _on_text_box_toggled(self, v):
        self.canvas.text_box = v
        self.text_box_margin_label.setVisible(v)
        self.text_box_margin_spin.setVisible(v)
        self.text_box_style_label.setVisible(v)
        self.text_box_style_cb.setVisible(v)
        self.text_box_width_label.setVisible(v)
        self.text_box_width_spin.setVisible(v)
        self.canvas.update()

    def _make_pick_btn(self, text, slot):
        btn = QPushButton(text)
        btn.setFixedSize(20, 20)
        btn.clicked.connect(slot)
        return btn

    def _make_checkerboard_icon(self):
        pix = QPixmap(16, 16)
        pix.fill(Qt.white)
        p = QPainter(pix)
        p.fillRect(0, 0, 8, 8, QColor(180, 180, 180))
        p.fillRect(8, 8, 8, 8, QColor(180, 180, 180))
        p.end()
        return pix

    def _on_text_setting_changed(self, *_):
        self.canvas.text_str = self.text_input.text()
        self.canvas.text_box_margin = self.text_box_margin_spin.value()
        self.canvas.text_box_style = self.text_box_style_cb.currentText()
        self.canvas.text_box_width = self.text_box_width_spin.value()
        self.canvas.text_bg_transparent = self.text_bg_transp_btn.isChecked()
        self.canvas.update()

    def _update_text_font(self, *_):
        font = self.font_cb.currentFont()
        font.setPointSize(self.font_size_spin.value())
        font.setBold(self.bold_btn.isChecked())
        font.setItalic(self.italic_btn.isChecked())
        font.setUnderline(self.underline_btn.isChecked())
        self.canvas.text_font = font
        self.canvas.update()

    def _pick_text_color(self):
        c = self._pick_color(self.canvas.text_color)
        if c:
            self.canvas.text_color = c
            self._set_color_btn(self.text_color_btn, c)
            self.canvas.update()

    def _pick_text_bg_color(self):
        c = self._pick_color(self.canvas.text_bg_color)
        if c:
            self.canvas.text_bg_color = c
            self._set_color_btn(self.text_bg_color_btn, c)
            self.canvas.update()

    def _pick_text_box_color(self):
        c = self._pick_color(self.canvas.text_box_color)
        if c:
            self.canvas.text_box_color = c
            self._set_color_btn(self.text_box_color_btn, c)
            self.canvas.update()

    def _update_color_swatch(self, label, color):
        label.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")
        label.setFixedSize(16, 16)

    def _highlight_tool(self, tool):
        """Update toolbar checked state without switching canvas.tool (used by Alt-eyedropper)."""
        for name, action in self._tool_actions.items():
            action.setChecked(name == tool)
        if tool in self._tool_option_index:
            self._option_stack.setCurrentIndex(self._tool_option_index[tool])

    def _set_tool(self, tool):
        if tool in ("fill", "eraser", "spray"):
            self.canvas._flatten_selection()
        elif tool != "cut":
            self.canvas._cancel_cut()
        self.canvas.tool = tool
        if tool in ("pencil", "forms"):
            self.canvas._update_pen_cursor()
        elif tool != "text":
            self.canvas._text_cursor_pos = None
            self.canvas.update()
        for name, action in self._tool_actions.items():
            action.setChecked(name == tool)
        self._option_stack.setCurrentIndex(self._tool_option_index[tool])

    def _on_color_picked(self, color):
        self._picker_swatch.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")
        self._picker_rgb_label.setText(f"RGB: {color.red()}, {color.green()}, {color.blue()}")
        self.canvas.pen_color = color
        self.canvas.text_color = color
        self.canvas.fill_color = color
        self._set_color_btn(self.pen_color_btn, color)
        self._set_color_btn(self.form_pen_color_btn, color)
        self._set_color_btn(self._spray_color_btn, color)
        self._set_color_btn(self.text_color_btn, color)
        self._set_color_btn(self.fill_color_btn, color)
        self.canvas.update()

    def _on_color_picked2(self, color):
        self._picker_swatch2.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")
        self._picker_rgb_label2.setText(f"RGB: {color.red()}, {color.green()}, {color.blue()}")
        self.canvas.pen_color2 = color
        self.canvas.fill_color2 = color
        self._set_color_btn(self.pen_color2_btn, color)
        self._set_color_btn(self._spray_color2_btn, color)
        self._set_color_btn(self.fill_color2_btn, color)
        self.canvas.update()

    def _update_sel_dim(self, start, end):
        mode = self.canvas.cut_mode
        if mode == "circle":
            rad = int(math.hypot(end.x() - start.x(), end.y() - start.y()))
            self._cut_dim_label.setText(f"R: {rad}")
        else:
            r = self.canvas._sel_rubber_rect(start, end)
            self._cut_dim_label.setText(f"W:{r.width()}  H:{r.height()}")

    def _set_cut_mode(self, mode):
        self.canvas._cancel_cut()
        self.canvas.cut_mode = mode
        self._cut_rect_btn.setChecked(mode == "rectangle")
        self._cut_circ_btn.setChecked(mode == "circle")
        self._cut_ellipse_btn.setChecked(mode == "ellipse")
        self._cut_lasso_btn.setChecked(mode == "lasso")
        self._cut_wand_btn.setChecked(mode == "wand")

    def _set_cut_op(self, op):
        prev = self.canvas.cut_op
        if prev == op:
            return
        # switching between cut and copy while a floating pixmap exists: just update op
        if prev != "select" and op != "select" and self.canvas._cut_pixmap:
            if op == "copy":
                self.canvas._copy_source_pixmap = self.canvas._cut_pixmap.copy()
                if self.canvas._cut_rect:
                    self.canvas._selection_rect = QRect(self.canvas._cut_rect)
                if self.canvas.cut_mode == "lasso" and self.canvas._lasso_pts:
                    # offset _lasso_pts to current _cut_pos so origin outline matches _selection_rect
                    ox = self.canvas._cut_pos.x() - self.canvas._lasso_origin.x()
                    oy = self.canvas._cut_pos.y() - self.canvas._lasso_origin.y()
                    self.canvas._copy_lasso_pts = [(p[0] + ox, p[1] + oy) for p in self.canvas._lasso_pts]
            else:
                self.canvas._copy_source_pixmap = None
                self.canvas._copy_lasso_pts = []
        elif prev == "select" and op != "select" and self.canvas._selection_rect and not self.canvas._cut_pixmap:
            rect = self.canvas._selection_rect
            self.canvas._push_undo()
            self.canvas._cut_rect = rect
            self.canvas._cut_pos = rect.topLeft()
            self.canvas._cut_pixmap = QPixmap.fromImage(self.canvas.image.copy(rect))
            if self.canvas.cut_mode == "lasso" and self.canvas._copy_lasso_pts:
                self.canvas._lasso_pts = list(self.canvas._copy_lasso_pts)
                self.canvas._lasso_origin = rect.topLeft()
                poly = QPolygon([QPoint(p[0], p[1]) for p in self.canvas._copy_lasso_pts])
                mask_img = QImage(rect.size(), QImage.Format_ARGB32)
                mask_img.fill(Qt.transparent)
                mp = QPainter(mask_img)
                mp.setRenderHint(QPainter.Antialiasing, False)
                mp.translate(-rect.x(), -rect.y())
                mp.setBrush(Qt.black)
                mp.setPen(Qt.NoPen)
                mp.drawPolygon(poly)
                mp.end()
                mask_pix = QPixmap.fromImage(mask_img)
                self.canvas._cut_pixmap.setMask(mask_pix.createMaskFromColor(Qt.transparent))
            elif self.canvas.cut_mode in ("circle", "ellipse"):
                mask = QPixmap(rect.size())
                mask.fill(Qt.transparent)
                mp = QPainter(mask)
                mp.setRenderHint(QPainter.Antialiasing)
                mp.setBrush(Qt.black)
                mp.setPen(Qt.NoPen)
                mp.drawEllipse(mask.rect())
                mp.end()
                self.canvas._cut_pixmap.setMask(mask.createMaskFromColor(Qt.transparent))
            elif self.canvas.cut_mode == "wand" and self.canvas._wand_mask_img:
                mask_pix = QPixmap.fromImage(self.canvas._wand_mask_img)
                self.canvas._cut_pixmap.setMask(mask_pix.createMaskFromColor(Qt.transparent))
            self.canvas._cut_pixmap_base = self.canvas._cut_pixmap
            if op == "copy":
                self.canvas._copy_source_pixmap = self.canvas._cut_pixmap.copy()
            else:
                self.canvas._copy_source_pixmap = None
                for img in ([self.canvas.image, self.canvas._color_image] if self.canvas._color_image else [self.canvas.image]):
                    p = QPainter(img)
                    if self.canvas.cut_mode == "lasso" and self.canvas._lasso_pts:
                        p.setBrush(self.canvas.bg_color)
                        p.setPen(Qt.NoPen)
                        p.drawPolygon(QPolygon([QPoint(pt[0], pt[1]) for pt in self.canvas._lasso_pts]))
                    elif self.canvas.cut_mode in ("circle", "ellipse"):
                        p.setBrush(self.canvas.bg_color)
                        p.setPen(Qt.NoPen)
                        p.drawEllipse(rect)
                    elif self.canvas.cut_mode == "wand" and self.canvas._wand_mask_img:
                        ox, oy = rect.x(), rect.y()
                        for wy in range(self.canvas._wand_mask_img.height()):
                            for wx in range(self.canvas._wand_mask_img.width()):
                                if self.canvas._wand_mask_img.pixel(wx, wy) & 0xFF000000:
                                    p.fillRect(ox + wx, oy + wy, 1, 1, self.canvas.bg_color)
                    else:
                        p.fillRect(rect, self.canvas.bg_color)
                    p.end()
                if self.canvas._color_image:
                    self.canvas._sync_gray()
            self.canvas._mod()
            self.canvas.update()
        elif op == "select":
            self.canvas._cancel_cut()
            self.canvas._blink_timer.stop()
        elif prev == "select":
            self.canvas._cancel_cut()
        self.canvas.cut_op = op
        self._cut_op_sel_btn.setChecked(op == "select")
        self._cut_op_cut_btn.setChecked(op == "cut")
        self._cut_op_copy_btn.setChecked(op == "copy")

    def _on_cut_delete(self):
        from PyQt5.QtCore import Qt as _Qt
        from PyQt5.QtGui import QKeyEvent as _QKE
        ev = _QKE(_QKE.KeyPress, _Qt.Key_Delete, _Qt.NoModifier)
        self.canvas.keyPressEvent(ev)

    def _pick_color(self, current):
        palette = _build_palette(self.bit_depth)
        if palette:
            dlg = PaletteDialog(palette, current, self)
            if dlg.exec_():
                return dlg.selected
            return None
        c = QColorDialog.getColor(current, self)
        return c if c.isValid() else None

    def _pick_pen_color(self):
        c = self._pick_color(self.canvas.pen_color)
        if c:
            self.canvas.pen_color = c
            self._set_color_btn(self.pen_color_btn, c)
            self._set_color_btn(self.form_pen_color_btn, c)
            self._set_color_btn(self._spray_color_btn, c)
            self._push_color_history(c)
            self.canvas._update_pen_cursor()

    def _pick_pen_color2(self):
        c = self._pick_color(self.canvas.pen_color2)
        if c:
            self.canvas.pen_color2 = c
            self._set_color_btn(self.pen_color2_btn, c)
            self._set_color_btn(self._spray_color2_btn, c)
            self._push_color_history(c)

    def _pick_fill_color(self):
        c = self._pick_color(self.canvas.fill_color)
        if c:
            self.canvas.fill_color = c
            self._set_color_btn(self.fill_color_btn, c)

    def _pick_fill_color2(self):
        c = self._pick_color(self.canvas.fill_color2)
        if c:
            self.canvas.fill_color2 = c
            self._set_color_btn(self.fill_color2_btn, c)

    def _pick_form_fill_color(self):
        c = self._pick_color(self.canvas.form_fill_color)
        if c:
            self.canvas.form_fill_color = c
            self._set_color_btn(self.form_fill_color_btn, c)

    def _pick_bg_color(self):
        c = self._pick_color(self.canvas.bg_color)
        if c:
            old = self.canvas.bg_color
            self.canvas.bg_color = c
            self.canvas._replace_color(old, c)
            self._set_color_btn(self.bg_color_btn, c)

    @staticmethod
    def _nearest_color(color, palette):
        r, g, b = color.red(), color.green(), color.blue()
        return min(palette, key=lambda c: (c.red()-r)**2 + (c.green()-g)**2 + (c.blue()-b)**2)

    def _depth_changed(self, text):
        self.bit_depth = BIT_DEPTHS[text]

    def _settings_path(self):
        import os
        return os.path.join(_app_dir(), "simpledraw.settings")

    def _save_settings(self):
        import os
        lines = [
            f"tool={self.canvas.tool}",
            f"pen_width={self.canvas.pen_width}",
            f"pen_width2={self.canvas.pen_width2}",
            f"pen_color={self.canvas.pen_color.name()}",
            f"pen_color2={self.canvas.pen_color2.name()}",
            f"fill_tolerance={self.canvas.fill_tolerance}",
            f"fill_tolerance2={self.canvas.fill_tolerance2}",
            f"fill_color={self.canvas.fill_color.name()}",
            f"fill_color2={self.canvas.fill_color2.name()}",
            f"form_fill_color={self.canvas.form_fill_color.name()}",
            f"eraser_width={self.canvas.eraser_width}",
            f"spray_radius={self.canvas.spray_radius}",
            f"spray_density={self.canvas.spray_density}",
            f"spray_radius2={self.canvas.spray_radius2}",
            f"spray_density2={self.canvas.spray_density2}",
            f"pen_smooth1={self.canvas.pen_smooth1}",
            f"pen_smooth2={self.canvas.pen_smooth2}",
            f"pen_smooth_pct1={self.canvas.pen_smooth_pct1}",
            f"pen_smooth_pct2={self.canvas.pen_smooth_pct2}",
            f"pencil_line_smooth={self.canvas._pencil_line_smooth}",
            f"symmetry_h={self.canvas.symmetry_h}",
            f"symmetry_v={self.canvas.symmetry_v}",
            f"pencil_bezier={self.canvas.pencil_bezier}",
            f"pencil_bezier2={self.canvas.pencil_bezier2}",
            f"pen_type1={self.canvas.pen_type1}",
            f"pen_type2={self.canvas.pen_type2}",
            f"pen_intensity1={self.canvas.pen_intensity1}",
            f"pen_intensity2={self.canvas.pen_intensity2}",
            f"form_mode={self.canvas.form_mode}",
            f"form_line_style={self.canvas.form_line_style}",
            f"form_fill_transparent={self.canvas.form_fill_transparent}",
            f"form_antialias={self.canvas.form_antialias}",
            f"rect_corner_radius={self.canvas.rect_corner_radius}",
            f"circle_start_angle={self.canvas.circle_start_angle}",
            f"circle_span_angle={self.canvas.circle_span_angle}",
            f"circle_pie_mode={self.canvas.circle_pie_mode}",
            f"circle_donut={self.canvas.circle_donut}",
            f"donut_gap={self.canvas.donut_gap}",
            f"arrow_head_size={self.canvas.arrow_head_size}",
            f"arrow_direction={self.canvas.arrow_direction}",
            f"triangle_orientation={self.canvas.triangle_orientation}",
            f"triangle_perpendicular={self.canvas.triangle_perpendicular}",
            f"trapezoid_flip={self.canvas.trapezoid_flip}",
            f"parallelogram_orientation={self.canvas.parallelogram_orientation}",
            f"callout_tail_pos={self.canvas.callout_tail_pos}",
            f"star_corners={self.canvas.star_corners}",
            f"ngon_edges={self.canvas.ngon_edges}",
            f"line_arrow_start={self.canvas.line_arrow_start}",
            f"line_arrow_end={self.canvas.line_arrow_end}",
            f"line_arrow_inward={self.canvas.line_arrow_inward}",
            f"text_font_family={self.canvas.text_font.family()}",
            f"text_font_size={self.canvas.text_font.pointSize()}",
            f"text_font_bold={self.canvas.text_font.bold()}",
            f"text_font_italic={self.canvas.text_font.italic()}",
            f"text_font_underline={self.canvas.text_font.underline()}",
            f"text_color={self.canvas.text_color.name()}",
            f"text_bg_color={self.canvas.text_bg_color.name()}",
            f"text_bg_transparent={self.canvas.text_bg_transparent}",
            f"text_box={self.canvas.text_box}",
            f"text_box_color={self.canvas.text_box_color.name()}",
            f"text_box_margin={self.canvas.text_box_margin}",
            f"text_box_style={self.canvas.text_box_style}",
            f"text_box_width={self.canvas.text_box_width}",
            f"text_antialias={self.canvas.text_antialias}",
            f"text_str={self.canvas.text_str}",
            f"cut_mode={self.canvas.cut_mode}",
            f"cut_op={self.canvas.cut_op}",
            f"selection_resize_enabled={self.canvas.selection_resize_enabled}",
            f"picker_sample_radius={self.canvas.picker_sample_radius}",
            f"picker_sample_radius2={self.canvas.picker_sample_radius2}",
            f"bg_color={self.canvas.bg_color.name()}",
            f"palette={self.depth_cb.currentText()}",
            f"color_history={','.join(c.name() for c in self.canvas._color_history)}",
            f"theme={getattr(self, '_theme', 'light')}",
            f"recent_files={'|'.join(self._recent_files)}",
            f"autosave_interval={self._autosave_interval}",
        ]
        for action_name, action in getattr(self, '_shortcut_actions', {}).items():
            sc = action.shortcut().toString()
            if sc:
                lines.append(f"shortcut_{action_name}={sc}")
        try:
            with open(self._settings_path(), "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass

    def _load_settings(self):
        import os
        path = self._settings_path()
        if not os.path.exists(path):
            return
        cfg = {}
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line:
                        k, v = line.split("=", 1)
                        cfg[k.strip()] = v.strip()
        except Exception:
            return
        if "tool" in cfg and cfg["tool"] in self._tool_option_index:
            self._set_tool(cfg["tool"])
        if "pen_width" in cfg:
            try:
                v = int(cfg["pen_width"])
                self.canvas.pen_width = v
                self.width_spin.setValue(v)
                self.form_width_spin.setValue(v)
            except ValueError:
                pass
        if "pen_width2" in cfg:
            try:
                v = int(cfg["pen_width2"])
                self.canvas.pen_width2 = v
                self.width_spin2.setValue(v)
            except ValueError:
                pass
        if "pen_color" in cfg:
            c = QColor(cfg["pen_color"])
            if c.isValid():
                self.canvas.pen_color = c
                self._set_color_btn(self.pen_color_btn, c)
                self._set_color_btn(self.form_pen_color_btn, c)
                self._set_color_btn(self._spray_color_btn, c)
                self.canvas._update_pen_cursor()
        if "pen_color2" in cfg:
            c = QColor(cfg["pen_color2"])
            if c.isValid():
                self.canvas.pen_color2 = c
                self._set_color_btn(self.pen_color2_btn, c)
                self._set_color_btn(self._spray_color2_btn, c)
        if "fill_tolerance2" in cfg:
            try:
                v = int(cfg["fill_tolerance2"])
                self.canvas.fill_tolerance2 = v
                self._fill_tol2_spin.setValue(v)
            except Exception:
                pass
        if "fill_tolerance" in cfg:
            try:
                v = int(cfg["fill_tolerance"])
                self.canvas.fill_tolerance = v
                self._fill_tol_spin.setValue(v)
            except Exception:
                pass
        if "fill_color" in cfg:
            c = QColor(cfg["fill_color"])
            if c.isValid():
                self.canvas.fill_color = c
                self._set_color_btn(self.fill_color_btn, c)
        if "fill_color2" in cfg:
            c = QColor(cfg["fill_color2"])
            if c.isValid():
                self.canvas.fill_color2 = c
                self._set_color_btn(self.fill_color2_btn, c)
        if "form_fill_color" in cfg:
            c = QColor(cfg["form_fill_color"])
            if c.isValid():
                self.canvas.form_fill_color = c
                self._set_color_btn(self.form_fill_color_btn, c)
        if "eraser_width" in cfg:
            try:
                v = int(cfg["eraser_width"])
                self.canvas.eraser_width = v
                self.eraser_spin.setValue(v)
            except ValueError:
                pass
        if "spray_radius" in cfg:
            try:
                v = int(cfg["spray_radius"])
                self.canvas.spray_radius = v
                self._spray_radius_spin.setValue(v)
            except ValueError:
                pass
        if "spray_density" in cfg:
            try:
                v = int(cfg["spray_density"])
                self.canvas.spray_density = v
                self._spray_density_spin.setValue(v)
            except ValueError:
                pass
        if "spray_radius2" in cfg:
            try:
                v = int(cfg["spray_radius2"])
                self.canvas.spray_radius2 = v
                self._spray_radius2_spin.setValue(v)
            except ValueError:
                pass
        if "spray_density2" in cfg:
            try:
                v = int(cfg["spray_density2"])
                self.canvas.spray_density2 = v
                self._spray_density2_spin.setValue(v)
            except ValueError:
                pass
        for _k, _attr, _widget, _type in [
            ("pen_smooth_pct1",  "pen_smooth_pct1",  "pen_smooth_pct1_spin",  int),
            ("pen_smooth_pct2",  "pen_smooth_pct2",  "pen_smooth_pct2_spin",  int),
            ("pencil_line_smooth","_pencil_line_smooth","_line_smooth_spin",  int),
            ("pen_intensity1",   "pen_intensity1",   "_pen_intensity1_spin",  int),
            ("pen_intensity2",   "pen_intensity2",   "_pen_intensity2_spin",  int),
            ("rect_corner_radius","rect_corner_radius","_corner_radius_spin", int),
            ("circle_start_angle","circle_start_angle","_arc_start_spin",    int),
            ("circle_span_angle","circle_span_angle", "_arc_span_spin",      int),
            ("donut_gap",        "donut_gap",         "_donut_gap_spin",      int),
            ("arrow_head_size",  "arrow_head_size",   "_arrow_head_spin",     int),
            ("star_corners",     "star_corners",      "_corners_spin",        int),
            ("ngon_edges",       "ngon_edges",        "_corners_spin",        int),
            ("text_font_size",   None,                "font_size_spin",       int),
            ("text_box_margin",  "text_box_margin",   "text_box_margin_spin", int),
            ("text_box_width",   "text_box_width",    "text_box_width_spin",  int),
            ("picker_sample_radius","picker_sample_radius","_picker_sample_spin",int),
            ("picker_sample_radius2","picker_sample_radius2","_picker_sample_spin2",int),
        ]:
            if _k in cfg:
                try:
                    v = _type(cfg[_k])
                    if _attr: setattr(self.canvas, _attr, v)
                    getattr(self, _widget).setValue(v)
                except Exception: pass
        for _k, _attr, _widget in [
            ("pen_smooth1",  "pen_smooth1",  "pen_smooth1_btn"),
            ("pen_smooth2",  "pen_smooth2",  "pen_smooth2_btn"),
            ("symmetry_h",   "symmetry_h",   "_sym_h_btn"),
            ("symmetry_v",   "symmetry_v",   "_sym_v_btn"),
            ("pencil_bezier","pencil_bezier","_bezier_btn"),
            ("pencil_bezier2","pencil_bezier2","_bezier_btn2"),
            ("form_fill_transparent","form_fill_transparent","form_fill_transp_btn"),
            ("form_antialias","form_antialias","_form_aa_btn"),
            ("circle_pie_mode","circle_pie_mode","_arc_pie_btn"),
            ("circle_donut",  "circle_donut", "_donut_btn"),
            ("triangle_perpendicular","triangle_perpendicular","_tri_perp_btn"),
            ("trapezoid_flip","trapezoid_flip","_trap_flip_btn"),
            ("line_arrow_start","line_arrow_start","_line_arrow_start_btn"),
            ("line_arrow_end","line_arrow_end","_line_arrow_end_btn"),
            ("line_arrow_inward","line_arrow_inward","_line_arrow_inward_btn"),
            ("text_bg_transparent","text_bg_transparent","text_bg_transp_btn"),
            ("text_antialias","text_antialias","_text_aa_btn"),
            ("selection_resize_enabled","selection_resize_enabled","_cut_resize_btn"),
            ("text_font_bold",  None, "bold_btn"),
            ("text_font_italic",None, "italic_btn"),
            ("text_font_underline",None,"underline_btn"),
        ]:
            if _k in cfg:
                try:
                    v = cfg[_k].lower() == "true"
                    if _attr: setattr(self.canvas, _attr, v)
                    getattr(self, _widget).setChecked(v)
                except Exception: pass
        for _k, _attr, _widget, _items in [
            ("pen_type1",  "pen_type1",  "_pen_type1_cb",  None),
            ("pen_type2",  "pen_type2",  "_pen_type2_cb",  None),
            ("text_box_style","text_box_style","text_box_style_cb",None),
        ]:
            if _k in cfg:
                try:
                    getattr(self, _widget).setCurrentText(cfg[_k])
                    if _attr: setattr(self.canvas, _attr, cfg[_k])
                except Exception: pass
        if "pen_smooth1" in cfg or "pen_smooth2" in cfg:
            self._on_pencil_smooth_toggled(None)
        if "callout_tail_pos" in cfg:
            try:
                v = float(cfg["callout_tail_pos"])
                self.canvas.callout_tail_pos = v
                self._callout_tail_spin.setValue(int(v * 100))
            except Exception: pass
        if "form_mode" in cfg:
            try: self._set_form_mode(cfg["form_mode"])
            except Exception: pass
        if "form_line_style" in cfg:
            try: self._set_form_line_style(cfg["form_line_style"])
            except Exception: pass
        if "arrow_direction" in cfg:
            try: self._set_arrow_dir(cfg["arrow_direction"])
            except Exception: pass
        if "triangle_orientation" in cfg:
            try: self._set_tri_orient(cfg["triangle_orientation"])
            except Exception: pass
        if "parallelogram_orientation" in cfg:
            try: self._set_para_orient(cfg["parallelogram_orientation"])
            except Exception: pass
        if "cut_mode" in cfg:
            try: self._set_cut_mode(cfg["cut_mode"])
            except Exception: pass
        if "cut_op" in cfg:
            try: self._set_cut_op(cfg["cut_op"])
            except Exception: pass
        if "text_font_family" in cfg or "text_font_size" in cfg:
            try: self._update_text_font()
            except Exception: pass
        if "text_box" in cfg:
            try:
                v = cfg["text_box"].lower() == "true"
                self.text_box_cb.setChecked(v)
            except Exception: pass
        if "text_str" in cfg:
            try:
                self.text_input.setText(cfg["text_str"])
            except Exception: pass
        for _k, _attr, _btn in [
            ("text_color",     "text_color",     "text_color_btn"),
            ("text_bg_color",  "text_bg_color",  "text_bg_color_btn"),
            ("text_box_color", "text_box_color", "text_box_color_btn"),
        ]:
            if _k in cfg:
                c = QColor(cfg[_k])
                if c.isValid():
                    setattr(self.canvas, _attr, c)
                    self._set_color_btn(getattr(self, _btn), c)
        if "font_size_spin" in dir(self):
            try: self._update_text_font()
            except Exception: pass
        if "bg_color" in cfg:
            c = QColor(cfg["bg_color"])
            if c.isValid():
                self.canvas.bg_color = c
                self.canvas.image.fill(c)
                self._set_color_btn(self.bg_color_btn, c)
        if "palette" in cfg and cfg["palette"] in BIT_DEPTHS:
            self.depth_cb.setCurrentText(cfg["palette"])
        if "color_history" in cfg and cfg["color_history"]:
            for hex_val in cfg["color_history"].split(","):
                c = QColor(hex_val.strip())
                if c.isValid():
                    self.canvas._color_history.append(c)
            for i, btn in enumerate(self._color_history_btns):
                if i < len(self.canvas._color_history):
                    c = self.canvas._color_history[i]
                    btn.setStyleSheet(f"background-color: {c.name()}; border: 1px solid #888;")
                    btn.setVisible(True)
        if "theme" in cfg:
            self._apply_theme(cfg["theme"])
        if "recent_files" in cfg and cfg["recent_files"]:
            for p in reversed(cfg["recent_files"].split("|")):
                p = p.strip()
                if p:
                    self._add_recent(p)
        if "autosave_interval" in cfg:
            try:
                v = int(cfg["autosave_interval"])
                self._autosave_interval = max(0, v)
                if self._autosave_interval > 0:
                    self._autosave_timer.start(self._autosave_interval * 60 * 1000)
            except ValueError:
                pass
        for k, v in cfg.items():
            if k.startswith("shortcut_"):
                action_name = k[len("shortcut_"):]
                actions = getattr(self, '_shortcut_actions', {})
                if action_name in actions:
                    actions[action_name].setShortcut(v)

    def closeEvent(self, event):
        if self._ask_save_if_needed():
            self._save_settings()
            event.accept()
        else:
            event.ignore()

    def _new_file(self):
        if not self._ask_save_if_needed():
            return
        dlg = SizeDialog(800, 600, self)
        if not dlg.exec_():
            return
        w, h = dlg.wSpin.value(), dlg.hSpin.value()
        self.canvas._cancel_cut()
        self.canvas._emit_modified = False
        self.canvas.image = QImage(w, h, QImage.Format_ARGB32)
        self.canvas.image.fill(self.canvas.bg_color)
        self._fit_canvas()
        self.canvas.update()
        self.canvas._emit_modified = True
        self._update_size_label()
        self.current_file = "new_picture.bmp"
        self._modified = False
        self._update_title()

    def _open_file(self):
        if not self._ask_save_if_needed():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open", "",
            "Images (*.bmp *.png *.jpg *.jpeg *.tiff *.webp);;All Files (*)")
        if path:
            self._open_path(path)
        if path:
            img = QImage(path)
            if not img.isNull():
                self.canvas._cancel_cut()
                self.canvas._emit_modified = False
                self.canvas.image = img.convertToFormat(QImage.Format_ARGB32)
                self._fit_canvas()
                self.canvas.update()
                self.canvas._emit_modified = True
                self.current_file = path
                self._modified = False
                self._update_title()
                self._update_size_label()
                self._add_recent(path)

    def _save_file(self):
        if self.current_file and self.current_file != "new_picture.bmp":
            self._do_save(self.current_file)
            return True
        return self._save_as()

    def _save_as(self):
        import os
        default = os.path.splitext(self.current_file)[0] if self.current_file else "new_picture"
        path, _ = QFileDialog.getSaveFileName(self, "Save As", default, "Bitmap (*.bmp);;PNG (*.png);;JPEG (*.jpg)")
        if path:
            self._do_save(path)
            self.current_file = path
            return True
        return False

    def _do_save(self, path):
        fmt = QT_FORMATS.get(self.bit_depth, QImage.Format_ARGB32)
        img = self.canvas.image.convertToFormat(fmt)
        if img.save(path):
            self.current_file = path
            self._modified = False
            self._update_title()
            self._add_recent(path)
        else:
            QMessageBox.warning(self, "Save Failed", f"Could not save to {path}")

    def _edit_size(self):
        dlg = SizeDialog(self.canvas.image.width(), self.canvas.image.height(), self)
        if dlg.exec_():
            self.canvas.resize_canvas(dlg.wSpin.value(), dlg.hSpin.value())
            self._update_size_label()
            self._fit_canvas()
            self.canvas.update()

    def _toggle_grayscale(self):
        self.canvas.apply_effect("Grayscale")
        self.recorder.record("canvas.apply_effect('grayscale')")
        is_gray = self.canvas._color_image is None
        self._grayscale_action.setText("Grayscale" if is_gray else "→ Color")

    def _effect_with_dialog(self, title, slider_specs, apply_fn, last_attr):
        if self._effect_origin_image is None:
            self._effect_origin_image = self.canvas.image.copy()
            self._effect_origin_cut   = self.canvas._cut_pixmap.copy() if self.canvas._cut_pixmap else None
            self._effect_origin_color = self.canvas._color_image.copy() if self.canvas._color_image else None
        self.canvas._push_undo()
        self._effect_dialog_open = True

        def restore():
            self.canvas.image = self._effect_origin_image.copy()
            if self._effect_origin_cut:
                self.canvas._cut_pixmap = self._effect_origin_cut.copy()
                self.canvas._cut_pixmap_base = self.canvas._cut_pixmap
            else:
                self.canvas._cut_pixmap = None
                self.canvas._cut_pixmap_base = None
            self.canvas._color_image = self._effect_origin_color.copy() if self._effect_origin_color else None

        def apply_cb(*values):
            restore()
            apply_fn(*values)

        dlg = _SliderDialog(title, slider_specs, apply_cb, self)
        if dlg.exec_():
            committed = dlg.committed()
            setattr(self, last_attr, committed[0] if len(committed) == 1 else tuple(committed))
            self._effect_origin_image = None
            self._effect_origin_cut   = None
            self._effect_origin_color = None
            _ename = title.lower().replace(" ", "_").replace("/", "_")
            if len(committed) == 1:
                _evals = str(committed[0])
            else:
                _knames = [s[0].lower().replace(' ', '_').replace('/', '_') for s in slider_specs]
                _evals = ", ".join(f"{k}={v}" for k, v in zip(_knames, committed))
            self.recorder.record(f"canvas.apply_effect({_ename!r}, {_evals})")
        else:
            restore()
            if self.canvas._undo_stack:
                self.canvas._undo_stack.pop()
            self.canvas.update()
        self._effect_dialog_open = False

    def _smooth_with_dialog(self):
        self._effect_with_dialog(
            "Smooth",
            [("Radius", 1, 20, 1)],
            lambda v: self.canvas.apply_effect("Smooth", v),
            "_last_smooth_value"
        )

    def _colorfade_with_dialog(self):
        if self._effect_origin_image is None:
            self._effect_origin_image = self.canvas.image.copy()
            self._effect_origin_cut   = self.canvas._cut_pixmap.copy() if self.canvas._cut_pixmap else None
            self._effect_origin_color = self.canvas._color_image.copy() if self.canvas._color_image else None
        self.canvas._push_undo()
        self._effect_dialog_open = True

        def restore():
            self.canvas.image = self._effect_origin_image.copy()
            if self._effect_origin_cut:
                self.canvas._cut_pixmap = self._effect_origin_cut.copy()
                self.canvas._cut_pixmap_base = self.canvas._cut_pixmap
            else:
                self.canvas._cut_pixmap = None
                self.canvas._cut_pixmap_base = None
            self.canvas._color_image = self._effect_origin_color.copy() if self._effect_origin_color else None

        def apply_cb(ca, cb, orient):
            restore()
            self.canvas.apply_colorfade(ca, cb, orient)

        dlg = _ColorFadeDialog(apply_cb, self._pick_color, self)
        if dlg.exec_():
            self._effect_origin_image = None
            self._effect_origin_cut   = None
            self._effect_origin_color = None
            ca, cb, orient = dlg.committed()
            self.recorder.record(
                f"canvas.apply_effect('color_fade', color_a=__{ca.name()}__, color_b=__{cb.name()}__, orient={orient})")
        else:
            restore()
            if self.canvas._undo_stack:
                self.canvas._undo_stack.pop()
            self.canvas.update()
        self._effect_dialog_open = False

    def _toggle_grid(self, checked):
        self.canvas._grid_visible = checked
        self.canvas.update()

    def _grid_settings(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Grid Settings")
        layout = QFormLayout(dlg)
        w_spin = QSpinBox()
        w_spin.setRange(1, 9999)
        w_spin.setValue(self.canvas._grid_w)
        h_spin = QSpinBox()
        h_spin.setRange(1, 9999)
        h_spin.setValue(self.canvas._grid_h)
        layout.addRow("Cell Width (px):", w_spin)
        layout.addRow("Cell Height (px):", h_spin)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addRow(btns)
        if dlg.exec_():
            self.canvas._grid_w = w_spin.value()
            self.canvas._grid_h = h_spin.value()
            self.canvas.update()

    def _copy_selection_to_clipboard(self):
        if self.canvas._cut_pixmap:
            QApplication.clipboard().setPixmap(self.canvas._cut_pixmap)
        elif self.canvas._selection_rect:
            region = self.canvas.image.copy(self.canvas._selection_rect)
            QApplication.clipboard().setImage(region)
        else:
            QApplication.clipboard().setImage(self.canvas.image)

    def _copy_canvas_to_clipboard(self):
        QApplication.clipboard().setImage(self.canvas.image)

    def _paste_from_clipboard(self):
        from PyQt5.QtWidgets import QApplication
        mime = QApplication.clipboard().mimeData()
        img = QImage()
        for fmt, hint in [("image/png", "PNG"), ("image/bmp", "BMP"),
                          ("image/jpeg", "JPEG"), ("image/tiff", "TIFF")]:
            if mime.hasFormat(fmt):
                img.loadFromData(mime.data(fmt), hint)
                if not img.isNull():
                    break
        if img.isNull():
            img = QApplication.clipboard().image()
        if img.isNull():
            return
        img.setDevicePixelRatio(1.0)
        pix = QPixmap.fromImage(img.convertToFormat(QImage.Format_ARGB32))
        pix.setDevicePixelRatio(1.0)
        cw, ch = self.canvas.image.width(), self.canvas.image.height()
        pw, ph = pix.width(), pix.height()
        if pw != cw or ph != ch:
            mb = QMessageBox(self)
            mb.setWindowTitle("Paste")
            mb.setText(f"Clipboard image is {pw}\u00d7{ph}, canvas is {cw}\u00d7{ch}.")
            btn_resize  = mb.addButton("Resize Canvas", QMessageBox.AcceptRole)
            btn_new     = mb.addButton("Paste as New",  QMessageBox.ActionRole)
            btn_paste   = mb.addButton("Paste Anyway",  QMessageBox.NoRole)
            mb.addButton(QMessageBox.Cancel)
            mb.exec_()
            clicked = mb.clickedButton()
            if clicked is None or clicked == mb.button(QMessageBox.Cancel):
                return
            if clicked == btn_new:
                self._paste_as_new_canvas(img)
                return
            if clicked == btn_resize:
                self.canvas.resize_canvas(pw, ph)
                self._update_size_label()
                self._fit_canvas()
        self._set_tool("cut")
        self.canvas._push_undo()
        self.canvas._cut_pixmap = pix
        self.canvas._cut_pixmap_base = pix
        self.canvas._cut_pos = QPoint(0, 0)
        self.canvas._cut_rect = QRect(QPoint(0, 0), pix.size())
        self.canvas._selection_rect = self.canvas._cut_rect
        self.canvas._zoom = 1.0
        self.canvas._zoom_base = 1.0
        self._zoom_label.setText("100%")
        self._center_canvas()
        self.canvas._march_timer.start(100)
        self.canvas._blink_timer.start(500)
        self.canvas.update()

    def _paste_as_new_canvas(self, img):
        if not self._ask_save_if_needed():
            return
        self.canvas._cancel_cut()
        self.canvas._emit_modified = False
        self.canvas.image = img.convertToFormat(QImage.Format_ARGB32)
        self._fit_canvas()
        self.canvas._zoom = 1.0
        self.canvas._zoom_base = 1.0
        self._zoom_label.setText("100%")
        self._center_canvas()
        self.canvas.update()
        self.canvas._emit_modified = True
        self.current_file = "new_picture.bmp"
        self._modified = True
        self._update_title()
        self._update_size_label()

    def _edit_effects(self):
        dlg = EffectsDialog(self)
        if dlg.exec_():
            eff = dlg.effect.currentText(); rad = dlg.smooth_radius.value()
            self.canvas.apply_effect(eff, rad)
            self.recorder.record(f"canvas.apply_effect({eff.lower().replace(' ','_')!r}, {rad})")

    def _open_scripts(self):
        if not hasattr(self, '_script_window') or not self._script_window.isVisible():
            self._script_window = ScriptWindow(self)
        self._script_window.show()
        self._script_window.raise_()
        self._script_window.activateWindow()


class MacroRecorder:
    """Records canvas operations and emits a runnable Python script."""
    def __init__(self):
        self._lines = []
        self.active = False

    def start(self, width=None, height=None, bg=None):
        self._lines = []
        self._width = width
        self._height = height
        self._bg = bg
        self.active = True

    def stop(self):
        self.active = False

    def record(self, line):
        if self.active:
            self._lines.append(line)

    def cancel_last_selection(self):
        if self._lines and self._lines[-1].startswith("canvas.set_selection("):
            self._lines.pop()
        elif self._lines and any(l.startswith("canvas.set_selection(") for l in self._lines):
            self._lines.append("canvas.deselect()")

    def script(self):
        if not self._lines:
            return "# empty recording\n"
        import re
        colors = {}
        def color_var(hex_str):
            if hex_str not in colors:
                colors[hex_str] = f"c{len(colors) + 1}"
            return colors[hex_str]
        # lines store hex as __#rrggbb__ markers (no quotes) for clean substitution
        resolved = []
        for line in self._lines:
            def repl(m):
                return color_var(m.group(1))
            resolved.append(re.sub(r"__([#][0-9a-fA-F]{6})__", repl, line))
        header = ["# Recorded macro"]
        header += [f"{v} = '{k}'" for k, v in colors.items()]
        if colors:
            header.append("")
        if self._width and self._height:
            header.append(f"canvas.set_size({self._width}, {self._height})")
        if self._bg:
            r, g, b = self._bg
            header.append(f"canvas.set_background_color({r}, {g}, {b})")
        header.append("canvas.clear()")
        header.append("canvas.push_undo()")
        return "\n".join(header + resolved + ["canvas.commit()\n"])


class ScriptAPI:
    """Interface exposed to macro scripts as the 'canvas' object."""
    def __init__(self, main_window):
        self._mw = main_window
        self._c  = main_window.canvas
        self._stopped = False
        self._ghost = None       # lazy-created ghost QImage

    def _check(self):
        if self._stopped:
            raise InterruptedError("Script stopped by user.")

    def _img(self, ghost=False):
        if ghost:
            if self._ghost is None:
                w, h = self._c.image.width(), self._c.image.height()
                self._ghost = QImage(w, h, QImage.Format_ARGB32)
                self._ghost.fill(Qt.transparent)
            return self._ghost
        return self._c.image

    def _scripts_dir(self):
        return os.path.join(_app_dir(), 'scripts')

    def _to_qcolor(self, c):
        if c is None: return None
        if isinstance(c, QColor): return QColor(c)
        if isinstance(c, (list, tuple)): return QColor(*[int(v) for v in c])
        return QColor(c)

    # --- color depth ---
    def set_color_depth(self, depth):
        """Set canvas color depth. depth: 1, 2, 4, 8, 16, 24, or 32."""
        self._check()
        key = f"{int(depth)}-bit"
        if key not in BIT_DEPTHS:
            raise ValueError(f"Invalid depth {depth}. Use 1,2,4,8,16,24,32.")
        self._mw.depth_cb.setCurrentText(key)

    def get_color_depth(self):
        """Return current color depth as an integer."""
        return self._mw.bit_depth

    # --- canvas size ---
    def get_size(self, ghost=False):
        img = self._img(ghost)
        return (img.width(), img.height())

    def set_size(self, width, height):
        self._check()
        self._c.resize_canvas(int(width), int(height))
        self._mw._update_size_label()
        self._mw._fit_canvas()

    # --- clear ---
    def clear(self, ghost=False):
        self._check()
        img = self._img(ghost)
        if ghost:
            img.fill(Qt.transparent)
        else:
            img.fill(self._c.bg_color)
            self._c.update()

    # --- cursor position ---
    def get_cursor_pos(self):
        pos = self._c._to_canvas_pos(self._c.mapFromGlobal(self._c.cursor().pos()))
        w, h = self._c.image.width(), self._c.image.height()
        if 0 <= pos.x() < w and 0 <= pos.y() < h:
            return (pos.x(), pos.y())
        return -1

    def set_cursor_pos(self, x, y):
        x, y = int(x), int(y)
        w, h = self._c.image.width(), self._c.image.height()
        if not (0 <= x < w and 0 <= y < h):
            return -1
        from PyQt5.QtGui import QCursor
        wx = int(x * self._c._zoom + self._c._offset.x())
        wy = int(y * self._c._zoom + self._c._offset.y())
        QCursor.setPos(self._c.mapToGlobal(QPoint(wx, wy)))
        return (x, y)

    # --- background color ---
    def get_background_color(self):
        c = self._c.bg_color
        return (c.red(), c.green(), c.blue())

    def set_background_color(self, r, g, b):
        self._c.bg_color = QColor(int(r), int(g), int(b))
        self._mw._set_color_btn(self._mw.bg_color_btn, self._c.bg_color)

    # --- get color at position ---
    def get_color(self, pos, tolerance=0, ghost=False):
        """Returns (r,g,b) at canvas position (x,y). tolerance averages nearby pixels."""
        x, y = int(pos[0]), int(pos[1])
        img = self._img(ghost)
        w, h = img.width(), img.height()
        if not (0 <= x < w and 0 <= y < h):
            return -1
        if tolerance <= 0:
            c = QColor(img.pixel(x, y))
            return (c.red(), c.green(), c.blue())
        r_sum = g_sum = b_sum = count = 0
        for dy in range(-tolerance, tolerance + 1):
            for dx in range(-tolerance, tolerance + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    c = QColor(img.pixel(nx, ny))
                    r_sum += c.red(); g_sum += c.green(); b_sum += c.blue()
                    count += 1
        return (r_sum // count, g_sum // count, b_sum // count) if count else -1

    # --- draw at position ---
    def draw(self, pos, channel=1, color=None, ghost=False):
        """Draw a single point at canvas position (x,y)."""
        self._check()
        x, y = int(pos[0]), int(pos[1])
        img = self._img(ghost)
        if not (0 <= x < img.width() and 0 <= y < img.height()):
            return -1
        color = self._to_qcolor(color) or (self._c.pen_color if channel == 1 else self._c.pen_color2)
        width = self._c.pen_width if channel == 1 else self._c.pen_width2
        p = QPainter(img)
        p.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPoint(x, y)
        p.end()
        return (x, y)

    # --- fill ---
    def fill(self, pos, color=None, tolerance=0):
        """Flood-fill at pos (x,y) with color and optional tolerance."""
        self._check()
        c = self._c
        fill_c = self._to_qcolor(color) or c.fill_color
        saved_tol = c.fill_tolerance
        c.fill_tolerance = int(tolerance)
        c._push_undo()
        c._flood_fill(QPoint(int(pos[0]), int(pos[1])), fill_c, c._selection_rect)
        c.fill_tolerance = saved_tol

    # --- pen stroke ---
    def draw_stroke(self, points, width=1, color=None, pen_type='normal', intensity=100):
        """Draw a freehand polyline through a list of (x,y) points."""
        self._check()
        if len(points) < 2:
            return
        pen_c = self._to_qcolor(color) or self._c.pen_color
        prev_type1, prev_int1 = self._c.pen_type1, self._c.pen_intensity1
        prev_w = self._c.pen_width
        self._c.pen_type1 = pen_type
        self._c.pen_intensity1 = intensity
        self._c.pen_width = int(width)
        for i in range(1, len(points)):
            p0 = QPoint(int(points[i-1][0]), int(points[i-1][1]))
            p1 = QPoint(int(points[i][0]),   int(points[i][1]))
            self._c._draw_dot(p1, pen_c)
        self._c.pen_type1 = prev_type1
        self._c.pen_intensity1 = prev_int1
        self._c.pen_width = prev_w

    # --- spray ---
    def spray(self, pos, radius=20, density=30, color=None):
        """Spray random dots. pos can be (x,y) or a list of (x,y) points."""
        self._check()
        import random, math
        pen_c = self._to_qcolor(color) or self._c.pen_color
        img = self._c.image
        w, h = img.width(), img.height()
        p = QPainter(img)
        p.setPen(pen_c)
        pts = pos if isinstance(pos, list) else [pos]
        for pt in pts:
            cx, cy = int(pt[0]), int(pt[1])
            for _ in range(int(density)):
                angle = random.uniform(0, 2 * math.pi)
                r = random.uniform(0, int(radius))
                x, y = int(cx + r * math.cos(angle)), int(cy + r * math.sin(angle))
                if 0 <= x < w and 0 <= y < h:
                    p.drawPoint(x, y)
        p.end()

    # --- draw form ---
    def draw_form(self, form_type, pos1, pos2, width=1, color=None, fill_color=None,
                  transparent=False, corners=4, edges=5, ghost=False, antialias=False):
        """Draw a shape. pos1/pos2 are (x,y) tuples.
           form_type: 'line','rectangle','ellipse','circle','triangle','trapezoid',
                      'star','polygon','heart','lightning','arrow'
           corners: star points (star only)  edges: polygon sides (polygon only)
        """
        self._check()
        pen_c  = self._to_qcolor(color)      or self._c.pen_color
        fill_c = self._to_qcolor(fill_color) or self._c.form_fill_color
        x1, y1 = int(pos1[0]), int(pos1[1])
        if isinstance(pos2, (int, float)):
            r = int(pos2)
            start = QPoint(x1 - r, y1 - r)
            end   = QPoint(x1 + r, y1 + r)
        else:
            start = QPoint(x1, y1)
            end   = QPoint(int(pos2[0]), int(pos2[1]))
        img = self._img(ghost)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing, antialias)
        p.setPen(QPen(pen_c, int(width), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush if transparent else QBrush(fill_c))
        ft = str(form_type).lower()
        r = QRect(start, end).normalized()
        if ft == 'rectangle':
            p.drawRect(r)
        elif ft in ('ellipse', 'circle'):
            p.drawEllipse(r)
        elif ft == 'line':
            p.drawLine(start, end)
        elif ft == 'triangle':
            p.drawPolygon(QPolygon(self._c._triangle_pts(start, end)))
        elif ft == 'trapezoid':
            p.drawPolygon(QPolygon(self._c._trapezoid_pts(start, end)))
        elif ft == 'star':
            saved = self._c.star_corners
            self._c.star_corners = int(corners)
            p.drawPolygon(QPolygon(self._c._star_pts(start, end)))
            self._c.star_corners = saved
        elif ft in ('polygon', 'ngon'):
            saved = self._c.ngon_edges
            self._c.ngon_edges = int(edges)
            p.drawPolygon(QPolygon(self._c._ngon_pts(start, end)))
            self._c.ngon_edges = saved
        elif ft == 'heart':
            p.drawPath(self._c._heart_pts(start, end))
        elif ft == 'lightning':
            p.drawPolygon(QPolygon(self._c._lightning_pts(start, end)))
        elif ft == 'arrow':
            p.drawPolygon(QPolygon(self._c._arrow_shape_pts(start, end)))
        elif ft == 'cross':
            p.drawPolygon(QPolygon(self._c._cross_pts(start, end)))
        elif ft in ('callout', 'speechbubble'):
            p.drawPolygon(QPolygon(self._c._callout_pts(start, end)))
        elif ft == 'parallelogram':
            p.drawPolygon(QPolygon(self._c._parallelogram_pts(start, end)))
        p.end()

    # --- effects ---
    def apply_effect(self, effect, value=None, **kwargs):
        """Apply an effect to the canvas (respects active selection).
           effect: 'grayscale','invert','smooth','sharpen','emboss',
                   'brightness_contrast','saturation','noise','pixelate',
                   'posterize','vignette'
           kwargs: radius, brightness, contrast, value, block, levels, strength
        """
        self._check()
        e = str(effect).lower().replace(' ', '_').replace('/', '_')
        if value is not None:
            _vmap = {'smooth': 'radius', 'brightness_contrast': 'brightness',
                     'brightness': 'brightness', 'saturation': 'value',
                     'noise': 'value', 'pixelate': 'block',
                     'posterize': 'levels', 'vignette': 'strength'}
            kwargs.setdefault(_vmap.get(e, 'value'), value)
        c = self._c
        if e == 'grayscale':
            c.apply_effect('Grayscale')
        elif e == 'invert':
            c.apply_effect('Invert Colors')
        elif e == 'smooth':
            c.apply_effect('Smooth', kwargs.get('radius', 1))
        elif e == 'sharpen':
            c.apply_sharpen()
        elif e == 'emboss':
            c.apply_emboss()
        elif e in ('brightness_contrast', 'brightness'):
            c.apply_brightness_contrast(kwargs.get('brightness', 0), kwargs.get('contrast', 0))
        elif e == 'saturation':
            c.apply_saturation(kwargs.get('value', 0))
        elif e == 'noise':
            c.apply_noise(kwargs.get('value', 10))
        elif e == 'pixelate':
            c.apply_pixelate(kwargs.get('block', 8))
        elif e == 'posterize':
            c.apply_posterize(kwargs.get('levels', 4))
        elif e == 'vignette':
            c.apply_vignette(kwargs.get('strength', 100))
        elif e == 'flip_horizontal':
            c.flip_canvas(True)
        elif e == 'flip_vertical':
            c.flip_canvas(False)
        elif e == 'rotate_cw':
            c.rotate_canvas(True)
        elif e == 'rotate_ccw':
            c.rotate_canvas(False)
        elif e == 'color_fade':
            ca = self._to_qcolor(kwargs.get('color_a', '#000000'))
            cb = self._to_qcolor(kwargs.get('color_b', '#ffffff'))
            c.apply_colorfade(ca, cb, int(kwargs.get('orient', 0)))

    # --- ghost canvas ---
    def copy_to_ghost(self):
        """Copy the visible canvas into the ghost canvas."""
        self._ghost = self._c.image.copy()

    def copy_from_ghost(self):
        """Composite the ghost canvas onto the visible canvas."""
        self._check()
        if self._ghost is None:
            return
        p = QPainter(self._c.image)
        p.drawImage(0, 0, self._ghost)
        p.end()
        self._c.update()

    # --- file I/O (scripts folder only) ---
    def save_image(self, filename, ghost=False):
        """Save canvas (or ghost) to a file inside the scripts folder."""
        self._check()
        path = os.path.join(self._scripts_dir(), os.path.basename(filename))
        img = self._img(ghost)
        if not img.save(path):
            raise IOError(f"Could not save image to {path}")
        return path

    def load_image(self, filename, ghost=False):
        """Load an image from the scripts folder into the canvas or ghost."""
        self._check()
        path = os.path.join(self._scripts_dir(), os.path.basename(filename))
        loaded = QImage(path)
        if loaded.isNull():
            raise IOError(f"Could not load image from {path}")
        loaded = loaded.convertToFormat(QImage.Format_ARGB32)
        if ghost:
            self._ghost = loaded
        else:
            self._c._push_undo()
            self._c.image = loaded
            self._mw._update_size_label()
            self._mw._fit_canvas()
            self._c.update()
        return (loaded.width(), loaded.height())

    # --- text ---
    def draw_text(self, text, pos, font=None, size=None, bold=False, italic=False,
                  underline=False, color=None, bg_color=None, bg_transparent=None,
                  antialias=None, box=False, box_color=None, box_margin=None,
                  box_style='solid', box_width=1, ghost=False):
        """Draw text onto the canvas (or ghost) at pos (x, y).
           All style args are optional; omitting them uses the current tool settings.
           box_style: 'solid', 'dashed', 'dotted'
        """
        self._check()
        c = self._c
        # --- save originals ---
        _str   = c.text_str
        _font  = QFont(c.text_font)
        _col   = QColor(c.text_color)
        _bg    = QColor(c.text_bg_color)
        _bgt   = c.text_bg_transparent
        _aa    = c.text_antialias
        _box   = c.text_box
        _boxc  = QColor(c.text_box_color)
        _boxm  = c.text_box_margin
        _boxs  = c.text_box_style
        _boxw  = c.text_box_width
        # --- apply overrides ---
        c.text_str = str(text)
        f = QFont(c.text_font)
        if font is not None:
            f.setFamily(str(font))
        if size is not None:
            f.setPointSize(int(size))
        f.setBold(bool(bold))
        f.setItalic(bool(italic))
        f.setUnderline(bool(underline))
        c.text_font = f
        if color is not None:
            c.text_color = self._to_qcolor(color)
        if bg_color is not None:
            c.text_bg_color = self._to_qcolor(bg_color)
        if bg_transparent is not None:
            c.text_bg_transparent = bool(bg_transparent)
        if antialias is not None:
            c.text_antialias = bool(antialias)
        c.text_box = bool(box)
        if box_color is not None:
            c.text_box_color = self._to_qcolor(box_color)
        if box_margin is not None:
            c.text_box_margin = int(box_margin)
        c.text_box_style = str(box_style)
        c.text_box_width = int(box_width)
        # --- render ---
        img = self._img(ghost)
        p = QPainter(img)
        c._draw_text_at(p, QPoint(int(pos[0]), int(pos[1])))
        p.end()
        # --- restore ---
        c.text_str = _str;  c.text_font = _font;  c.text_color = _col
        c.text_bg_color = _bg;  c.text_bg_transparent = _bgt;  c.text_antialias = _aa
        c.text_box = _box;  c.text_box_color = _boxc;  c.text_box_margin = _boxm
        c.text_box_style = _boxs;  c.text_box_width = _boxw

    # --- selection ---
    def set_selection(self, shape, x, y, w, h):
        """shape: 'rectangle','circle','ellipse','wand'
           Returns dict with keys: x,y,w,h (or radius for circle)."""
        self._check()
        shape = str(shape).lower()
        self._mw._set_cut_mode(shape if shape in ('rectangle','circle','ellipse','wand') else 'rectangle')
        if shape == 'wand':
            prev_op = self._c.cut_op
            self._c.cut_op = 'select'
            self._c._magic_wand_select(QPoint(int(x), int(y)))
            if self._c._undo_stack:
                self._c._undo_stack.pop()
            self._c.cut_op = prev_op
            rect = self._c._selection_rect
            if rect is None:
                return {'x': 0, 'y': 0, 'w': 0, 'h': 0}
            return {'x': rect.x(), 'y': rect.y(), 'w': rect.width(), 'h': rect.height()}
        start = QPoint(int(x), int(y))
        end   = QPoint(int(x + w), int(y + h))
        if shape == 'circle':
            rect = QRect(int(x), int(y), int(w), int(h))
        else:
            rect = QRect(start, end).normalized()
        self._c._selection_rect = rect
        self._c.update()
        return {'x': rect.x(), 'y': rect.y(), 'w': rect.width(), 'h': rect.height()}

    def deselect(self):
        """Clear the current selection."""
        self._check()
        self._c._cancel_cut()

    # --- undo/redo ---
    def push_undo(self):
        self._c._push_undo()

    def commit(self):
        self._c.update()
        self._mw._mark_modified()


class ScriptConsole(QDialog):
    _append_sig = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("Script Console")
        self.resize(520, 300)
        layout = QVBoxLayout(self)
        self._out = QPlainTextEdit()
        self._out.setReadOnly(True)
        self._out.setFont(QFont("Courier New", 9))
        layout.addWidget(self._out)
        btn_row = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(70)
        clear_btn.clicked.connect(self._out.clear)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        self._append_sig.connect(self._out.appendPlainText)

    def write(self, text):
        if text.strip():
            self._append_sig.emit(text.rstrip())

    def flush(self):
        pass


class ScriptRunner(QObject):
    finished  = pyqtSignal()
    errored   = pyqtSignal(str)
    printed   = pyqtSignal(str)

    def __init__(self, path, api):
        super().__init__()
        self._path = path
        self._api  = api
        self._check_timer = QTimer()  # kept for stop signal compatibility

    def start_script(self):
        QTimer.singleShot(0, self._run)

    def stop(self):
        self._api._stopped = True

    def _run(self):
        import io
        class _Writer(io.TextIOBase):
            def __init__(self_, sig): self_._sig = sig
            def write(self_, s):
                if s.strip(): self_._sig.emit(s.rstrip())
                return len(s)
        writer = _Writer(self.printed)
        try:
            with open(self._path, encoding='utf-8') as f:
                code = f.read()
            import builtins
            globs = {'__builtins__': builtins, 'canvas': self._api, 'QColor': QColor, 'QPoint': QPoint,
                     'QRect': QRect, 'QPainter': QPainter, 'QPen': QPen,
                     'print': lambda *a, **kw: writer.write(' '.join(str(x) for x in a) + kw.get('end', '\n'))}
            exec(compile(code, self._path, 'exec'), globs)
            self.finished.emit()
        except InterruptedError:
            self.finished.emit()
        except Exception:
            import traceback
            self.errored.emit(traceback.format_exc())

class ScriptWindow(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window, Qt.Window)
        self.setWindowTitle("Scripts")
        self.resize(420, 340)
        self._mw = main_window
        self._runner = None
        self._scripts_dir = os.path.join(_app_dir(), 'scripts')
        os.makedirs(self._scripts_dir, exist_ok=True)
        self._console = ScriptConsole(self)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        warn = QLabel("Macros are Python scripts that run with full system access. Only run macros you trust.")
        warn.setWordWrap(True)
        warn.setStyleSheet("color: red; font-family: Arial; font-size: 10px;")
        layout.addWidget(warn)

        self._list = QListWidget()
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        self._run_btn = QPushButton()
        self._run_btn.setFixedWidth(80)
        self._refresh_btn = QPushButton()
        self._refresh_btn.setFixedWidth(80)
        self._console_btn = QPushButton("Console")
        self._console_btn.setFixedWidth(80)
        btn_row.addWidget(self._run_btn)
        btn_row.addWidget(self._refresh_btn)
        btn_row.addWidget(self._console_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._status = QLabel("")
        self._status.setStyleSheet("font-size: 11px; color: #555;")
        layout.addWidget(self._status)

        self._set_idle()
        self._refresh_btn.clicked.connect(self._refresh)
        self._run_btn.clicked.connect(self._toggle)
        self._console_btn.clicked.connect(self._open_console)
        self._refresh()

    def _play_icon(self):
        pix = QPixmap(16, 16)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setBrush(QColor(0, 160, 0))
        p.setPen(Qt.NoPen)
        p.drawPolygon(QPolygon([QPoint(3, 2), QPoint(13, 8), QPoint(3, 14)]))
        p.end()
        return QIcon(pix)

    def _stop_icon(self):
        pix = QPixmap(16, 16)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setBrush(QColor(200, 0, 0))
        p.setPen(Qt.NoPen)
        p.drawRect(3, 3, 10, 10)
        p.end()
        return QIcon(pix)

    def _refresh_icon(self):
        pix = QPixmap(16, 16)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(60, 60, 200), 2))
        p.setBrush(Qt.NoBrush)
        from PyQt5.QtCore import QRectF
        p.drawArc(QRectF(2, 2, 12, 12), 30 * 16, 300 * 16)
        p.setPen(QPen(QColor(60, 60, 200), 1))
        p.setBrush(QColor(60, 60, 200))
        p.drawPolygon(QPolygon([QPoint(13, 2), QPoint(13, 7), QPoint(8, 4)]))
        p.end()
        return QIcon(pix)

    def _set_idle(self):
        self._run_btn.setIcon(self._play_icon())
        self._run_btn.setText(" Run")
        self._refresh_btn.setIcon(self._refresh_icon())
        self._refresh_btn.setText(" Refresh")

    def _set_running(self, name):
        self._run_btn.setIcon(self._stop_icon())
        self._run_btn.setText(" Stop")
        self._status.setText(f"Running {name} ...")

    def _refresh(self):
        self._list.clear()
        if not os.path.isdir(self._scripts_dir):
            return
        for f in sorted(os.listdir(self._scripts_dir)):
            if f.endswith('.py'):
                self._list.addItem(f)

    def _open_console(self):
        self._console.show()
        self._console.raise_()
        self._console.activateWindow()

    def _toggle(self):
        if self._runner is not None:
            self._runner.stop()
            return
        item = self._list.currentItem()
        if not item:
            return
        name = item.text()
        path = os.path.join(self._scripts_dir, name)
        api  = ScriptAPI(self._mw)
        self._runner = ScriptRunner(path, api)
        self._runner.finished.connect(self._on_done)
        self._runner.errored.connect(self._on_error)
        self._runner.printed.connect(self._console.write)
        self._set_running(name)
        self._runner.start_script()

    def _on_done(self):
        self._runner = None
        self._status.setText("")
        self._set_idle()
        self._mw.canvas.update()

    def _on_error(self, msg):
        self._runner = None
        self._status.setText("")
        self._set_idle()
        self._mw.canvas.update()
        self._console.write("--- ERROR ---")
        self._console.write(msg)
        self._open_console()


def _write_error_log(exc_type, exc_value, exc_tb):
    import traceback, datetime, os
    log_path = os.path.join(_app_dir(), "error_SimpleDraw.txt")
    last_tool = "unknown"
    try:
        for obj in QApplication.topLevelWidgets():
            if isinstance(obj, MainWindow):
                last_tool = obj.canvas.tool
                break
    except Exception:
        pass
    log_written = False
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write(f"SimpleDraw v{APP_VERSION}\n")
            f.write(f"Date/Time : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Last Tool : {last_tool}\n")
            f.write(f"Error     : {exc_type.__name__}: {exc_value}\n")
            f.write("Traceback :\n")
            f.write("".join(traceback.format_tb(exc_tb)))
            f.write("\n")
        log_written = True
    except Exception:
        pass
    try:
        log_status = f"Error log written to:\n{log_path}" if log_written else "Error log could not be written."
        msg = QMessageBox()
        msg.setWindowTitle("Unexpected Error")
        msg.setText(f"{exc_type.__name__}: {exc_value}\n\n{log_status}")
        msg.setIcon(QMessageBox.Critical)
        msg.exec_()
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)


if __name__ == "__main__":
    sys.excepthook = _write_error_log
    app = QApplication(sys.argv)
    win = MainWindow()
    win._apply_theme(getattr(win, "_theme", "light"))
    win.show()
    sys.exit(app.exec_())
