# -*- mode: python ; coding: utf-8 -*-
# PortoWrite — PyInstaller build spec (folder/COLLECT mode)
# Build: .\.venv\Scripts\pyinstaller.exe portowrite.spec --noconfirm
# Output: dist\PortoWrite\PortoWrite.exe  (+ all dependencies alongside it)

from PyInstaller.utils.hooks import collect_all, collect_data_files

pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all('PySide6')
ebooklib_datas = collect_data_files('ebooklib')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=pyside6_binaries,
    datas=[
        ('dictionaries', 'dictionaries'),
        ('LICENSE.txt', '.'),
        *pyside6_datas,
        *ebooklib_datas,
    ],
    hiddenimports=[
        *pyside6_hiddenimports,
        'spylls',
        'spylls.hunspell',
        'spylls.hunspell.algo',
        'ebooklib',
        'ebooklib.epub',
        'docx',
        'docx.oxml',
        'mistune',
        'lxml',
        'lxml.etree',
        'lxml._elementpath',
        'lxml.html',
        'spellchecker',
        'porto_write',
        'porto_write.document',
        'porto_write.styles',
        'porto_write.project',
        'porto_write.epub_io',
        'porto_write.md_io',
        'porto_write.docx_io',
        'porto_write.epub_validator',
        'porto_write.spell',
        'porto_write.licensing',
        'porto_write.toc',
        'porto_write.constants',
        'porto_write.settings',
        'porto_write.logger',
        'porto_write.ui',
        'porto_write.ui.main_window',
        'porto_write.ui.editor_widget',
        'porto_write.ui.chapter_sidebar',
        'porto_write.ui.style_panel',
        'porto_write.ui.toolbar',
        'porto_write.ui.kindle_preview',
        'porto_write.ui.dialogs',
        'porto_write.ui.dialogs.licence_key_dialog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'IPython', 'jupyter'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PortoWrite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='portowrite.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'msvcp140.dll'],
    name='PortoWrite',
)
