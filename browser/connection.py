import socket
import ssl
import time
from dataclasses import dataclass
from typing import Final, Literal

from browser.protocols.http.header_map import HeaderMap
from browser.protocols.http.request import (
    HTTP_LINE_SEPARATOR,
    HttpRequest,
    HttpRequestEncoder,
)
from browser.protocols.http.response import HttpResponse
from browser.url import HttpFamilyUrl

__all__ = ("Connection",)

HTTP_FAMILY_SCHEME = Literal["http", "https"]

DEFAULT_PORT: dict[HTTP_FAMILY_SCHEME, int] = {
    "http": 80,
    "https": 443,
}


def get_default_port(scheme: HTTP_FAMILY_SCHEME) -> int:
    return DEFAULT_PORT[scheme]


class Connection:
    """HTTP connection"""

    def __init__(self, socket: ssl.SSLSocket | socket.socket) -> None:
        self._socket: Final[ssl.SSLSocket | socket.socket] = socket
        self._reader = socket.makefile("rb", newline=HTTP_LINE_SEPARATOR)

    @classmethod
    def open(cls, scheme: Literal["http", "https"], host: str, port: int | None = None):
        _socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
        )

        if scheme == "https":
            context = ssl.create_default_context()
            _socket = context.wrap_socket(_socket, server_hostname=host)

        port = port or DEFAULT_PORT[scheme]

        _socket.connect((host, port))

        return cls(_socket)

    def close(self):
        self._socket.close()

    def request(
        self,
        request: HttpRequest,
        encoder: HttpRequestEncoder | None = None,
    ) -> HttpResponse:
        encoder = encoder or HttpRequestEncoder()

        _sent_bytes = self._socket.send(encoder.encode(request))

        statusline = self._reader.readline().decode("iso-8859-1")
        print("request", request)
        print("statusline", statusline.encode())
        version, status_code, status_message = statusline.split(" ", 2)

        headers = dict[str, str]()
        while (line := self._reader.readline()) != b"\r\n":
            name, value = line.decode("iso-8859-1").split(":", 1)
            headers[name.strip().casefold()] = value.strip()

        if headers.get("transfer-encoding") == "chunked":
            # https://httpwg.org/specs/rfc9112.html#chunked.encoding
            # Chunk length is represented in hexadecimal
            body = b""
            while (line := self._reader.readline()) != b"\r\n":
                content_length = int(line.decode("iso-8859-1").strip(), 16)
                if content_length == 0:
                    break
                body += self._reader.read(content_length + 2).strip()
        elif headers.get("content-length") is not None:
            content_length = int(headers["content-length"])
            body = self._reader.read(content_length)
        else:
            body = self._reader.read()

        match headers.get("content-encoding"):
            case "gzip":
                import gzip

                body = gzip.decompress(body)
            case None:
                pass
            case _:
                raise Exception("Unknown content encoding")

        return HttpResponse(
            version=version,
            status_code=int(status_code),
            status_message=status_message,
            headers=HeaderMap(headers),
            body=body,
            request=request,
        )


# Unit is seconds
CONNECTION_LIFETIME = 119


@dataclass(frozen=True, eq=True)
class ConnectionCacheKey:
    scheme: str
    host: str
    port: int


# Key is ConnectionCacheKey, value is tuple of Connection and expiration time
_connection_cache: dict[ConnectionCacheKey, tuple[Connection, int]] = {}


def request_http(
    url: HttpFamilyUrl,
    request: HttpRequest,
    encoder: HttpRequestEncoder | None = None,
) -> HttpResponse:
    cache_key = ConnectionCacheKey(
        scheme=url.scheme,
        host=url.host,
        port=url.port or get_default_port(url.scheme),
    )

    cached = _connection_cache.get(cache_key)
    if cached is None:
        connection = Connection.open(scheme=url.scheme, host=url.host, port=url.port)
        _connection_cache[cache_key] = (
            connection,
            int(time.time()) + CONNECTION_LIFETIME,
        )
    else:
        connection, expiration_time = cached
        current_time = time.time()
        if expiration_time < current_time:
            connection, _ = _connection_cache.pop(cache_key)
            connection.close()

            connection = Connection.open(
                scheme=url.scheme, host=url.host, port=url.port
            )
            _connection_cache[cache_key] = (
                connection,
                int(time.time()) + CONNECTION_LIFETIME,
            )

    response = connection.request(request, encoder)
    if response.headers.get("connection") == "close":
        connection, _ = _connection_cache.pop(cache_key)
        connection.close()

    return response
