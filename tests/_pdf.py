"""Compare two PDFs on what they say rather than on how well they compressed.

Both brief tests used to hash raw bytes, and that turned out to guard nothing
where it mattered most. A PDF written by matplotlib stores its page content,
its font subsets and its embedded images as zlib streams, and zlib is free to
reach the same decompressed bytes through a different number of compressed
ones. Two builds of the same brief, from the same artifacts, with the same
matplotlib and the same font subsets, differed by 986 bytes on this project
while every one of their 162 streams decompressed to identical content and the
total decompressed size matched exactly.

So a raw-byte comparison fails whenever the committed file and the regenerated
one were produced against different zlib builds -- which is every CI run here,
because the briefs are generated on a developer machine and checked on a Linux
runner. A test that cannot pass is not a strict test; it is an ignored one, and
an ignored test is how a brief goes stale unnoticed.

``content_digest`` hashes the decompressed streams instead. A changed number, a
changed sentence, a changed figure and a changed font subset all still move it.
A different zlib does not.
"""

from __future__ import annotations

import hashlib
import re
import zlib
from pathlib import Path

_STREAM = re.compile(rb"stream\r?\n(.*?)endstream", re.S)


def content_streams(pdf: Path) -> list[bytes]:
    """Every stream in the file, decompressed where it is deflate-compressed.

    A stream that does not decompress is kept as it stands rather than skipped:
    whatever it is, a change in it should still be caught.
    """
    out: list[bytes] = []
    for match in _STREAM.finditer(pdf.read_bytes()):
        raw = match.group(1)
        try:
            out.append(zlib.decompress(raw))
        except zlib.error:
            out.append(raw)
    return out


def content_digest(pdf: Path) -> str:
    """A digest of what the PDF renders, independent of compression."""
    digest = hashlib.sha256()
    streams = content_streams(pdf)
    digest.update(str(len(streams)).encode())
    for stream in streams:
        digest.update(hashlib.sha256(stream).digest())
    return digest.hexdigest()
