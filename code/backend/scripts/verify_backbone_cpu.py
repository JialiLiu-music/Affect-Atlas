"""Independently load and check downloaded frozen backbone on CPU, no head."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import MODEL_ID, REVISION
from app.inference import file_sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import torch
    from transformers import AutoModel, Wav2Vec2FeatureExtractor
    assert torch.version.cuda is None, 'Expected CPU-only Torch build'
    torch.set_num_threads(2)
    manifest = json.loads((args.model_dir / 'demo-model.json').read_text(encoding='utf-8'))
    assert manifest['revision'] == REVISION and manifest['model_id'] == MODEL_ID
    for name, digest in manifest['files'].items():
        assert file_sha(args.model_dir / name) == digest, name
    start = time.perf_counter()
    model = AutoModel.from_pretrained(str(args.model_dir), trust_remote_code=True, local_files_only=True).to('cpu').eval()
    raw = torch.load(args.model_dir / 'pytorch_model.bin', map_location='cpu', weights_only=True)
    mapping = {'encoder.pos_conv_embed.conv.weight_g': 'encoder.pos_conv_embed.conv.parametrizations.weight.original0',
               'encoder.pos_conv_embed.conv.weight_v': 'encoder.pos_conv_embed.conv.parametrizations.weight.original1'}
    state = model.state_dict()
    assert len(raw) == len(state) == 211
    for name, values in raw.items():
        assert torch.equal(values, state[mapping.get(name, name)]), name
    extractor = Wav2Vec2FeatureExtractor.from_pretrained(str(args.model_dir), local_files_only=True)
    # Generated one-second silence tests actual backbone execution, not accuracy.
    import numpy as np
    values = extractor(np.zeros(24000, dtype=np.float32), sampling_rate=24000, return_tensors='pt').input_values
    with torch.inference_mode():
        outputs = model(values, output_hidden_states=True)
        features = torch.stack(outputs.hidden_states[-4:]).mean(0)
    assert torch.isfinite(features).all()
    assert features.shape[0] == 1 and features.shape[-1] == 768
    result = {'status': 'BACKBONE_CPU_PASS', 'revision': REVISION, 'weight_tensors_checked': 211,
              'feature_shape': list(features.shape), 'torch': torch.__version__, 'device': 'cpu',
              'elapsed_seconds': round(time.perf_counter() - start, 3),
              'input': 'generated one-second silence; execution smoke only, not music accuracy evaluation',
              'head_available': False, 'full_prediction_verified': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
