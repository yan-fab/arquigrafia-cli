# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = []
datas += collect_data_files('pyfiglet')
datas += collect_data_files('transformers')
datas += collect_data_files('tokenizers')
datas += [('core/vcaa_tags.json', 'core')]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['questionary', 'keyring.backends.Windows', 'PIL', 'piexif', 'geopy', 'bs4', 'requests', 'transformers', 'transformers.models.blip', 'torch', 'deep_translator', 'deep_translator.google'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'onnxruntime',
        'scipy',
        'pandas',
        'pyarrow',
        'cv2',
        'numba',
        'matplotlib',
        'tkinter',
        'torchvision',
        'yt_dlp',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='arquigrafia',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
