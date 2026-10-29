from starlette.responses import JSONResponse

from app.core.config import settings


class RequestBodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        maximum = settings.max_upload_bytes + 256_000
        content_length = next(
            (value for name, value in scope.get("headers", []) if name.lower() == b"content-length"),
            None,
        )
        if content_length is not None:
            try:
                if int(content_length) > maximum:
                    response = JSONResponse(status_code=413, content={"detail": "Request body exceeds the allowed size"})
                    await response(scope, receive, send)
                    return
            except ValueError:
                response = JSONResponse(status_code=400, content={"detail": "Invalid request content length"})
                await response(scope, receive, send)
                return

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > maximum:
                raise RequestBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            response = JSONResponse(status_code=413, content={"detail": "Request body exceeds the allowed size"})
            await response(scope, receive, send)


class RequestBodyTooLarge(Exception):
    pass
