import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rag.indexing.identity import chunk_id


def test_chunk_id_is_stable_for_the_same_snapshot() -> None:
    chunk = {
        "repository_id": "payments-service",
        "commit_sha": "a" * 40,
        "file_path": "src/payment.py",
        "start_line": 10,
        "end_line": 12,
        "content": "def charge(): pass",
    }

    assert chunk_id(chunk) == chunk_id(chunk)


def test_chunk_id_changes_when_commit_changes() -> None:
    chunk = {
        "repository_id": "payments-service",
        "commit_sha": "a" * 40,
        "file_path": "src/payment.py",
        "start_line": 10,
        "end_line": 12,
        "content": "def charge(): pass",
    }
    newer_chunk = {**chunk, "commit_sha": "b" * 40}

    assert chunk_id(chunk) != chunk_id(newer_chunk)
