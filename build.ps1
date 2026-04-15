# build.ps1 — Construit Snapzor.exe et l'installeur en une commande
# Prérequis : Python 3.10+, Inno Setup 6 installé

$ErrorActionPreference = "Stop"

Write-Host "==> Création de l'environnement virtuel" -ForegroundColor Cyan
if (-not (Test-Path .venv)) {
    python -m venv .venv
}
.\.venv\Scripts\Activate.ps1

Write-Host "==> Installation des dépendances" -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

Write-Host "==> Conversion de l'icône PNG → ICO" -ForegroundColor Cyan
if (-not (Test-Path Snapzor.ico)) {
    python -c "from PIL import Image; img = Image.open('snapzor/Snapzor.png'); img.save('Snapzor.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
}

Write-Host "==> Build PyInstaller" -ForegroundColor Cyan
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist)  { Remove-Item -Recurse -Force dist }
pyinstaller --noconfirm Snapzor.spec

Write-Host "==> Construction de l'installeur (Inno Setup)" -ForegroundColor Cyan
$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (Test-Path $iscc) {
    & $iscc Snapzor.iss
    Write-Host "✓ Installeur créé dans Output\" -ForegroundColor Green
} else {
    Write-Warning "Inno Setup 6 introuvable. Installez-le pour générer le .exe d'installation."
    Write-Host "   L'application portable est disponible dans dist\Snapzor\" -ForegroundColor Yellow
}
