"""Safe GitHub Releases updater for the packaged Pet Reminder app."""

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from threading import Event
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PyQt5.QtCore import QObject, QThread, pyqtSignal
from app_version import APP_VERSION


CURRENT_VERSION = APP_VERSION
GITHUB_API_URL = "https://api.github.com/repos/kaiCATs/pet-reminder/releases/latest"
USER_AGENT = f"PetReminder/{CURRENT_VERSION}"
INSTALLER_RE = re.compile(
    r"^PetReminder_Setup_v?(\d+(?:\.\d+){1,2})_GUI\.exe$",
    re.IGNORECASE,
)
SHA256_RE = re.compile(r"\b([0-9a-fA-F]{64})\b")


class UpdateError(Exception):
    """Expected network, package, or checksum error during an update."""


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    version_tuple: tuple
    tag_name: str
    asset_name: str
    asset_url: str
    sha256: str | None = None
    checksum_url: str | None = None


def parse_version(value):
    """Return a normalized three-part version tuple or None."""
    match = re.search(r"\d+(?:\.\d+){0,3}", str(value or ""))
    if not match:
        return None
    parts = [int(part) for part in match.group(0).split(".")[:3]]
    return tuple((parts + [0, 0, 0])[:3])


def format_version(version_tuple):
    return ".".join(str(part) for part in version_tuple)


def _url_is_allowed(url, allowed_hosts):
    parsed = urlparse(str(url or ""))
    return parsed.scheme == "https" and parsed.hostname in allowed_hosts


def _request(url, accept="*/*"):
    request = Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": USER_AGENT,
        },
    )
    try:
        return urlopen(request, timeout=15)
    except HTTPError as exc:
        if exc.code == 404:
            raise UpdateError("not_found") from exc
        raise UpdateError("network") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise UpdateError("network") from exc


def _fetch_release():
    if not _url_is_allowed(GITHUB_API_URL, {"api.github.com"}):
        raise UpdateError("invalid_source")
    try:
        with _request(GITHUB_API_URL, "application/vnd.github+json") as response:
            try:
                return json.loads(response.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise UpdateError("invalid_release") from exc
    except UpdateError as exc:
        # A repository without any published Release is a normal state while
        # the first public version is being prepared, not a user-facing error.
        if str(exc) == "not_found":
            return {}
        raise


def _asset_url(asset):
    url = asset.get("browser_download_url", "")
    if not _url_is_allowed(url, {"github.com", "objects.githubusercontent.com"}):
        raise UpdateError("invalid_asset")
    return url


def _digest_from_asset(asset):
    digest = str(asset.get("digest") or "")
    if digest.lower().startswith("sha256:"):
        digest = digest.split(":", 1)[1]
    return digest.lower() if SHA256_RE.fullmatch(digest) else None


def latest_release(current_version=CURRENT_VERSION):
    """Find a newer signed-by-checksum GUI installer in the latest release."""
    release = _fetch_release()
    if release.get("draft") or release.get("prerelease"):
        return None

    current = parse_version(current_version)
    release_version = parse_version(release.get("tag_name") or release.get("name"))
    if current is None or release_version is None or release_version <= current:
        return None

    installers = []
    for asset in release.get("assets", []):
        name = str(asset.get("name") or "")
        match = INSTALLER_RE.fullmatch(name)
        if match:
            installers.append((parse_version(match.group(1)), asset))
    installers = [item for item in installers if item[0] is not None]
    if not installers:
        return None

    _, installer = max(installers, key=lambda item: item[0])
    installer_name = str(installer.get("name"))
    checksum_asset = None
    checksum_names = {
        installer_name.lower() + ".sha256",
        "sha256sums",
        "sha256sums.txt",
    }
    for asset in release.get("assets", []):
        if str(asset.get("name") or "").lower() in checksum_names:
            checksum_asset = asset
            break

    return UpdateInfo(
        version=format_version(release_version),
        version_tuple=release_version,
        tag_name=str(release.get("tag_name") or ""),
        asset_name=installer_name,
        asset_url=_asset_url(installer),
        sha256=_digest_from_asset(installer),
        checksum_url=_asset_url(checksum_asset) if checksum_asset else None,
    )


def _checksum_from_text(text, asset_name):
    file_match = re.search(
        rf"([0-9a-fA-F]{{64}})\s+[* ]?{re.escape(asset_name)}(?:\s|$)",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if file_match:
        return file_match.group(1).lower()
    hashes = SHA256_RE.findall(text)
    if len(hashes) == 1:
        return hashes[0].lower()
    return None


def _download_checksum(url, asset_name):
    if not _url_is_allowed(url, {"github.com", "objects.githubusercontent.com"}):
        raise UpdateError("invalid_checksum")
    with _request(url) as response:
        try:
            text = response.read().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UpdateError("invalid_checksum") from exc
    checksum = _checksum_from_text(text, asset_name)
    if not checksum:
        raise UpdateError("checksum_missing")
    return checksum


class CheckWorker(QThread):
    found = pyqtSignal(object)
    none = pyqtSignal()
    failed = pyqtSignal(str)

    def run(self):
        try:
            info = latest_release()
            if info is None:
                self.none.emit()
            else:
                self.found.emit(info)
        except UpdateError as exc:
            self.failed.emit(str(exc))


class DownloadWorker(QThread):
    progress = pyqtSignal(int)
    ready = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.info = info
        self._cancel = Event()

    def cancel(self):
        self._cancel.set()

    def run(self):
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp(prefix="PetReminder-update-")
            installer_path = os.path.join(temp_dir, self.info.asset_name)
            with _request(self.info.asset_url) as response, open(installer_path, "wb") as output:
                total = int(response.headers.get("Content-Length") or 0)
                received = 0
                while True:
                    if self._cancel.is_set():
                        raise UpdateError("cancelled")
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    output.write(chunk)
                    received += len(chunk)
                    if total > 0:
                        self.progress.emit(min(100, int(received * 100 / total)))

            expected = self.info.sha256
            if not expected and self.info.checksum_url:
                expected = _download_checksum(self.info.checksum_url, self.info.asset_name)
            if not expected:
                raise UpdateError("checksum_missing")

            digest = hashlib.sha256()
            with open(installer_path, "rb") as package:
                for chunk in iter(lambda: package.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest().lower() != expected.lower():
                raise UpdateError("checksum_mismatch")

            self.progress.emit(100)
            self.ready.emit(installer_path)
        except UpdateError as exc:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
            self.failed.emit(str(exc))
        except (OSError, ValueError) as exc:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
            self.failed.emit("download")


class UpdateManager(QObject):
    update_available = pyqtSignal(object)
    no_update = pyqtSignal()
    check_failed = pyqtSignal(str)
    download_progress = pyqtSignal(int)
    download_ready = pyqtSignal(str)
    download_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._check_worker = None
        self._download_worker = None

    def check(self):
        if self._check_worker is not None or self._download_worker is not None:
            return False
        worker = CheckWorker(self)
        self._check_worker = worker
        worker.found.connect(self._handle_found)
        worker.none.connect(self._handle_none)
        worker.failed.connect(self._handle_failed)
        worker.finished.connect(self._check_finished)
        worker.start()
        return True

    def _handle_found(self, info):
        # Release the check slot before the UI asks to start downloading.
        self._check_worker = None
        self.update_available.emit(info)

    def _handle_none(self):
        self._check_worker = None
        self.no_update.emit()

    def _handle_failed(self, reason):
        self._check_worker = None
        self.check_failed.emit(reason)

    def _check_finished(self):
        self._check_worker = None

    def download(self, info):
        if self._check_worker is not None or self._download_worker is not None:
            return False
        worker = DownloadWorker(info, self)
        self._download_worker = worker
        worker.progress.connect(self.download_progress)
        worker.ready.connect(self.download_ready)
        worker.failed.connect(self.download_failed)
        worker.finished.connect(self._download_finished)
        worker.start()
        return True

    def _download_finished(self):
        self._download_worker = None

    def cancel_download(self):
        if self._download_worker is not None:
            self._download_worker.cancel()

    def shutdown(self):
        if self._download_worker is not None and self._download_worker.isRunning():
            self._download_worker.cancel()
            self._download_worker.wait(12000)
        if self._check_worker is not None and self._check_worker.isRunning():
            self._check_worker.wait(17000)
