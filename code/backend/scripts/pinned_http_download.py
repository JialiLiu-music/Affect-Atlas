"""Fetch pinned HF files using GET when a mirror omits SDK HEAD metadata.

Verify LFS SHA256 for weights and Git blob SHA1 for all small source/config
files against the fixed-revision repository API. No gated resource access.
"""
import hashlib
import os
from pathlib import Path
import time


def fetch_pinned_http(destination: Path, model_id: str, revision: str):
    import requests
    endpoint = os.getenv('HF_ENDPOINT', 'https://huggingface.co').rstrip('/')
    session = requests.Session()
    response = session.get(f'{endpoint}/api/models/{model_id}/revision/{revision}',
                           params={'blobs': 'true'}, timeout=30)
    response.raise_for_status()
    info = response.json()
    if info.get('sha') != revision:
        raise RuntimeError('Repository API revision differs from pinned commit')
    selected = {r['rfilename']: r for r in info['siblings'] if r['rfilename'] in {
        'config.json', 'configuration_MERT.py', 'modeling_MERT.py',
        'preprocessor_config.json', 'pytorch_model.bin', 'README.md'}}
    if len(selected) != 6:
        raise RuntimeError('Pinned repository file set is incomplete')
    destination.mkdir(parents=True, exist_ok=True)

    def verified(path, metadata):
        if not path.is_file() or path.stat().st_size != metadata['size']:
            return False
        if 'lfs' in metadata:
            digest = hashlib.sha256()
            expected = metadata['lfs']['sha256']
        else:
            digest = hashlib.sha1()
            digest.update(f"blob {metadata['size']}\0".encode())
            expected = metadata['blobId']
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
        return digest.hexdigest() == expected

    for name, metadata in selected.items():
        path = destination / name
        if verified(path, metadata):
            print('FILE_ALREADY_VERIFIED', name, flush=True)
            continue
        if path.exists():
            raise RuntimeError('Unexpected existing file; refusing overwrite: ' + name)
        partial = destination / (name + '.http-part')
        if verified(partial, metadata):
            partial.replace(path)
            print('RESUMED_FILE_VERIFIED', name, metadata['size'], flush=True)
            continue
        previous = partial.stat().st_size if partial.exists() else 0
        headers = {'Range': f'bytes={previous}-'} if previous else {}
        with session.get(f'{endpoint}/{model_id}/resolve/{revision}/{name}',
                         headers=headers, stream=True, timeout=(20, 120)) as download:
            download.raise_for_status()
            if previous and download.status_code == 206:
                if not download.headers.get('Content-Range', '').startswith(f'bytes {previous}-'):
                    raise RuntimeError('Incorrect resume range')
                mode, count = 'ab', previous
            else:
                mode, count = 'wb', 0
            last = time.monotonic()
            with partial.open(mode) as output:
                for chunk in download.iter_content(1024 * 1024):
                    if not chunk:
                        continue
                    count += len(chunk)
                    if count > metadata['size']:
                        raise RuntimeError('Downloaded bytes exceed recorded file size')
                    output.write(chunk)
                    if time.monotonic() - last > 5:
                        print('DOWNLOAD_PROGRESS', name, count, metadata['size'], flush=True)
                        last = time.monotonic()
        if not verified(partial, metadata):
            partial.unlink(missing_ok=True)
            raise RuntimeError('Downloaded checksum or length mismatch: ' + name)
        partial.replace(path)
        print('FILE_VERIFIED', name, metadata['size'], flush=True)
    return info
