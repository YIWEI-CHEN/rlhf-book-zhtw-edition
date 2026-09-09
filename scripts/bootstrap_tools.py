"""Download pinned portable ebook tools into ignored .tools (never install TeX)."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / ".tools"
NOTO = "https://raw.githubusercontent.com/notofonts/noto-cjk/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Serif/OTF/TraditionalChinese/"
ASSETS = [
    ("fonts/NotoSerifCJKtc-Regular.otf", NOTO + "NotoSerifCJKtc-Regular.otf",
     "234301038e76e7c35c43113785024700c4e4fe7bdce1d1fbbc42fca7e6683798", None, False),
    ("fonts/NotoSerifCJKtc-Bold.otf", NOTO + "NotoSerifCJKtc-Bold.otf",
     "a4441a76dbf56719600c5dcbd5b5e5a068a20944cc41c959487a657133576ee6", None, False),
    ("epubcheck-5.3.0.zip", "https://github.com/w3c/epubcheck/releases/download/v5.3.0/epubcheck-5.3.0.zip",
     "6c07e68584b2e2ce2f89fe06e1246dfead3eb36b46b340e7d93524f29dcff6c5", "epubcheck", False),
    ("pandoc-3.11-windows-x86_64.zip", "https://github.com/jgm/pandoc/releases/download/3.11/pandoc-3.11-windows-x86_64.zip",
     "2ab72baf2399450e148ddf7a2a8689806c42e1bba71862b57e220fd9b8456d3d", "pandoc", True),
    ("temurin-21.0.12.1-windows-x64.zip", "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.12.1%2B1/OpenJDK21U-jre_x64_windows_hotspot_21.0.12.1_1.zip",
     "d35f31e712f0fcf6ac5a093edc90204fbff22f720ba3950bd09d331d5e621636", "java", True),
]


def download(path: Path, url: str, digest: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == digest:
        return
    print(f"Downloading {path.name}", flush=True)
    temporary = path.with_suffix(path.suffix + ".download")
    with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as output:
        shutil.copyfileobj(response, output)
    if hashlib.sha256(temporary.read_bytes()).hexdigest() != digest:
        raise ValueError(f"Checksum mismatch: {path.name}; refusing to use download")
    temporary.replace(path)


def extract(archive: Path, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    base = directory.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (base / member.filename).resolve()
            if not target.is_relative_to(base):
                raise ValueError(f"Unsafe archive path: {member.filename}")
        bundle.extractall(base)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-mathjax", action="store_true", help="PDF-only setup")
    args = parser.parse_args()
    for filename, url, digest, destination, windows_only in ASSETS:
        if windows_only and os.name != "nt":
            continue
        path = TOOLS / filename
        download(path, url, digest)
        if destination:
            extract(path, TOOLS / destination)
    if not args.skip_mathjax:
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if not npm:
            raise FileNotFoundError("Install Node.js 18+ (including npm) and rerun")
        target = TOOLS / "mathjax"
        target.mkdir(parents=True, exist_ok=True)
        for name in ("package.json", "package-lock.json"):
            shutil.copy2(ROOT / "tooling" / "mathjax" / name, target / name)
        subprocess.run([npm, "ci", "--prefix", str(target), "--ignore-scripts",
                        "--no-audit", "--no-fund", "--registry=https://registry.npmjs.org"], check=True)
    print("Portable tools ready. PDF additionally requires XeLaTeX; see docs/EXPORT.md.")


if __name__ == "__main__":
    main()
