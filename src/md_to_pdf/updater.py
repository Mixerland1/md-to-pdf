"""Explicit desktop updates from public GitHub Releases; no document data sent."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
import zipfile
from packaging.version import Version, InvalidVersion
from . import __version__

REPO = "Mixerland1/md-to-pdf"
API = "https://api.github.com/repos/" + REPO + "/releases?per_page=30"
DOWNLOAD = "https://github.com/" + REPO + "/releases/download/"
MAX_ZIP = 250 * 1024 * 1024
MAX_UNPACKED = 800 * 1024 * 1024
TAG = re.compile(r"v[0-9][0-9A-Za-z.+-]{0,39}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
WINDOWS = "MD-to-PDF-Windows-x64.zip"


@dataclass(frozen=True)
class Release:
    version: str
    tag: str
    asset: str
    size: int
    url: str
    checksum_url: str


def platform_asset():
    arch = platform.machine().lower()
    if sys.platform == "win32" and arch in ("amd64", "x86_64"):
        return WINDOWS
    if sys.platform == "darwin" and arch in ("arm64", "x86_64"):
        return "MD-to-PDF-macOS-" + arch + ".zip"
    return None


def _request(url):
    # Release metadata and downloads are public; never attach credentials.
    response = urlopen(Request(url, headers={"User-Agent": "MD-to-PDF/" + __version__}), timeout=20)
    if urlsplit(response.geturl()).scheme != "https":
        response.close()
        raise ValueError("Небезопасный адрес загрузки")
    return response


def _read(url, limit):
    with _request(url) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Слишком большой ответ сервера")
    return data


def select_release(releases, current, asset):
    """Only a strictly newer compatible release; stable never opts into beta."""
    installed = Version(current)
    candidates = []
    for item in releases:
        tag = item.get("tag_name", "")
        if item.get("draft") or not TAG.fullmatch(tag):
            continue
        try:
            version = Version(tag[1:])
        except InvalidVersion:
            continue
        if version <= installed or (not installed.is_prerelease and (item.get("prerelease") or version.is_prerelease)):
            continue
        assets = {a["name"]: a for a in item.get("assets", []) if a.get("state") == "uploaded" and isinstance(a.get("name"), str)}
        binary = assets.get(asset)
        checksum = assets.get("SHA256SUMS.txt")
        if not binary or not checksum:
            continue
        prefix = DOWNLOAD + tag + "/"
        size = binary.get("size")
        if type(size) is not int or not 0 < size <= MAX_ZIP:
            continue
        if binary.get("browser_download_url") != prefix + asset or checksum.get("browser_download_url") != prefix + "SHA256SUMS.txt":
            continue
        candidates.append((version, Release(str(version), tag, asset, size, prefix + asset, prefix + "SHA256SUMS.txt")))
    return max(candidates, key=lambda x: x[0])[1] if candidates else None


def check():
    asset = platform_asset()
    if not asset:
        return None
    releases = json.loads(_read(API, 2_000_000))
    if not isinstance(releases, list):
        raise ValueError("Не удалось прочитать список версий")
    return select_release(releases, __version__, asset)


def checksum_for(text, asset):
    matches = []
    for line in text.splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2 and parts[1].lstrip("*") == asset:
            matches.append(parts[0].lower())
    if len(matches) != 1 or not SHA.fullmatch(matches[0]):
        raise ValueError("Нет однозначной контрольной суммы архива")
    return matches[0]


def download(release, directory):
    expected = checksum_for(_read(release.checksum_url, 64_000).decode("ascii"), release.asset)
    target = Path(directory) / release.asset
    digest = hashlib.sha256()
    total = 0
    try:
        with _request(release.url) as response, target.open("xb") as stream:
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > release.size or total > MAX_ZIP:
                    raise ValueError("Неверный размер архива")
                digest.update(chunk)
                stream.write(chunk)
        if total != release.size or digest.hexdigest() != expected:
            raise ValueError("Проверка SHA-256 не пройдена")
        return target
    except Exception:
        target.unlink(missing_ok=True)
        raise


def unpack_windows(archive, destination):
    """Extract only the managed exe and runtime; reject unsafe paths and links."""
    destination = Path(destination)
    seen = set()
    total = 0
    with zipfile.ZipFile(archive) as bundle:
        for info in bundle.infolist():
            raw = info.filename
            # Windows Compress-Archive may use backslashes.
            raw = raw.replace("\\", "/")
            parts = PurePosixPath(raw).parts
            if not parts or raw.startswith("/") or any(p in (".", "..") or ":" in p or p.endswith((".", " ")) for p in parts):
                raise ValueError("Небезопасный путь в архиве")
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("Ссылки в Windows-архиве не поддерживаются")
            if parts[0] != "MD-to-PDF":
                raise ValueError("Неверная структура дистрибутива")
            if len(parts) < 2 or parts[1] not in ("MD-to-PDF.exe", "_internal"):
                continue
            if parts[1] == "MD-to-PDF.exe" and (len(parts) != 2 or info.is_dir()):
                raise ValueError("Неверная структура EXE")
            key = "/".join(parts).casefold()
            if key in seen:
                raise ValueError("Повторяющийся путь в архиве")
            seen.add(key)
            if any(re.fullmatch(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", p, re.I) for p in parts):
                raise ValueError("Зарезервированное имя Windows")
            total += info.file_size
            if total > MAX_UNPACKED:
                raise ValueError("Слишком большой распакованный архив")
            target = destination.joinpath(*parts[1:])
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(info) as src, target.open("xb") as dst:
                    shutil.copyfileobj(src, dst)
    if not (destination / "MD-to-PDF.exe").is_file() or not (destination / "_internal").is_dir() or not any((destination / "_internal").iterdir()):
        raise ValueError("Неполный дистрибутив")


def prepare_windows(release):
    if release.asset != WINDOWS or not getattr(sys, "frozen", False) or sys.platform != "win32":
        raise ValueError("Автоматическая замена поддерживается только в Windows-сборке")
    executable = Path(sys.executable).resolve()
    install = executable.parent
    if executable.name.lower() != "md-to-pdf.exe" or not (install / "_internal").is_dir():
        raise ValueError("Не удалось определить папку приложения")
    stage = Path(tempfile.mkdtemp(prefix=".md-to-pdf-update-", dir=install.parent))
    try:
        archive = download(release, stage)
        unpack_windows(archive, stage / "new")
        archive.unlink()
        helper = stage / "update.ps1"
        shutil.copyfile(Path(__file__).with_name("update.ps1"), helper)
        powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        subprocess.Popen([str(powershell), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                          "-File", str(helper), "-InstallDir", str(install), "-Stage", str(stage),
                          "-AppPid", str(os.getpid())], cwd=stage, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return stage
