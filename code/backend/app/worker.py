"""Single resident CPU inference subprocess with a killable per-job deadline."""
import multiprocessing as mp
from pathlib import Path
import time

from .config import Settings
from .inference import PredictionError


def _serve(connection, settings):
    import os
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    from .inference import CpuPredictor
    predictor = CpuPredictor(settings)
    try:
        while True:
            path = connection.recv()
            if path is None:
                break
            try:
                result = predictor.predict(Path(path), lambda stage, progress: connection.send(
                    {'kind': 'progress', 'stage': stage, 'progress': progress}))
                connection.send({'kind': 'result', 'result': result})
            except PredictionError as exc:
                connection.send({'kind': 'error', 'error': str(exc)})
            except Exception:
                # Do not expose uploaded paths, model paths or stack traces.
                connection.send({'kind': 'error', 'error': 'CPU推理失败，请检查后端依赖和已验证模型资产。'})
    except (EOFError, BrokenPipeError):
        pass
    finally:
        connection.close()


class CpuWorker:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.process = None
        self.connection = None
        self.loaded = False
        self._closed = False

    def execute(self, path, progress):
        if self._closed:
            raise PredictionError('服务正在关闭。')
        if self.process is None or not self.process.is_alive():
            self.close_process()
            ctx = mp.get_context('spawn')
            parent, child = ctx.Pipe()
            self.connection = parent
            self.process = ctx.Process(target=_serve, args=(child, self.settings), daemon=True)
            self.process.start()
            child.close()
        try:
            self.connection.send(str(path))
            deadline = time.monotonic() + self.settings.inference_timeout_seconds
            while not self._closed:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self.close_process()
                    raise PredictionError('CPU任务处理超时，请上传更短片段后重试。')
                if self.connection.poll(min(remaining, .5)):
                    message = self.connection.recv()
                    if message['kind'] == 'progress':
                        progress(message['stage'], message['progress'])
                    elif message['kind'] == 'result':
                        self.loaded = True
                        return message['result']
                    else:
                        raise PredictionError(message['error'])
                elif not self.process.is_alive():
                    raise PredictionError('CPU工作进程退出，请重试。')
            raise PredictionError('服务正在关闭。')
        except (EOFError, OSError, BrokenPipeError) as exc:
            self.close_process()
            raise PredictionError('CPU工作进程连接中断，请重试。') from exc

    def close_process(self):
        if self.process is not None:
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=3)
                if self.process.is_alive():
                    self.process.kill()
                    self.process.join(timeout=3)
            self.process = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        self.loaded = False

    def close(self):
        self._closed = True
        self.close_process()
