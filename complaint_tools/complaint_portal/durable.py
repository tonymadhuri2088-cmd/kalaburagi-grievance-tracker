"""Keeps the portal's data when the host restarts.

Free hosts (Render's free plan) wipe the disk every time the service sleeps, restarts or is redeployed. The portal
stores everything in one SQLite file plus a photos folder, so this module keeps a copy of both in a Postgres database
(Render offers a free one) and puts it back when the service starts.

Nothing here changes how the portal works. If DATABASE_URL is not set, or the Postgres driver is missing, or the
database cannot be reached, the portal just runs as before and says so in the log.

A copy is made a few seconds after any change (never more often than every few seconds), and once more when the
host asks the service to stop.
"""

import io
import os
import sqlite3
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import unquote, urlsplit

TABLE = "portal_snapshot"
PHOTO_LIMIT_BYTES = 60_000_000   # photos beyond this total are left out of the copy; the database itself always goes


def database_url() -> Optional[str]:
    url = (os.environ.get("DATABASE_URL") or "").strip()
    return url or None


def _connect(url: str):
    """Open a Postgres connection with the pure-Python driver pg8000. Raises if it is not installed."""
    import pg8000.native  # imported here so the portal runs without it

    parts = urlsplit(url)
    host = parts.hostname or "localhost"
    internal = "." not in host   # Render's private address has no dots; the public one does
    ssl_context: Any = None
    if not internal and host not in ("localhost", "127.0.0.1"):
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    return pg8000.native.Connection(
        user=unquote(parts.username or ""), password=unquote(parts.password or ""), host=host,
        port=parts.port or 5432, database=(parts.path or "/").lstrip("/"), ssl_context=ssl_context, timeout=20,
    )


def _ensure_table(con) -> None:
    con.run(f"CREATE TABLE IF NOT EXISTS {TABLE} (id INTEGER PRIMARY KEY, saved_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
            f"data BYTEA NOT NULL)")


def _pack(db_path: Path) -> bytes:
    """One zip holding a consistent copy of the database and the photos folder."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        source = sqlite3.connect(str(db_path))
        try:
            copy_path = db_path.with_name(db_path.name + ".copy")
            if copy_path.exists():
                copy_path.unlink()
            target = sqlite3.connect(str(copy_path))
            try:
                source.backup(target)   # safe while the portal is writing
            finally:
                target.close()
        finally:
            source.close()
        archive.write(copy_path, "portal.db")
        copy_path.unlink()
        photos = db_path.parent / "photos"
        total = 0
        if photos.is_dir():
            for item in sorted(photos.iterdir()):
                if item.is_file():
                    total += item.stat().st_size
                    if total > PHOTO_LIMIT_BYTES:
                        break
                    archive.write(item, f"photos/{item.name}")
    return buffer.getvalue()


def _unpack(data: bytes, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in archive.namelist():
            if name == "portal.db":
                db_path.write_bytes(archive.read(name))
            elif name.startswith("photos/") and "/" not in name[len("photos/"):] and not name.endswith("/"):
                folder = db_path.parent / "photos"
                folder.mkdir(parents=True, exist_ok=True)
                (folder / Path(name).name).write_bytes(archive.read(name))


def restore(db_path: str, force: bool = False, log: Callable[[str], None] = print) -> str:
    """Put the saved copy back, if there is one and this host has no database yet. Returns what happened."""
    url = database_url()
    if not url:
        return "DATABASE_URL is not set: data is kept only on this host's disk."
    path = Path(db_path)
    if path.exists() and path.stat().st_size > 0 and not force:
        return "A database file already exists here; the saved copy was not used."
    try:
        con = _connect(url)
        try:
            _ensure_table(con)
            rows = con.run(f"SELECT data FROM {TABLE} WHERE id = 1")
        finally:
            con.close()
    except Exception as error:   # driver missing, database asleep, wrong address ...
        log(f"Saved copy could not be read ({error.__class__.__name__}: {error}). Starting with an empty database.")
        return "unavailable"
    if not rows:
        return "No saved copy yet. Starting with an empty database."
    _unpack(bytes(rows[0][0]), path)
    return "Restored the saved copy of the database."


def save(db_path: str) -> int:
    """Write the copy now. Returns its size in bytes. Raises on failure."""
    url = database_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    data = _pack(Path(db_path))
    con = _connect(url)
    try:
        _ensure_table(con)
        con.run(f"INSERT INTO {TABLE} (id, saved_at, data) VALUES (1, now(), :d) "
                f"ON CONFLICT (id) DO UPDATE SET saved_at = now(), data = :d", d=data)
    finally:
        con.close()
    return len(data)


class Saver:
    """Background thread: copies the data soon after it changes."""

    def __init__(self, db_path: str, every_seconds: float = 5.0, log: Callable[[str], None] = print) -> None:
        self.db_path = db_path
        self.every = every_seconds
        self.log = log
        self._dirty = threading.Event()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._failed_once = False
        self.last_saved: Optional[float] = None
        self.thread = threading.Thread(target=self._run, daemon=True)

    @property
    def enabled(self) -> bool:
        return database_url() is not None

    def changed(self) -> None:
        """Call after any write to the database."""
        self._dirty.set()

    def start(self) -> None:
        if self.enabled:
            self._dirty.set()   # save once at start, so the first copy exists
            self.thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            self._dirty.wait(timeout=1.0)
            if self._dirty.is_set() and not self._stop.is_set():
                self.flush()
                self._stop.wait(self.every)

    def flush(self) -> bool:
        """Save now if anything changed since the last copy."""
        if not self._dirty.is_set():
            return True
        with self._lock:
            self._dirty.clear()
            try:
                size = save(self.db_path)
                self.last_saved = time.time()
                if self._failed_once:
                    self.log("Saved copy of the database works again.")
                    self._failed_once = False
                return size > 0
            except Exception as error:
                self._dirty.set()   # try again next time
                if not self._failed_once:
                    self.log(f"Could not save a copy of the database ({error.__class__.__name__}: {error}).")
                    self._failed_once = True
                return False

    def stop(self) -> None:
        """Last copy before the service ends."""
        self._stop.set()
        if self.enabled:
            self._dirty.set()
            self.flush()
