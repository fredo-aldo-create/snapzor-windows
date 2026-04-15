"""
Snapzor — Couche d'annotation Qt.

Reproduit fidèlement les outils du Snapzor Linux :
  - Rectangle, Flèche, Stylo, Surligneur, Texte
  - Couleur + épaisseur configurables
  - Stockage en coordonnées image, affichage avec scale/offset
  - Undo, Clear
  - Aperçu temps réel pendant le tracé
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, Signal
from PySide6.QtGui import (
    QColor, QImage, QPainter, QPen, QBrush, QFont, QPixmap, QFontMetrics,
    QMouseEvent, QPaintEvent, QResizeEvent
)
from PySide6.QtWidgets import QWidget, QInputDialog


class Tool(str, Enum):
    NONE = "none"
    RECTANGLE = "rectangle"
    ARROW = "arrow"
    PEN = "pen"
    HIGHLIGHT = "highlight"
    TEXT = "text"


@dataclass
class Annotation:
    tool: Tool
    color: QColor
    width: float
    font_size: int = 16
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    points: List[Tuple[float, float]] = field(default_factory=list)
    text: str = ""


class AnnotationCanvas(QWidget):
    """Affiche le screenshot + permet de dessiner par-dessus."""

    statusChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)

        self._base: Optional[QImage] = None
        self.annotations: List[Annotation] = []

        self.current_tool: Tool = Tool.RECTANGLE
        self.current_color: QColor = QColor(220, 38, 38, 255)
        self.current_width: float = 2.5
        self.font_size: int = 16

        self._drawing = False
        self._start = QPointF()
        self._last = QPointF()
        self._pen_pts: List[Tuple[float, float]] = []

        # Géométrie d'affichage (contain)
        self._scale_x = 1.0
        self._scale_y = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._disp_w = 0.0
        self._disp_h = 0.0

    # ------------------------------------------------------------------ API

    def set_image(self, img: QImage):
        self._base = img
        self.annotations.clear()
        self._recompute_geometry()
        self.update()

    def has_image(self) -> bool:
        return self._base is not None

    def set_tool(self, tool: Tool):
        self.current_tool = tool

    def set_color(self, color: QColor):
        self.current_color = QColor(color)

    def set_width(self, w: float):
        self.current_width = float(w)

    def undo(self):
        if self.annotations:
            self.annotations.pop()
            self.update()

    def clear_annotations(self):
        self.annotations.clear()
        self.update()

    def render_final(self) -> Optional[QImage]:
        """Fusionne les annotations sur l'image de base (taille originale)."""
        if self._base is None:
            return None
        out = QImage(self._base)
        p = QPainter(out)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        for ann in self.annotations:
            self._draw_annotation(p, ann, in_image_coords=True, preview=False)
        p.end()
        return out

    # --------------------------------------------------------------- Géom

    def _recompute_geometry(self):
        if self._base is None:
            return
        iw, ih = self._base.width(), self._base.height()
        ww, wh = max(1, self.width()), max(1, self.height())

        img_ratio = iw / ih
        wgt_ratio = ww / wh
        if img_ratio > wgt_ratio:
            disp_w = ww
            disp_h = ww / img_ratio
        else:
            disp_h = wh
            disp_w = wh * img_ratio

        self._disp_w = disp_w
        self._disp_h = disp_h
        self._offset_x = (ww - disp_w) / 2.0
        self._offset_y = (wh - disp_h) / 2.0
        self._scale_x = iw / disp_w  # widget → image
        self._scale_y = ih / disp_h

    def _to_image(self, wx: float, wy: float) -> Tuple[float, float]:
        return ((wx - self._offset_x) * self._scale_x,
                (wy - self._offset_y) * self._scale_y)

    def _to_widget(self, ix: float, iy: float) -> Tuple[float, float]:
        return (ix / self._scale_x + self._offset_x,
                iy / self._scale_y + self._offset_y)

    def _scale_for_widget(self) -> float:
        """Facteur image→widget (1/scale_x)."""
        return 1.0 / self._scale_x if self._scale_x else 1.0

    # ----------------------------------------------------------- Évents Qt

    def resizeEvent(self, e: QResizeEvent):
        self._recompute_geometry()
        super().resizeEvent(e)

    def mousePressEvent(self, e: QMouseEvent):
        if self._base is None or self.current_tool == Tool.NONE:
            return
        if e.button() != Qt.LeftButton:
            return
        # Clamp dans la zone d'image affichée
        if not self._point_in_image(e.position()):
            return
        self._drawing = True
        self._start = e.position()
        self._last = e.position()
        if self.current_tool == Tool.PEN:
            self._pen_pts = [(e.position().x(), e.position().y())]
        elif self.current_tool == Tool.TEXT:
            # On capture le point puis on demande le texte au mouseRelease
            pass
        self.update()

    def mouseMoveEvent(self, e: QMouseEvent):
        if not self._drawing:
            return
        self._last = e.position()
        if self.current_tool == Tool.PEN:
            self._pen_pts.append((e.position().x(), e.position().y()))
        self.update()

    def mouseReleaseEvent(self, e: QMouseEvent):
        if not self._drawing or self._base is None:
            return
        self._drawing = False
        self._last = e.position()

        if self.current_tool == Tool.TEXT:
            ix, iy = self._to_image(self._start.x(), self._start.y())
            text, ok = QInputDialog.getText(self, "Texte", "Saisir le texte :")
            if ok and text.strip():
                self.annotations.append(Annotation(
                    tool=Tool.TEXT,
                    color=QColor(self.current_color),
                    width=self.current_width,
                    font_size=self.font_size,
                    x1=ix, y1=iy,
                    text=text.strip(),
                ))
            self.update()
            return

        ix1, iy1 = self._to_image(self._start.x(), self._start.y())
        ix2, iy2 = self._to_image(self._last.x(), self._last.y())

        ann = Annotation(
            tool=self.current_tool,
            color=QColor(self.current_color),
            width=self.current_width,
            font_size=self.font_size,
            x1=ix1, y1=iy1, x2=ix2, y2=iy2,
        )
        if self.current_tool == Tool.PEN:
            ann.points = [self._to_image(px, py) for px, py in self._pen_pts]
            self._pen_pts = []
        # Ne pas enregistrer un geste « vide »
        if self.current_tool != Tool.PEN and abs(ix1 - ix2) < 2 and abs(iy1 - iy2) < 2:
            self.update()
            return
        self.annotations.append(ann)
        self.update()

    def _point_in_image(self, p: QPointF) -> bool:
        return (self._offset_x <= p.x() <= self._offset_x + self._disp_w
                and self._offset_y <= p.y() <= self._offset_y + self._disp_h)

    # -------------------------------------------------------------- Render

    def paintEvent(self, e: QPaintEvent):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        # Fond
        p.fillRect(self.rect(), QColor(30, 30, 32))

        if self._base is None:
            p.setPen(QColor(180, 180, 185))
            f = p.font()
            f.setPointSize(13)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignCenter,
                       'Cliquez sur "Capture" ou appuyez sur F1\n\n'
                       'F1 = plein écran   ·   F2 = région   ·   F3 = délai 3s')
            return

        # Image
        target = QRectF(self._offset_x, self._offset_y, self._disp_w, self._disp_h)
        p.drawImage(target, self._base)

        # Annotations existantes (en coords image → widget)
        for ann in self.annotations:
            self._draw_annotation(p, ann, in_image_coords=False, preview=False)

        # Aperçu en cours
        if self._drawing and self.current_tool != Tool.NONE:
            self._draw_preview(p)

    def _draw_preview(self, p: QPainter):
        ann = Annotation(
            tool=self.current_tool,
            color=QColor(self.current_color),
            width=self.current_width,
            font_size=self.font_size,
            x1=self._start.x(), y1=self._start.y(),
            x2=self._last.x(), y2=self._last.y(),
        )
        if self.current_tool == Tool.PEN:
            ann.points = list(self._pen_pts)
        self._draw_annotation_widget_coords(p, ann, preview=True)

    def _draw_annotation(self, p: QPainter, ann: Annotation,
                          in_image_coords: bool, preview: bool):
        """
        Dessine une annotation.
        - in_image_coords=True  : les coords ann.x1/y1 sont en pixels image
                                  (utilisé pour rendu final sur l'image originale).
        - in_image_coords=False : convertir image→widget pour l'affichage.
        """
        if in_image_coords:
            x1, y1 = ann.x1, ann.y1
            x2, y2 = ann.x2, ann.y2
            scale_w = 1.0  # on dessine déjà à la taille image
            pts = ann.points
            font_px = ann.font_size
            stroke_w = ann.width * 2.0  # rendu final → traits proportionnels image
        else:
            x1, y1 = self._to_widget(ann.x1, ann.y1)
            x2, y2 = self._to_widget(ann.x2, ann.y2)
            scale_w = self._scale_for_widget()
            pts = [self._to_widget(ix, iy) for ix, iy in ann.points]
            font_px = ann.font_size
            stroke_w = ann.width

        self._render(p, ann, x1, y1, x2, y2, pts, stroke_w, font_px,
                     in_image_coords=in_image_coords, preview=preview)

    def _draw_annotation_widget_coords(self, p: QPainter, ann: Annotation, preview: bool):
        """Aperçu : coords déjà en widget."""
        pts = ann.points  # déjà widget
        self._render(p, ann, ann.x1, ann.y1, ann.x2, ann.y2, pts,
                     ann.width, ann.font_size,
                     in_image_coords=False, preview=preview)

    def _render(self, p: QPainter, ann: Annotation,
                x1, y1, x2, y2, pts, stroke_w, font_px,
                in_image_coords: bool, preview: bool):
        color = QColor(ann.color)
        if preview:
            color.setAlphaF(color.alphaF() * 0.7)

        pen = QPen(color)
        pen.setWidthF(stroke_w)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        tool = ann.tool
        if tool == Tool.RECTANGLE:
            rx, ry = min(x1, x2), min(y1, y2)
            rw, rh = abs(x2 - x1), abs(y2 - y1)
            p.drawRect(QRectF(rx, ry, rw, rh))

        elif tool == Tool.ARROW:
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            angle = math.atan2(y2 - y1, x2 - x1)
            head_len = max(12.0 if not in_image_coords else 24.0, stroke_w * 4.0)
            spread = math.pi / 6
            for side in (angle + math.pi - spread, angle + math.pi + spread):
                hx = x2 + head_len * math.cos(side)
                hy = y2 + head_len * math.sin(side)
                p.drawLine(QPointF(x2, y2), QPointF(hx, hy))

        elif tool == Tool.PEN:
            if len(pts) >= 2:
                for i in range(1, len(pts)):
                    p.drawLine(QPointF(pts[i-1][0], pts[i-1][1]),
                               QPointF(pts[i][0], pts[i][1]))

        elif tool == Tool.HIGHLIGHT:
            fill = QColor(color)
            fill.setAlphaF(0.35)
            rx, ry = min(x1, x2), min(y1, y2)
            rw, rh = abs(x2 - x1), abs(y2 - y1)
            p.fillRect(QRectF(rx, ry, rw, rh), fill)

        elif tool == Tool.TEXT:
            f = QFont()
            f.setPixelSize(int(font_px * (2.0 if in_image_coords else 1.0)))
            p.setFont(f)
            p.setPen(color)
            # y est la baseline approximative
            p.drawText(QPointF(x1, y1), ann.text)
