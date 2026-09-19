"""Prevent competing batch writers and retain exact reproducible source versions."""
from contextlib import contextmanager
from collections.abc import Iterator
import fcntl
import hashlib
import os
from pathlib import Path
import tarfile


@contextmanager
def exclusive_batch(root: Path) -> Iterator[None]:
    """Hold a kernel lock; process termination releases it without stale-lock tricks."""
    with (root/'.batch.lock').open('a+') as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('This batch already has a running writer') from exc
        try:
            handle.seek(0)
            handle.truncate()
            handle.write(str(os.getpid())+'\n')
            handle.flush()
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def archive_sources(root: Path, sources: dict[str, str]) -> None:
    """Create a source archive once; verify existing content before reuse."""
    for name, digest in sources.items():
        path=Path(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Archive members must be repository-relative source paths')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('Source changed before archiving')
    target=root/'source.tar.gz'
    if not target.exists():
        with target.open('xb') as handle:
            with tarfile.open(fileobj=handle, mode='w:gz') as archive:
                for name in sorted(sources):
                    archive.add(name, arcname=name)
    with tarfile.open(target) as archive:
        if sorted(m.name for m in archive.getmembers()) != sorted(sources):
            raise ValueError('Archived source membership differs from batch contract')
        for name,digest in sources.items():
            if hashlib.sha256(archive.extractfile(name).read()).hexdigest()!=digest:
                raise ValueError('Archived source content differs from batch contract')
