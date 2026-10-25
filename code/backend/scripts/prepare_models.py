"""Download a pinned public MERT snapshot; verify the existing source head.

This does NOT train a prediction head or create random substitute weights.
HF_ENDPOINT can be set to https://hf-mirror.com before executing.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import MODEL_ID, REVISION, HEAD_SHA256
from app.inference import file_sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--head-path', type=Path)
    parser.add_argument('--backbone-only', action='store_true',
                        help='Prepare only public MERT while the existing head is unavailable; cannot enable predictions.')
    parser.add_argument('--transport', choices=['hub', 'http'], default='hub',
                        help='HTTP GET fallback for mirrors missing the HEAD metadata required by the Hub SDK.')
    args = parser.parse_args()
    head_verified = args.head_path is not None and args.head_path.is_file() and file_sha(args.head_path) == HEAD_SHA256
    if not args.backbone_only and not head_verified:
        parser.error('Provide the verified DEAM mean_mlp seed20261011 best.pt; expected SHA256: ' + HEAD_SHA256)
    from huggingface_hub import snapshot_download
    destination = args.model_dir.resolve()
    if (destination / 'demo-model.json').exists():
        parser.error('Model manifest already exists; use a new directory rather than overwrite verified assets.')
    if args.transport == 'http':
        from pinned_http_download import fetch_pinned_http
        fetch_pinned_http(destination, MODEL_ID, REVISION)
    else:
        snapshot_download(repo_id=MODEL_ID, revision=REVISION, local_dir=str(destination),
                          allow_patterns=['*.json', '*.py', 'pytorch_model*.bin', '*.safetensors', '*.txt', 'LICENSE*'])
    files = {p.relative_to(destination).as_posix(): file_sha(p)
             for p in destination.rglob('*') if p.is_file() and '.cache' not in p.relative_to(destination).parts}
    if not any(name.endswith(('.bin', '.safetensors')) for name in files):
        raise RuntimeError('Downloaded snapshot has no model weights')
    manifest = {'model_id': MODEL_ID, 'revision': REVISION, 'files': files,
                'head_seed': 20261011, 'head_sha256': HEAD_SHA256, 'head_verified_at_preparation': head_verified,
                'origin': 'Pinned public Hugging Face snapshot; custom model code runs offline only after explicit preparation.'}
    (destination / 'demo-model.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('MODEL_PREPARED', MODEL_ID, REVISION, 'files', len(files))
    print('HEAD_VERIFIED' if head_verified else 'BACKBONE_ONLY_HEAD_STILL_REQUIRED', HEAD_SHA256)


if __name__ == '__main__':
    main()
