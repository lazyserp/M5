# """Stable identity helpers for repository-aware code chunks."""

# from __future__ import annotations

# import hashlib
# from typing import Any


# def chunk_id(chunk: dict[str, Any]) -> str:
#     """Return a deterministic ID for a chunk in one immutable repository snapshot."""
#     identity = "\x1f".join(
#         str(chunk.get(key, ""))
#         for key in (
#             "repository_id",
#             "commit_sha",
#             "file_path",
#             "start_line",
#             "end_line",
#             "content",
#         )
#     )
#     return hashlib.sha256(identity.encode("utf-8")).hexdigest()
