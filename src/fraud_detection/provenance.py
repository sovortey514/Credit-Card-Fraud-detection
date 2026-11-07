"""Dataset provenance helpers."""

from hashlib import sha256


def sha256_file(path, chunk_size=1024 * 1024):
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
