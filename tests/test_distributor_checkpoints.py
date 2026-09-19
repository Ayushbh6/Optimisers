"""Checkpoint integrity checks; all temporary files use repository-local pytest storage."""
import hashlib
from pathlib import Path
import pytest

from src.distributor_research import checkpoints


def test_competing_writer_is_rejected_and_lock_is_released(tmp_path):
    with checkpoints.exclusive_batch(tmp_path):
        with pytest.raises(RuntimeError,match='running writer'):
            with checkpoints.exclusive_batch(tmp_path):
                pass
    with checkpoints.exclusive_batch(tmp_path):
        pass


def test_source_archive_survives_and_detects_changed_code(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path('source.py').write_text('value = 1\n')
    sources={'source.py':hashlib.sha256(Path('source.py').read_bytes()).hexdigest()}
    checkpoints.archive_sources(tmp_path,sources)
    checkpoints.archive_sources(tmp_path,sources)
    Path('source.py').write_text('value = 2\n')
    with pytest.raises(ValueError,match='Source changed'):
        checkpoints.archive_sources(tmp_path,sources)
