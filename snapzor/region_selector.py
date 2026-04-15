"""
Snapzor — Sélecteur de région fullscreen.

Affiche le bureau capturé en fond, assombri, et permet de tracer
un rectangle de sélection. Couvre tous les écrans du bureau virtuel.
"""

from __future__ import annotations
from typing import Optional, Tuple

from PIL import Image
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import (
    QImage, QPainter, QColor, QPen, QPixmap, QKeyEvent, QMouseEvent,
    QGuiApplication, QFont
)
from PySide6.QtWidgets import QWidget


def pil_to_qimage(img: Image.Image) -> QImage:
    """Conversion PIL → QImage sans copie de données superflue."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    data = img.tobytes("raw", "RGB")
    qimg = QImage(data, img.width, img.height, img.width * 3, QImage.Format_RGB888)
    return qimg.copy()  # détache du buffer Python


class RegionSelector(QWidget):
    """
    Fenêtre fullscreen sans bordures couvrant le bureau virtuel complet.
    Émet `regionSelected(x, y, w, h)` en coordonnées absolues, ou
    `cancelled` si l'utilisateur appuie sur Échap.
    """

    regionSelected = Signal(int, int, int, int)
    cancelled = Signal()

    def __init__(self, background: Image.Image,
                 desktop_origin: Tuple[int, int]):
        super().__init__(None)
        self._origin_x, self._origin_y = desktop_origin
        self._bg = pil_to_qimage(background)
        self._pixmap = QPixmap.fromImage(self._bg)

        self._start: Optional[QPoint] = None
        self._end: Optional[QPoint] = None

        # Couvrir tout le bureau virtuel
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setCursor(Qt.CrossCursor)

        # Position absolue en pixels physiques
        self.setGeometry(self._origin_x, self._origin_y,
                         self._bg.width(), self._bg.height())

    # ----------------------------------------------------------- Évents

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() == Qt.Key_Escape:
            self.cancelled.emit()
            self.close()
        else:
            super().keyPressEvent(e)

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            self._start = e.position().toPoint()
            self._end = self._start
            self.update()

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._start is not None:
            self._end = e.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, e: QMouseEvent):
        if e.button() != Qt.LeftButton or self._start is None:
            return
        self._end = e.position().toPoint()
        rect = self._normalized_rect()
        if rect.width() < 5 or rect.height() < 5:
            self.cancelled.emit()
            self.close()
            return
        # Conversion en coordonnées absolues du bureau virtuel
        x = rect.x() + self._origin_x
        y = rect.y() + self._origin_y
        self.regionSelected.emit(x, y, rect.width(), rect.height())
        self.close()

    def _normalized_rect(self) -> QRect:
        if self._start is None or self._end is None:
            return QRect()
        return QRect(self._start, self._end).normalized()

    # ------------------------------------------------------------ Render

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        # Fond
        p.drawPixmap(0, 0, self._pixmap)
        # Voile sombre
        p.fillRect(self.rect(), QColor(0, 0, 0, 110))

        if self._start is not None and self._end is not None:
            sel = self._normalized_rect()
            # Re-révéler la zone sélectionnée
            p.drawPixmap(sel, self._pixmap, sel)

            # Bordure
            pen = QPen(QColor(56, 152, 255, 230))
            pen.setWidth(2)
            p.setPen(pen)
            p.drawRect(sel)

            # Étiquette dimensions
            label = f"{sel.width()} × {sel.height()} px"
            f = QFont()
            f.setPointSize(10)
            f.setBold(True)
            p.setFont(f)
            metrics = p.fontMetrics()
            tw = metrics.horizontalAdvance(label) + 12
            th = metrics.height() + 6
            tx = sel.x()
            ty = sel.y() - th - 4
            if ty < 0:
                ty = sel.y() + sel.height() + 4
            p.fillRect(tx, ty, tw, th, QColor(0, 0, 0, 200))
            p.setPen(QColor(255, 255, 255))
            p.drawText(tx + 6, ty + metrics.ascent() + 3, label)

        # Aide en haut
        if self._start is None:
            hint = "Cliquez-glissez pour sélectionner une zone   ·   Échap pour annuler"
            f = QFont()
            f.setPointSize(11)
            p.setFont(f)
            metrics = p.fontMetrics()
            tw = metrics.horizontalAdvance(hint) + 24
            th = metrics.height() + 12
            tx = (self.width() - tw) // 2
            ty = 32
            p.fillRect(tx, ty, tw, th, QColor(0, 0, 0, 180))
            p.setPen(QColor(255, 255, 255))
            p.drawText(tx + 12, ty + metrics.ascent() + 6, hint)
