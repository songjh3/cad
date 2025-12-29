# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['cad_viewer.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['ezdxf', 'ezdxf.addons', 'ezdxf.addons.drawing', 'ezdxf.addons.drawing.matplotlib', 'matplotlib.backends.backend_agg'],
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
    name='CAD看图工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
