# Snapzor pour Windows 10 / 11

Outil de capture d'écran avec annotations, adapté de la version Zorin OS.

## Fonctionnalités

- **Captures** : plein écran (multi-moniteurs), région personnalisée, fenêtre active, délai 3 s
- **Annotations** : rectangle, flèche, stylo libre, surligneur, texte
- **Couleur et épaisseur** réglables
- **Export** : enregistrement PNG/JPEG ou copie directe dans le presse-papiers
- **Raccourcis** : F1 / F2 / F3 / F4, Ctrl+C, Ctrl+S, Ctrl+Shift+S, Ctrl+Z

## Installation utilisateur

Télécharger `Snapzor_Setup_1.0.0.exe` depuis le dossier `Output/` après build, puis l'exécuter. Aucune dépendance requise (Python embarqué).

## Lancement en mode développement

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python snapzor.py
```

## Construction du .exe et de l'installeur

Prérequis :
- **Python 3.10 ou supérieur**
- **Inno Setup 6** ([téléchargement](https://jrsoftware.org/isdl.php)) pour le `.exe` d'installation

Build automatisé (un seul script) :

```powershell
.\build.ps1
```

Cela produit :
- `dist\Snapzor\Snapzor.exe` — version portable (dossier complet à copier)
- `Output\Snapzor_Setup_1.0.0.exe` — installeur Windows

Build manuel :

```powershell
pip install pyinstaller
pyinstaller Snapzor.spec
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" Snapzor.iss
```

## Architecture

```
snapzor_win/
├── snapzor.py              # Point d'entrée (QApplication)
├── snapzor/
│   ├── __init__.py
│   ├── capture.py          # Backend Win32 (mss + PrintWindow)
│   ├── annotation.py       # Couche d'annotation QPainter
│   ├── main_window.py      # Fenêtre principale Qt
│   ├── region_selector.py  # Overlay fullscreen pour sélection
│   └── Snapzor.png
├── Snapzor.spec            # Configuration PyInstaller
├── Snapzor.iss             # Configuration Inno Setup
├── version_info.txt        # Métadonnées de l'exe
├── build.ps1               # Script de build automatique
└── requirements.txt
```

## Différences notables avec la version Linux

| Aspect | Linux (GTK4) | Windows (Qt6) |
|--------|--------------|---------------|
| UI | GTK4 + libadwaita | PySide6 |
| Capture plein écran | gdbus / grim / gnome-screenshot | mss (BitBlt) |
| Capture région | slurp + grim | Overlay Qt fullscreen |
| Capture fenêtre | — | PrintWindow + PW_RENDERFULLCONTENT |
| Presse-papiers | wl-copy / xclip | QClipboard |
| Distribution | install.sh + .desktop | Installeur Inno Setup |

## Licence

Voir le projet d'origine.
