# Native Windows PyInstaller build; run from the repository root.
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

repo = Path(SPECPATH).parent
media = repo / 'build' / 'windows-media'
datas = [
    (str(repo / 'multitrack' / 'static'), 'multitrack/static'),
    (str(repo / 'models'), 'models'),
    (str(repo / 'LICENSE'), 'notices'),
    (str(repo / 'docs' / 'licenses'), 'notices/licenses'),
    (str(repo / 'docs' / 'THIRD_PARTY.md'), 'notices'),
    (str(media / 'source'), 'notices/ffmpeg'),
    (str(repo / 'build' / 'THIRD-PARTY-LICENSES.txt'), 'notices'),
]
binaries = [(str(media / 'bin' / 'ffmpeg.exe'), 'ffmpeg/bin'),
            (str(media / 'bin' / 'ffprobe.exe'), 'ffmpeg/bin')]
hidden = collect_submodules('scipy._external') + ['multitrack.worker', 'multitrack.remix', 'uvicorn.logging', 'uvicorn.loops.auto',
          'uvicorn.protocols.http.h11_impl', 'uvicorn.lifespan.on']
for package in ['torch', 'torchaudio', 'sherpa_onnx', 'soundfile']:
    data, binary, imports = collect_all(package)
    datas += data
    binaries += binary
    hidden += imports
# Eager inference needs the DLLs, not the C++ SDK headers or CMake development files.
datas = [item for item in datas if not item[1].replace('\\', '/').startswith(('torch/include', 'torch/share/cmake'))]
for distribution in ['multitrackert-audio', 'torch', 'torchaudio']:
    datas += copy_metadata(distribution)
a = Analysis([str(repo / 'windows' / 'entry.py')], pathex=[str(repo)],
             binaries=binaries, datas=datas, hiddenimports=hidden,
             excludes=['pytest', 'IPython', 'tkinter'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='MultitrackertAudio',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='MultitrackertAudio')
