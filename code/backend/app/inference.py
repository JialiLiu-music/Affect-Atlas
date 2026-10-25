"""Pinned offline frozen MERT and existing DEAM head, always on CPU."""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import time

from .config import Settings, MODEL_ID, REVISION, HEAD_SHA256


class PredictionError(Exception):
    """Safe error suitable for returning to a demo visitor."""


def file_sha(path: Path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def asset_status(settings: Settings):
    missing = [name for name in ['torch', 'transformers', 'soundfile', 'librosa', 'numpy']
               if importlib.util.find_spec(name) is None]
    if missing:
        return False, '后端推理依赖未安装：' + ', '.join(missing)
    if not settings.head_path.is_file():
        return False, '缺少论文训练得到的预测头权重，请按README准备模型资产。'
    if not (settings.model_dir / 'demo-model.json').is_file():
        return False, '缺少固定版本MERT模型，请先运行prepare_models.py。'
    try:
        manifest = json.loads((settings.model_dir / 'demo-model.json').read_text(encoding='utf-8'))
        if manifest.get('model_id') != MODEL_ID or manifest.get('revision') != REVISION:
            return False, 'MERT模型版本与论文不一致。'
        required = ['config.json', 'preprocessor_config.json']
        if any(not (settings.model_dir / p).is_file() for p in required):
            return False, 'MERT配置不完整，请重新准备模型。'
    except (OSError, ValueError):
        return False, '模型来源记录无法读取。'
    return True, None


def window_starts(size: int, window: int = 240000, hop: int = 120000):
    if size <= 0:
        raise PredictionError('音频为空。')
    if size <= window:
        return [0]
    last = size - window
    starts = list(range(0, last + 1, hop))
    if starts[-1] != last:
        starts.append(last)
    return starts


def decode_audio(path: Path, settings: Settings):
    import numpy as np
    import soundfile as sf
    import librosa
    try:
        with sf.SoundFile(path) as audio:
            if not 8000 <= audio.samplerate <= 192000 or not 1 <= audio.channels <= 8:
                raise PredictionError('不支持此音频的采样率或声道数。')
            duration = audio.frames / audio.samplerate
            if not settings.min_duration_seconds <= duration <= settings.max_duration_seconds:
                raise PredictionError(f'当前解码时长为{duration:.2f}秒；请上传{settings.min_duration_seconds:g}至{settings.max_duration_seconds:g}秒的完整音频片段，系统不会自动截断。')
            # Bounded mono accumulation; do not allocate all multi-channel samples.
            parts = []
            count = 0
            for block in audio.blocks(blocksize=65536, dtype='float32', always_2d=True):
                if not np.isfinite(block).all():
                    raise PredictionError('音频包含非有限数值。')
                count += len(block)
                if count > math.ceil(settings.max_duration_seconds * audio.samplerate):
                    raise PredictionError('解码后的音频超过允许时长。')
                parts.append(block.mean(axis=1))
            if not parts:
                raise PredictionError('音频没有有效采样。')
            wave = np.concatenate(parts)
            sr = audio.samplerate
    except PredictionError:
        raise
    except Exception as exc:
        raise PredictionError('音频无法解码，请使用有效的WAV、MP3、FLAC或OGG文件。') from exc
    if sr != 24000:
        wave = librosa.resample(wave, orig_sr=sr, target_sr=24000).astype(np.float32)
    if not np.isfinite(wave).all() or not len(wave):
        raise PredictionError('重采样后音频无效。')
    return wave


class CpuPredictor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = None
        self.extractor = None
        self.head = None

    def load(self):
        if self.model is not None:
            return
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        import torch
        from transformers import AutoModel, Wav2Vec2FeatureExtractor
        settings = self.settings
        torch.set_num_threads(settings.cpu_threads)
        if file_sha(settings.head_path) != HEAD_SHA256:
            raise PredictionError('预测头SHA256与已核验的论文模型不一致，拒绝随机或替代权重。')
        manifest = json.loads((settings.model_dir / 'demo-model.json').read_text(encoding='utf-8'))
        if manifest.get('revision') != REVISION or manifest.get('model_id') != MODEL_ID:
            raise PredictionError('模型版本不匹配。')
        files = manifest.get('files', {})
        if not files or any(Path(name).is_absolute() or '..' in Path(name).parts for name in files):
            raise PredictionError('MERT模型文件清单包含无效路径。')
        if not all((settings.model_dir / name).is_file() and file_sha(settings.model_dir / name) == digest
                   for name, digest in files.items()):
            raise PredictionError('MERT模型文件校验失败。')
        model = AutoModel.from_pretrained(str(settings.model_dir), trust_remote_code=True, local_files_only=True)
        raw = {}
        if list(settings.model_dir.glob('*.safetensors')):
            from safetensors.torch import load_file
            for p in settings.model_dir.glob('*.safetensors'):
                raw.update(load_file(str(p), device='cpu'))
        else:
            for p in settings.model_dir.glob('pytorch_model*.bin'):
                raw.update(torch.load(p, map_location='cpu', weights_only=True))
        # Transformers warns on renamed weight-norm tensors; verify actual values.
        mapping = {'encoder.pos_conv_embed.conv.weight_g': 'encoder.pos_conv_embed.conv.parametrizations.weight.original0',
                   'encoder.pos_conv_embed.conv.weight_v': 'encoder.pos_conv_embed.conv.parametrizations.weight.original1'}
        state = model.state_dict()
        if len(raw) != 211 or len(state) != 211:
            raise PredictionError('MERT张量数量与已核验模型不一致。')
        for key, tensor in raw.items():
            if not torch.equal(tensor, state.get(mapping.get(key, key), torch.empty(0))):
                raise PredictionError('MERT加载后权重不一致。')
        head = torch.nn.Sequential(torch.nn.Linear(768, 32), torch.nn.ReLU(), torch.nn.Linear(32, 2))
        checkpoint = torch.load(settings.head_path, map_location='cpu', weights_only=True)
        values = checkpoint['state_dict']
        if set(values) != {'head.0.weight', 'head.0.bias', 'head.2.weight', 'head.2.bias'}:
            raise PredictionError('预测头结构与论文mean_mlp不一致。')
        head.load_state_dict({k.removeprefix('head.'): v for k, v in values.items()}, strict=True)
        self.model = model.to(torch.device('cpu')).eval()
        self.head = head.to(torch.device('cpu')).eval()
        for p in list(self.model.parameters()) + list(self.head.parameters()):
            p.requires_grad_(False)
        self.extractor = Wav2Vec2FeatureExtractor.from_pretrained(str(settings.model_dir), local_files_only=True)

    def predict(self, path: Path, progress):
        import numpy as np
        import torch
        start = time.perf_counter()
        progress('decoding', .02)
        wave = decode_audio(path, self.settings)
        progress('loading_model', .07)
        self.load()
        duration = len(wave) / 24000
        bins = math.floor(duration - .5) + 1
        sums = np.zeros((bins, 768), dtype=np.float64)
        counts = np.zeros(bins, dtype=np.int64)
        starts = window_starts(len(wave))
        with torch.inference_mode():
            for i, at in enumerate(starts):
                window = wave[at:at + 240000]
                if len(window) < 240000:
                    window = np.pad(window, (0, 240000 - len(window)))
                values = self.extractor(window, sampling_rate=24000, return_tensors='pt', padding=False).input_values.to('cpu')
                output = self.model(values, output_hidden_states=True)
                frames = torch.stack(output.hidden_states[-4:]).mean(0)[0].float().cpu().numpy()
                frame_duration = min(10., (len(wave) - at) / 24000)
                times = at / 24000 + (np.arange(len(frames)) + .5) * frame_duration / len(frames)
                indices = np.floor(times).astype(np.int64)
                keep = (indices >= 0) & (indices < bins)
                for b in np.unique(indices[keep]):
                    chosen = frames[keep & (indices == b)]
                    sums[b] += chosen.sum(axis=0, dtype=np.float64)
                    counts[b] += len(chosen)
                progress('extracting_features', .1 + .8 * (i + 1) / len(starts))
                del output, frames
            if np.any(counts == 0):
                raise PredictionError('特征时间bin缺失，无法完成预测。')
            features = (sums / counts[:, None]).astype(np.float32)
            if not np.isfinite(features).all():
                raise PredictionError('模型特征包含无效数值。')
            progress('predicting', .95)
            # Match the original StaticModel's float32 temporal mean on CPU.
            prediction = self.head(torch.from_numpy(features).mean(0)).numpy()
            from .timeline import timeline_scores
            timeline = timeline_scores(features, duration,
                                       lambda pooled: self.head(torch.from_numpy(pooled)).numpy())
        if prediction.shape != (2,) or not np.isfinite(prediction).all():
            raise PredictionError('预测数值无效。')
        v, a = [float(x) for x in prediction]
        return dict(valence=v, arousal=a, display_valence=max(-1., min(1., v)),
                    display_arousal=max(-1., min(1., a)), out_of_range=abs(v) > 1 or abs(a) > 1,
                    duration_seconds=round(duration, 4), feature_bins=bins,
                    processing_seconds=round(time.perf_counter() - start, 3),
                    device='cpu', calibration='none', head_seed=20261011, model_revision=REVISION,
                    timeline=timeline)
