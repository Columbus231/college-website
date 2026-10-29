import socket
import struct

from app.core.config import settings


class ScannerUnavailable(RuntimeError):
    pass


class MalwareDetected(RuntimeError):
    pass


def scan_document(content: bytes) -> None:
    if not settings.clamav_host:
        if settings.environment == "production":
            raise ScannerUnavailable("Malware scanning is not configured")
        return
    try:
        with socket.create_connection(
            (settings.clamav_host, settings.clamav_port),
            timeout=settings.clamav_timeout_seconds,
        ) as connection:
            connection.settimeout(settings.clamav_timeout_seconds)
            connection.sendall(b"zINSTREAM\0")
            for offset in range(0, len(content), 64 * 1024):
                chunk = content[offset:offset + 64 * 1024]
                connection.sendall(struct.pack("!I", len(chunk)) + chunk)
            connection.sendall(struct.pack("!I", 0))
            response = connection.makefile("rb").readline(4096)
    except OSError as exc:
        raise ScannerUnavailable("Malware scanning service is unavailable") from exc
    if response.endswith(b"FOUND\0"):
        raise MalwareDetected("Uploaded document failed malware scanning")
    if not response.endswith(b"OK\0"):
        raise ScannerUnavailable("Malware scanning service returned an invalid response")
