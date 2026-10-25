"""Small synthetic transport fixtures verify checksums and pinned revision.

No test weights enter the production model directory.
"""
import hashlib
from types import SimpleNamespace
import pytest
from scripts.pinned_http_download import fetch_pinned_http

NAMES = ['config.json', 'configuration_MERT.py', 'modeling_MERT.py',
         'preprocessor_config.json', 'pytorch_model.bin', 'README.md']


class Response:
    def __init__(self, data=None, content=b''):
        self.data = data
        self.content = content
        self.status_code = 200
        self.headers = {}
    def json(self): return self.data
    def raise_for_status(self): pass
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def iter_content(self, _): yield self.content


def setup_transport(monkeypatch, revision='commit', corrupt=False):
    files = {name: ('test-only-' + name).encode() for name in NAMES}
    metadata = []
    for name, body in files.items():
        item = dict(rfilename=name, size=len(body), blobId=hashlib.sha1(f'blob {len(body)}\0'.encode() + body).hexdigest())
        if name.endswith('.bin'):
            item['lfs'] = dict(sha256='0' * 64 if corrupt else hashlib.sha256(body).hexdigest())
        metadata.append(item)
    def get(url, **kwargs):
        if '/api/models/' in url:
            return Response(dict(sha=revision, siblings=metadata))
        return Response(content=files[url.rsplit('/', 1)[1]])
    monkeypatch.setattr('requests.Session', lambda: SimpleNamespace(get=get))
    return files


def test_blob_and_lfs_checksums_and_existing_resume(monkeypatch, tmp_path):
    files = setup_transport(monkeypatch)
    fetch_pinned_http(tmp_path, 'model', 'commit')
    fetch_pinned_http(tmp_path, 'model', 'commit')
    assert {name: (tmp_path/name).read_bytes() for name in NAMES} == files


def test_weight_checksum_mismatch_rejected(monkeypatch, tmp_path):
    setup_transport(monkeypatch, corrupt=True)
    with pytest.raises(RuntimeError, match='checksum'):
        fetch_pinned_http(tmp_path, 'model', 'commit')
    assert not (tmp_path/'pytorch_model.bin').exists()


def test_other_revision_rejected_before_files(monkeypatch, tmp_path):
    setup_transport(monkeypatch, revision='other-commit')
    with pytest.raises(RuntimeError, match='revision'):
        fetch_pinned_http(tmp_path, 'model', 'commit')
    assert not list(tmp_path.iterdir())
