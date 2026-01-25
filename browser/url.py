from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import Literal, Self, cast

from browser.protocols.http.media_type import (
    MediaType,
    parse_media_type,
)

__all__ = ("Url", "DataUrlData")

QueryValueType = str | list[str]


@dataclass(frozen=True)
class Url:
    scheme: str
    username: str | None = None
    password: str | None = None
    host: str | None = None
    port: int | None = None
    path: str | None = None
    # FIXME: it doens't parse query string (e.g., "key[]=a&key[3]=b")
    query: str | None = None
    fragment: str | None = None

    @classmethod
    def parse(cls, s: str) -> Self | UrlParseError:
        # RFC 3986 compliant URL regex pattern
        # URI = scheme ":" ["//" authority] path ["?" query] ["#" fragment]
        # authority = [userinfo "@"] host [":" port]

        # Scheme: starts with letter, followed by letters, digits, +, -, or .
        scheme = r"(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*)"

        # Userinfo (optional): username[:password]@
        # Unreserved: A-Z a-z 0-9 - . _ ~
        # Sub-delims: ! $ & ' ( ) * + , ; =
        # Also allows : and percent-encoded chars
        userinfo = r"(?:(?P<username>[a-zA-Z0-9\-._~!$&'()*+,;=%]+)(?::(?P<password>[a-zA-Z0-9\-._~!$&'()*+,;=%]*))?@)?"

        # Host can be:
        # - IPv6: enclosed in brackets [...]
        # - IPv4: dot-decimal notation
        # - Registered name: letters, digits, hyphens, dots, underscores, tildes
        ipv6 = r"\[[0-9a-fA-F:]+\]"
        ipv4 = r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}"
        registered_name = r"[a-zA-Z0-9\-._~!$&'()*+,;=%]*"
        host = rf"(?P<hostname>{ipv6}|{ipv4}|{registered_name})"

        # Port (optional): decimal digits
        port = r"(?::(?P<port>\d+))?"

        # Authority (optional): [userinfo "@"] host [":" port]
        authority = rf"(?://(?:{userinfo}{host}{port}))?"

        # Path: sequence of segments separated by /
        # Can contain unreserved chars, percent-encoded, sub-delims, :, @
        # For URIs without authority, path can contain additional characters
        # Matches everything except ? and # (which start query and fragment)
        path = r"(?P<path>[^?#]*)"

        # Query (optional): after ?, can contain any character except #
        query = r"(?:\?(?P<query>[^#]*))?"

        # Fragment (optional): after #, can contain any remaining characters
        fragment = r"(?:#(?P<fragment>.*))?"

        # Complete regex pattern
        regex = rf"^{scheme}:{authority}{path}{query}{fragment}$"

        match = re.match(regex, s)
        if not match:
            return UrlParseError("message")

        scheme_value = match.group("scheme")
        username_value = match.group("username")
        password_value = match.group("password")
        hostname = match.group("hostname") or None
        port_value = int(match.group("port")) if match.group("port") else None
        path_value = match.group("path") or None
        query_value = match.group("query")
        fragment_value = match.group("fragment")

        return cls(
            scheme=scheme_value,
            username=username_value,
            password=password_value,
            host=hostname,
            port=port_value,
            path=path_value,
            query=query_value,
            fragment=fragment_value,
        )

    def resolve(self, url: str) -> Url:
        print("resolve debugging", self, url)
        if "://" in url:
            parsed = Url.parse(url)
            assert isinstance(parsed, Url)
            return parsed
        if not url.startswith("/"):
            assert self.path is not None
            dir, _ = self.path.rsplit("/", 1)
            while url.startswith("../"):
                _, url = url.split("/", 1)
                if "/" in dir:
                    dir, _ = dir.rsplit("/", 1)
            url = dir + "/" + url
        if url.startswith("//"):
            parsed = Url.parse(self.scheme + ":" + url)
            assert isinstance(parsed, Url)
            return parsed
        else:
            assert self.host is not None
            parsed = Url.parse(
                self.scheme
                + "://"
                + self.host
                + (":" + str(self.port) if self.port else "")
                + url
            )
            assert isinstance(parsed, Url)
            return parsed


@dataclass(frozen=True)
class HttpFamilyUrl:
    scheme: Literal["http", "https"]
    username: str | None
    password: str | None
    host: str
    port: int | None
    path: str | None
    query: str | None
    fragment: str | None

    def to_url(self) -> Url:
        return Url(
            scheme=self.scheme,
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            path=self.path,
            query=self.query,
            fragment=self.fragment,
        )

    @classmethod
    def from_url(cls, url: Url) -> HttpFamilyUrl | UrlParseError:
        if not (url.scheme == "http" or url.scheme == "https"):
            return UrlParseError(f"Unexpected scheme: {url.scheme}")

        if url.host is None:
            return UrlParseError("Host is required for HTTP URL.")

        return cls(
            scheme=url.scheme,
            username=url.username,
            password=url.password,
            host=url.host,
            port=url.port,
            path=url.path,
            query=url.query,
            fragment=url.fragment,
        )


@dataclass(frozen=True)
class FileUrl:
    host: str
    path: str | None


@dataclass(frozen=True)
class ViewSourceUrl:
    url: Url


@dataclass(frozen=True)
class DataUrlData:
    """
    Data URI scheme parser according to RFC 2397.

    Syntax: data:[<mediatype>][;base64],<data>

    - mediatype: optional MIME type with optional parameters (e.g., text/plain;charset=UTF-8)
                 defaults to text/plain;charset=US-ASCII
    - base64: optional indicator that data is base64-encoded
    - data: the actual data (may be empty)
    """

    media_type: MediaType  # e.g., "text/plain", "image/png"
    is_base64: bool
    data: str

    @staticmethod
    def parse(path: str) -> "DataUrlData":
        """
        Parse a data URI path (without the 'data:' scheme prefix).

        Examples:
            - "" -> mediatype=text/plain, charset=US-ASCII, data=""
            - "text/html,<h1>Hello</h1>" -> mediatype=text/html, data="<h1>Hello</h1>"
            - "text/plain;charset=UTF-8,Hello" -> mediatype=text/plain, charset=UTF-8, data="Hello"
            - "image/png;base64,iVBORw0..." -> mediatype=image/png, base64=True, data="iVBORw0..."
            - ";base64,R0lGODdh" -> mediatype=text/plain, base64=True, data="R0lGODdh"
        """
        if not path:
            # Minimal data URI: "data:,"
            path = ","

        # The comma is required and separates metadata from data
        if "," not in path:
            raise ValueError("Invalid data URI: missing comma separator")

        metadata, data = path.split(",", 1)

        # Parse metadata part: [<mediatype>][;<param>=<value>]*[;base64]
        parts = metadata.split(";") if metadata else []

        # First part is the mediatype (if present and not a parameter)
        mediatype = "text/plain"
        parameters: dict[str, str] = {}
        is_base64 = False

        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue

            # Check if it's "base64" indicator
            if part.lower() == "base64":
                is_base64 = True
            # Check if it's a parameter (contains '=')
            elif "=" in part:
                key, value = part.split("=", 1)
                parameters[key.strip()] = value.strip()
            # First non-parameter, non-base64 part is the mediatype
            elif i == 0:
                mediatype = part
            else:
                # If we encounter a part without '=' that's not first and not 'base64',
                # it might be a malformed URI, but we'll treat it as part of mediatype
                pass

        # Set default charset if not specified and mediatype is text/plain
        if mediatype == "text/plain" and "charset" not in parameters:
            parameters["charset"] = "US-ASCII"

        # NOTE: I can believe it's a valid media type
        media_type = cast(
            MediaType,
            parse_media_type(
                f"{mediatype}{''.join(f';{key}={value}' for key, value in parameters.items())}"
            ),
        )

        return DataUrlData(
            media_type=media_type,
            is_base64=is_base64,
            data=data,
        )

    def get_data(self) -> str | bytes:
        if self.is_base64:
            data = base64.b64decode(self.data)

            if self.media_type.type == "text":
                charset = self.media_type.parameters.get("charset", "US-ASCII")
                data = data.decode(charset)

            return data
        else:
            return self.data


class UrlParseError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


@dataclass(frozen=True)
class AboutUrl:
    path: str

    @classmethod
    def from_url(cls, url: Url) -> AboutUrl | UrlParseError:
        if url.scheme != "about" or url.path is None:
            return UrlParseError()

        return AboutUrl(path=url.path)

    def to_url(self) -> Url:
        return Url(scheme="about", path=self.path)
