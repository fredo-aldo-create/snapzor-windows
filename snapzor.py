"""
Snapzor — point d'entrée Windows.
Lancement : python snapzor.py
"""
import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from snapzor.main_window import SnapzorWindow, APP_NAME


def resource_path(rel: str) -> str:
    """Trouve une ressource, qu'on tourne en script ou via PyInstaller."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def main():
    # Hint pour Windows : utiliser un AppUserModelID dédié
    # → l'icône Snapzor s'affiche correctement dans la barre des tâches
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "io.github.snapzor.app"
            )
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Snapzor")

    icon_path = resource_path("Snapzor.ico")
    if not os.path.exists(icon_path):
        icon_path = resource_path("Snapzor.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    win = SnapzorWindow()
    if os.path.exists(icon_path):
        win.setWindowIcon(QIcon(icon_path))
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
