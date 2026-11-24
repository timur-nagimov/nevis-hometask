"""Download the embedding model at a pinned revision, for the model stage of the image.

Standard library only, so the stage can run it before anything is installed:
    python -I scripts/fetch_model.py <target-dir>
Every file is checked against its pinned sha256 and size and tried several times; when all attempts fail,
the error says what the download needs.

Environment: HF_ENDPOINT, a mirror (unset or empty: Hugging Face itself);
urllib honours HTTPS_PROXY and SSL_CERT_FILE.
"""

import argparse
import hashlib
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = 'MongoDB/mdbr-leaf-ir'
REVISION = '4262131b32c3182bd06e67e92ae69d7bd66e0c5c'  # a commit, so the files behind it cannot change
FILES = {  # path in the repository -> (sha256, size in bytes)
    'onnx/model.onnx': ('9546f40fdbf194103951b7dd3bbf82a14489cab8cc55e9540c13f1dce957573f', 60894),
    'onnx/model.onnx_data': ('c509bc3c7759c3d851cf610b02b47908e5456f334c19743fa74b1a4cee8fdc27', 91444224),
    'tokenizer.json': ('da0e79933b9ed51798a3ae27893d3c5fa4a201126cef75586296df9b4d2c62a0', 711661),
}
DEFAULT_ENDPOINT = 'https://huggingface.co'
# Empty counts as unset: a build argument can be emptied, not unset.
ENDPOINT = (os.environ.get('HF_ENDPOINT') or DEFAULT_ENDPOINT).rstrip('/')
ATTEMPTS = 5  # per file
TIMEOUT_SECONDS = 60  # to connect and for each read, so a stalled transfer fails instead of hanging
READ_BYTES = 1 << 20  # files go to disk in pieces of this size, never whole through memory
USER_AGENT = 'model-fetch/1.0'
BYTES_PER_MB = 1_000_000  # the progress lines count decimal megabytes


def fetch(rel: str, sha256: str, size: int, target: Path) -> float:
    """Download one file to `target / rel` and verify it; returns the seconds the good attempt took."""
    url = f'{ENDPOINT}/{REPO}/resolve/{REVISION}/{rel}'
    dest = target / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    headers = {'User-Agent': USER_AGENT}
    last: Exception | None = None
    for attempt in range(1, ATTEMPTS + 1):
        started = time.perf_counter()
        try:
            digest = hashlib.sha256()
            # a new request per attempt: behind a proxy, urlopen alters the one it is given
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as resp, open(dest, 'wb') as out:
                while chunk := resp.read(READ_BYTES):
                    digest.update(chunk)
                    out.write(chunk)
            if digest.hexdigest() != sha256 or dest.stat().st_size != size:
                raise ValueError(
                    f'checksum/size mismatch for {rel}: '
                    f'got {digest.hexdigest()} / {dest.stat().st_size} bytes'
                )
            return time.perf_counter() - started
        except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError) as exc:
            last = exc
            print(
                f'  attempt {attempt}/{ATTEMPTS} for {rel} failed: {type(exc).__name__}: {exc}',
                file=sys.stderr,
            )
            if attempt < ATTEMPTS:  # the last failure ends the build without waiting
                time.sleep(2**attempt)
    raise SystemExit(
        f'\nERROR: could not download {url}\n  last error: {last}\n'
        '  The image build needs HTTPS access to huggingface.co and its CDN (*.hf.co).\n'
        '  Behind a proxy pass --build-arg HTTPS_PROXY=...; for a mirror pass --build-arg HF_ENDPOINT=...\n'
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('target', type=Path, metavar='target-dir', help='where the model files are written')
    target: Path = parser.parse_args(argv).target
    width = max(map(len, FILES))
    total = 0.0
    for rel, (sha256, size) in FILES.items():
        took = fetch(rel, sha256, size, target)
        total += took
        megabytes = size / BYTES_PER_MB
        print(f'ok {rel:{width}} {megabytes:6.1f} MB in {took:5.1f}s ({megabytes / took:5.1f} MB/s)')
    print(f'total {total:.1f}s')


if __name__ == '__main__':
    main()
