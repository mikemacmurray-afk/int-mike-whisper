# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['src\\sidecar_main.py'],
    pathex=[],
    binaries=[],
    datas=collect_data_files('faster_whisper') + [('src/audio_recorder.py', '.'), ('src/injector.py', '.'), ('src/transcriber.py', '.')],
    hiddenimports=['faster_whisper', 'torch', 'sounddevice', 'keyboard', 'numpy', 'requests', 'pyperclip'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='mike-whisper-engine',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
