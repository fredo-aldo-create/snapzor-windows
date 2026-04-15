"""
Snapzor — Fenêtre principale Windows.

Reproduit fidèlement l'UX du Snapzor Linux :
  - Bouton Capture (menu : région / plein écran / délai 3s / fenêtre active)
  - Barre d'outils annotation
  - Sauvegarde / copie presse-papiers / undo / clear
  - Raccourcis : F1 plein écran, F2 région, F3 délai, F4 fenêtre active,
                 Ctrl+C copier, Ctrl+S enregistrer, Ctrl+Z annuler
"""

from __future__ import annotations
import io
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image
from PySide6.QtCore import Qt, QTimer, QSize, QStandardPaths
from PySide6.QtGui import (
    QAction, QIcon, QImage, QPixmap, QColor, QKeySequence, QPainter, QFont,
    QShortcut, QGuiApplication, QClipboard
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QPushButton,
    QToolButton, QMenu, QLabel, QFileDialog, QMessageBox, QColorDialog,
    QDoubleSpinBox, QFrame, QStatusBar, QSizePolicy, QApplication
)

from .annotation import AnnotationCanvas, Tool
from .region_selector import RegionSelector, pil_to_qimage
from . import capture as cap


APP_NAME = "Snapzor"
VERSION = "1.0.0-win"


def default_save_dir() -> Path:
    """Dossier Pictures\\Screenshots de l'utilisateur."""
    pics = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
    if not pics:
        pics = str(Path.home() / "Pictures")
    d = Path(pics) / "Screenshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def pil_to_qimage_fast(img: Image.Image) -> QImage:
    if img.mode != "RGB":
        img = img.convert("RGB")
    data = img.tobytes("raw", "RGB")
    return QImage(data, img.width, img.height,
                  img.width * 3, QImage.Format_RGB888).copy()


def qimage_to_pil(qimg: QImage) -> Image.Image:
    qimg = qimg.convertToFormat(QImage.Format_RGB888)
    w, h = qimg.width(), qimg.height()
    ptr = qimg.constBits()
    # PySide6 retourne un memoryview ; on convertit en bytes
    raw = bytes(ptr)
    # Le stride peut différer de w*3 (alignement 4 bytes)
    stride = qimg.bytesPerLine()
    if stride == w * 3:
        return Image.frombytes("RGB", (w, h), raw)
    # Reconstruire ligne par ligne
    rows = [raw[i * stride: i * stride + w * 3] for i in range(h)]
    return Image.frombytes("RGB", (w, h), b"".join(rows))


class SnapzorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1024, 720)

        self.save_dir = default_save_dir()
        self._build_ui()
        self._build_shortcuts()
        self._update_status("Prêt — F1 pour capturer le plein écran")

    # ----------------------------------------------------------------- UI

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        v = QVBoxLayout(central)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # ---- Barre du haut : capture / copie / save ----
        top_bar = QToolBar()
        top_bar.setMovable(False)
        top_bar.setIconSize(QSize(18, 18))
        self.addToolBar(top_bar)

        capture_btn = QToolButton()
        capture_btn.setText("Capture ▾")
        capture_btn.setToolTip("Nouvelle capture")
        capture_btn.setPopupMode(QToolButton.InstantPopup)
        capture_menu = QMenu(capture_btn)
        capture_menu.addAction("Plein écran (F1)", self.capture_full)
        capture_menu.addAction("Sélection de région (F2)", self.capture_region)
        capture_menu.addAction("Avec délai 3 s (F3)", self.capture_delayed)
        capture_menu.addAction("Fenêtre active (F4)", self.capture_window)
        capture_btn.setMenu(capture_menu)
        top_bar.addWidget(capture_btn)

        top_bar.addSeparator()

        copy_act = QAction("Copier", self)
        copy_act.setToolTip("Copier dans le presse-papiers (Ctrl+C)")
        copy_act.triggered.connect(self.copy_to_clipboard)
        top_bar.addAction(copy_act)

        save_act = QAction("Enregistrer", self)
        save_act.setToolTip("Enregistrer sous… (Ctrl+S)")
        save_act.triggered.connect(self.save_as)
        top_bar.addAction(save_act)

        save_quick_act = QAction("Enregistrement rapide", self)
        save_quick_act.setToolTip(f"Enregistrer dans {self.save_dir}")
        save_quick_act.triggered.connect(self.save_quick)
        top_bar.addAction(save_quick_act)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        top_bar.addWidget(spacer)

        folder_act = QAction("Ouvrir le dossier", self)
        folder_act.triggered.connect(self.open_save_folder)
        top_bar.addAction(folder_act)

        about_act = QAction("À propos", self)
        about_act.triggered.connect(self.show_about)
        top_bar.addAction(about_act)

        # ---- Barre d'annotation ----
        ann_bar = QToolBar()
        ann_bar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, ann_bar)
        self.insertToolBarBreak(ann_bar)

        ann_bar.addWidget(QLabel("  Outil : "))

        self._tool_actions: dict[Tool, QAction] = {}
        for tool, label, shortcut in [
            (Tool.RECTANGLE, "▭ Rectangle", "R"),
            (Tool.ARROW, "➜ Flèche", "A"),
            (Tool.PEN, "✎ Stylo", "P"),
            (Tool.HIGHLIGHT, "▮ Surligneur", "H"),
            (Tool.TEXT, "T Texte", "T"),
        ]:
            act = QAction(label, self)
            act.setCheckable(True)
            act.setShortcut(QKeySequence(shortcut))
            act.triggered.connect(lambda checked, t=tool: self._select_tool(t))
            ann_bar.addAction(act)
            self._tool_actions[tool] = act

        ann_bar.addSeparator()
        ann_bar.addWidget(QLabel(" Couleur : "))
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(32, 22)
        self._current_color = QColor(220, 38, 38)
        self._refresh_color_btn()
        self.color_btn.clicked.connect(self._pick_color)
        ann_bar.addWidget(self.color_btn)

        ann_bar.addWidget(QLabel("  Épaisseur : "))
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0.5, 20.0)
        self.width_spin.setSingleStep(0.5)
        self.width_spin.setValue(2.5)
        self.width_spin.setDecimals(1)
        self.width_spin.valueChanged.connect(
            lambda v: self.canvas.set_width(v)
        )
        ann_bar.addWidget(self.width_spin)

        ann_bar.addSeparator()
        undo_act = QAction("↶ Annuler", self)
        undo_act.setToolTip("Annuler (Ctrl+Z)")
        undo_act.triggered.connect(lambda: self.canvas.undo())
        ann_bar.addAction(undo_act)

        clear_act = QAction("✕ Tout effacer", self)
        clear_act.triggered.connect(lambda: self.canvas.clear_annotations())
        ann_bar.addAction(clear_act)

        # ---- Canvas ----
        self.canvas = AnnotationCanvas()
        self.canvas.set_color(self._current_color)
        self.canvas.set_tool(Tool.RECTANGLE)
        self._tool_actions[Tool.RECTANGLE].setChecked(True)
        v.addWidget(self.canvas, 1)

        # ---- Status bar ----
        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def _build_shortcuts(self):
        for key, fn in [
            ("F1", self.capture_full),
            ("F2", self.capture_region),
            ("F3", self.capture_delayed),
            ("F4", self.capture_window),
            ("Ctrl+C", self.copy_to_clipboard),
            ("Ctrl+S", self.save_as),
            ("Ctrl+Shift+S", self.save_quick),
            ("Ctrl+Z", lambda: self.canvas.undo()),
        ]:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(fn)

    # ------------------------------------------------------------ Helpers

    def _update_status(self, text: str):
        self.status.showMessage(text)

    def _select_tool(self, tool: Tool):
        for t, act in self._tool_actions.items():
            act.setChecked(t == tool)
        self.canvas.set_tool(tool)

    def _refresh_color_btn(self):
        c = self._current_color
        self.color_btn.setStyleSheet(
            f"background-color: rgb({c.red()},{c.green()},{c.blue()}); "
            f"border: 1px solid #555; border-radius: 3px;"
        )

    def _pick_color(self):
        c = QColorDialog.getColor(self._current_color, self, "Choisir la couleur")
        if c.isValid():
            self._current_color = c
            self.canvas.set_color(c)
            self._refresh_color_btn()

    # ----------------------------------------------------------- Captures

    def _take_and_load(self, capture_fn):
        """Pattern : minimiser, attendre, capturer, restaurer."""
        self.showMinimized()
        QTimer.singleShot(350, lambda: self._do_capture(capture_fn))

    def _do_capture(self, capture_fn):
        try:
            img = capture_fn()
        except Exception as e:
            self.showNormal()
            self.activateWindow()
            QMessageBox.critical(self, "Erreur de capture", str(e))
            return
        self.showNormal()
        self.activateWindow()
        self.raise_()
        if img is None:
            self._update_status("Capture annulée ou impossible.")
            return
        self._set_image(img)

    def _set_image(self, img: Image.Image):
        qimg = pil_to_qimage_fast(img)
        self.canvas.set_image(qimg)
        self._update_status(f"Capture {img.width}×{img.height} px — annotez puis Ctrl+S / Ctrl+C")

    # --- Actions de capture ---

    def capture_full(self):
        self._take_and_load(cap.capture_all_screens)

    def capture_delayed(self):
        self._update_status("Capture dans 3 s…")
        QTimer.singleShot(3000, lambda: self._take_and_load(cap.capture_all_screens))

    def capture_window(self):
        self._take_and_load(cap.capture_active_window)

    def capture_region(self):
        """
        On masque la fenêtre, on capture le bureau virtuel pour l'overlay,
        puis on lance le sélecteur. La capture finale est un crop.
        """
        self.showMinimized()
        QTimer.singleShot(350, self._launch_region_selector)

    def _launch_region_selector(self):
        try:
            bg = cap.capture_all_screens()
        except Exception as e:
            self.showNormal()
            QMessageBox.critical(self, "Erreur", f"Impossible de capturer le fond : {e}")
            return

        ox, oy, _, _ = cap.virtual_desktop_geometry()
        self._selector = RegionSelector(bg, (ox, oy))
        self._selector.regionSelected.connect(self._on_region_picked)
        self._selector.cancelled.connect(self._on_region_cancelled)
        # Garder le fond en mémoire pour cropper sans recapturer
        self._region_bg = bg
        self._region_origin = (ox, oy)
        self._selector.show()
        self._selector.activateWindow()
        self._selector.raise_()

    def _on_region_picked(self, x: int, y: int, w: int, h: int):
        # Crop depuis le fond déjà capturé : pas de seconde capture, pas de scintillement
        ox, oy = self._region_origin
        crop = self._region_bg.crop((x - ox, y - oy, x - ox + w, y - oy + h))
        self.showNormal()
        self.activateWindow()
        self.raise_()
        self._set_image(crop)

    def _on_region_cancelled(self):
        self.showNormal()
        self.activateWindow()
        self._update_status("Sélection annulée.")

    # -------------------------------------------------------- Sortie image

    def _final_image(self) -> Optional[Image.Image]:
        if not self.canvas.has_image():
            QMessageBox.information(self, APP_NAME, "Aucune capture à exporter.")
            return None
        qimg = self.canvas.render_final()
        return qimage_to_pil(qimg)

    def copy_to_clipboard(self):
        if not self.canvas.has_image():
            self._update_status("Rien à copier.")
            return
        qimg = self.canvas.render_final()
        QGuiApplication.clipboard().setImage(qimg, QClipboard.Clipboard)
        self._update_status("Copié dans le presse-papiers ✓")

    def save_quick(self):
        img = self._final_image()
        if img is None:
            return
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = self.save_dir / f"Snapzor_{ts}.png"
        img.save(path, "PNG", optimize=True)
        self._update_status(f"Enregistré : {path}")

    def save_as(self):
        img = self._final_image()
        if img is None:
            return
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default = str(self.save_dir / f"Snapzor_{ts}.png")
        path, selected = QFileDialog.getSaveFileName(
            self, "Enregistrer la capture", default,
            "Image PNG (*.png);;Image JPEG (*.jpg *.jpeg);;Tous les fichiers (*)"
        )
        if not path:
            return
        ext = Path(path).suffix.lower()
        if ext in (".jpg", ".jpeg"):
            img.convert("RGB").save(path, "JPEG", quality=92)
        else:
            if not ext:
                path += ".png"
            img.save(path, "PNG", optimize=True)
        self._update_status(f"Enregistré : {path}")

    def open_save_folder(self):
        os.startfile(self.save_dir)  # type: ignore[attr-defined]

    def show_about(self):
        QMessageBox.about(
            self, f"À propos de {APP_NAME}",
            f"<b>{APP_NAME}</b> {VERSION}<br>"
            "Outil de capture d'écran pour Windows 10 / 11.<br><br>"
            "Capture plein écran, région, fenêtre active.<br>"
            "Annotations : rectangle, flèche, stylo, surligneur, texte.<br><br>"
            "Adapté de Snapzor pour Zorin OS."
        )
