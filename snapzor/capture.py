"""
Snapzor — Capture backend Windows.

Stratégies :
- Plein écran multi-moniteurs : mss (BitBlt natif, très rapide)
- Écran courant : moniteur sous le curseur
- Région : overlay fullscreen sans bordures (Qt) géré côté UI
- Fenêtre active : PrintWindow + PW_RENDERFULLCONTENT (capture même fenêtres masquées partiellement)
"""

from __future__ import annotations
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple

from PIL import Image
import mss


# ---------------------------------------------------------------------------
# Capture plein écran / multi-moniteurs / monitor courant
# ---------------------------------------------------------------------------

def capture_all_screens() -> Image.Image:
    """Capture l'ensemble du bureau virtuel (tous les écrans)."""
    with mss.mss() as sct:
        # Le premier monitor (index 0) est l'union de tous
        shot = sct.grab(sct.monitors[0])
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def capture_primary_screen() -> Image.Image:
    """Capture l'écran principal."""
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[1])
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def capture_screen_under_cursor() -> Image.Image:
    """Capture l'écran qui contient actuellement le curseur."""
    pt = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    with mss.mss() as sct:
        for mon in sct.monitors[1:]:
            if (mon["left"] <= pt.x < mon["left"] + mon["width"]
                    and mon["top"] <= pt.y < mon["top"] + mon["height"]):
                shot = sct.grab(mon)
                return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    return capture_primary_screen()


def capture_region(x: int, y: int, w: int, h: int) -> Image.Image:
    """Capture une zone précise du bureau virtuel (coordonnées absolues)."""
    if w <= 0 or h <= 0:
        raise ValueError("Largeur/hauteur de région invalides")
    region = {"left": x, "top": y, "width": w, "height": h}
    with mss.mss() as sct:
        shot = sct.grab(region)
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


# ---------------------------------------------------------------------------
# Capture de la fenêtre active (Win32)
# ---------------------------------------------------------------------------

def capture_active_window() -> Optional[Image.Image]:
    """
    Capture la fenêtre actuellement au premier plan via PrintWindow.
    Retourne None en cas d'échec.
    """
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None

    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None

    w = rect.right - rect.left
    h = rect.bottom - rect.top
    if w <= 0 or h <= 0:
        return None

    hdc_window = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_window)
    hbitmap = gdi32.CreateCompatibleBitmap(hdc_window, w, h)
    gdi32.SelectObject(hdc_mem, hbitmap)

    PW_RENDERFULLCONTENT = 0x00000002
    user32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT)

    # Extraction des pixels
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h  # négatif = top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0  # BI_RGB

    buffer_len = w * h * 4
    buffer = (ctypes.c_ubyte * buffer_len)()
    gdi32.GetDIBits(hdc_mem, hbitmap, 0, h, buffer, ctypes.byref(bmi), 0)

    img = Image.frombuffer("RGBA", (w, h), buffer, "raw", "BGRA", 0, 1).convert("RGB")

    # Nettoyage
    gdi32.DeleteObject(hbitmap)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_window)

    return img


# ---------------------------------------------------------------------------
# Géométrie du bureau virtuel
# ---------------------------------------------------------------------------

def virtual_desktop_geometry() -> Tuple[int, int, int, int]:
    """Retourne (x, y, w, h) du bureau virtuel complet."""
    with mss.mss() as sct:
        m = sct.monitors[0]
        return m["left"], m["top"], m["width"], m["height"]
