"""Bound request bytes before multipart parsing can spool an oversized upload."""
import asyncio
import secrets
from starlette.responses import JSONResponse


class UploadBoundaryMiddleware:
    def __init__(self, app, max_bytes, capacity=4, api_token=''):
        self.app = app
        self.max_bytes = max_bytes + 256 * 1024  # bounded multipart overhead
        self.capacity = capacity
        self.api_token = api_token
        self.reading = 0

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST' or scope['path'] != '/api/jobs':
            return await self.app(scope, receive, send)
        headers = dict(scope.get('headers', []))
        if self.api_token and not secrets.compare_digest(headers.get(b'authorization', b''),
                                                         ('Bearer ' + self.api_token).encode()):
            return await JSONResponse({'detail': '需要有效的演示访问令牌。'}, status_code=401)(scope, receive, send)
        if self.reading >= self.capacity:
            return await JSONResponse({'detail': '上传处理繁忙，请稍后重试。'}, status_code=429)(scope, receive, send)
        length = headers.get(b'content-length')
        if length:
            try:
                too_large = int(length) > self.max_bytes
            except ValueError:
                return await JSONResponse({'detail': '无效请求长度。'}, status_code=400)(scope, receive, send)
            if too_large:
                return await JSONResponse({'detail': '上传请求超过大小限制。'}, status_code=413)(scope, receive, send)
        self.reading += 1
        chunks = []
        total = 0
        deadline = asyncio.get_running_loop().time() + 60
        try:
            while True:
                timeout = deadline - asyncio.get_running_loop().time()
                if timeout <= 0:
                    raise asyncio.TimeoutError()
                message = await asyncio.wait_for(receive(), timeout=timeout)
                if message['type'] == 'http.disconnect':
                    return
                total += len(message.get('body', b''))
                if total > self.max_bytes:
                    return await JSONResponse({'detail': '上传请求超过大小限制。'}, status_code=413)(scope, receive, send)
                chunks.append(message)
                if not message.get('more_body', False):
                    break
            iterator = iter(chunks)
            async def replay():
                return next(iterator, {'type': 'http.request', 'body': b'', 'more_body': False})
            await self.app(scope, replay, send)
        except asyncio.TimeoutError:
            await JSONResponse({'detail': '上传超时，请重试。'}, status_code=408)(scope, receive, send)
        finally:
            self.reading -= 1
