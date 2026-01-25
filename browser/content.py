from dataclasses import dataclass
from typing import Literal

from browser.protocols.http.media_type import MediaType

__all__ = (
    "Content",
    "ImageContent",
    "UnknownContent",
    "PlainTextContent",
    "HtmlContent",
)


type Content = (
    ImageContent
    | UnknownContent
    | UnhandledContent
    | PlainTextContent
    | HtmlContent
    | CssContent
    | ViewSource
)


@dataclass(frozen=True)
class ImageContent:
    bytes: bytes
    media_type: MediaType


@dataclass(frozen=True)
class UnknownContent:
    bytes: bytes
    media_type: None


@dataclass(frozen=True)
class UnhandledContent:
    bytes: bytes
    media_type: MediaType


@dataclass(frozen=True)
class PlainTextContent:
    text: str
    media_type: Literal["text/plain"] = "text/plain"


@dataclass(frozen=True)
class HtmlContent:
    data: bytes
    media_type: Literal["text/html"] = "text/html"


@dataclass(frozen=True)
class CssContent:
    data: bytes
    media_type: Literal["text/css"] = "text/css"


@dataclass(frozen=True)
class ViewSource:
    content: Content


def recognize_content(media_type: MediaType, data: bytes) -> Content:
    match media_type:
        case MediaType(type="text", subtype="html"):
            return HtmlContent(data)
        case MediaType(type="text", subtype="plain"):
            charset = media_type.parameters.get("charset") or "iso-8859-1"
            return PlainTextContent(text=data.decode(charset))
        case MediaType(type="text", subtype="css"):
            return CssContent(data)
        case MediaType(type="image", subtype="jpeg"):
            return ImageContent(media_type=media_type, bytes=data)
        case _:
            return UnhandledContent(media_type=media_type, bytes=data)
