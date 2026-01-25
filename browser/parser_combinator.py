from dataclasses import dataclass
from typing import Callable


@dataclass
class ParseResult[T]:
    value: T
    remaining: str


type Parser[T] = Callable[[str], ParseResult[T] | None]


def char(c: str) -> Parser[str]:
    def parse(input: str) -> ParseResult[str] | None:
        if input and input[0] == c:
            return ParseResult(c, input[1:])
        return None

    return parse


def satisfy(predicate: Callable[[str], bool]) -> Parser[str]:
    def parse(input: str) -> ParseResult[str] | None:
        if input and predicate(input[0]):
            return ParseResult(input[0], input[1:])
        return None

    return parse


def many[T](parser: Parser[T]) -> Parser[list[T]]:
    def parse(input: str) -> ParseResult[list[T]]:
        results: list[T] = []
        while (result := parser(input)) is not None:
            results.append(result.value)
            input = result.remaining
        return ParseResult(results, input)

    return parse


def many1[T](parser: Parser[T]) -> Parser[list[T]]:
    def parse(input: str) -> ParseResult[list[T]] | None:
        result = many(parser)(input)
        if not result.value:
            return None
        return result

    return parse


def map[T, U](parser: Parser[T], fn: Callable[[T], U]) -> Parser[U]:
    def parse(input: str) -> ParseResult[U] | None:
        result = parser(input)
        if result is None:
            return None
        return ParseResult(fn(result.value), result.remaining)

    return parse


def seq[T](*parsers: Parser[T]) -> Parser[list[T]]:
    def parse(input: str) -> ParseResult[list[T]] | None:
        results: list[T] = []
        for parser in parsers:
            result = parser(input)
            if result is None:
                return None
            results.append(result.value)
            input = result.remaining
        return ParseResult(results, input)

    return parse


def alt[T](*parsers: Parser[T]) -> Parser[T]:
    def parse(input: str) -> ParseResult[T] | None:
        for parser in parsers:
            result = parser(input)
            if result is not None:
                return result
        return None

    return parse


def optional[T](parser: Parser[T]) -> Parser[T | None]:
    def parse(input: str) -> ParseResult[T | None]:
        result = parser(input)
        if result is None:
            return ParseResult(None, input)
        return result

    return parse


def skip_many[T](parser: Parser[T]) -> Parser[None]:
    def parse(input: str) -> ParseResult[None]:
        while (result := parser(input)) is not None:
            input = result.remaining
        return ParseResult(None, input)

    return parse


def take_while(predicate: Callable[[str], bool]) -> Parser[str]:
    return map(many(satisfy(predicate)), lambda chars: "".join(chars))


def take_while1(predicate: Callable[[str], bool]) -> Parser[str]:
    return map(many1(satisfy(predicate)), lambda chars: "".join(chars))


def take_until(stop: str) -> Parser[str]:
    def parse(input: str) -> ParseResult[str]:
        idx = input.find(stop)
        if idx == -1:
            return ParseResult(input, "")
        return ParseResult(input[:idx], input[idx:])

    return parse


whitespace: Parser[None] = skip_many(satisfy(str.isspace))
