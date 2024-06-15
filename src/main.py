from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from typing import Callable, ParamSpec, TypeVar
import readline  # noqa: F401

DEBUG_FUNCTION_INDENT = 0

T = TypeVar("T")
P = ParamSpec("P")


def debug_function(func: Callable[P, T]) -> Callable[P, T]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        global DEBUG_FUNCTION_INDENT
        indent = "  " * DEBUG_FUNCTION_INDENT
        DEBUG_FUNCTION_INDENT += 1
        print(f"{indent}+ {func.__name__}({args}, {kwargs})")

        result = func(*args, **kwargs)

        print(f"{indent}- {func.__name__} -> {result}")
        DEBUG_FUNCTION_INDENT -= 1

        return result

    return wrapper


@dataclass(frozen=True, slots=True)
class Source:
    lines: list[str]


@dataclass(frozen=True)
class SourcePosition:
    source: Source
    line: int
    column: int
    length: int = 1

    def grow(self) -> "SourcePosition":
        assert len(self.full_line) >= self.column + self.length
        return SourcePosition(self.source, self.line, self.column, self.length + 1)

    def eof(self) -> bool:
        return self.line >= len(self.source.lines)

    def next(self) -> "SourcePosition":
        if self.column + self.length + 1 < len(self.full_line):
            return SourcePosition(self.source, self.line, self.column + 1)
        else:
            return SourcePosition(self.source, self.line + 1, 0)

    @property
    def full_line(self) -> str:
        return self.source.lines[self.line]

    @cached_property
    def content(self) -> str:
        # This doesn't support multi-line tokens
        assert len(self.full_line) >= self.column + self.length
        return self.full_line[self.column : self.column + self.length]

    def __repr__(self) -> str:
        if self.eof():
            return "EOF"
        return f"{self.line + 1}:{self.column + 1} '{self.content}'"


class TokenCategory(Enum):
    LAMBDA = "Lambda"
    DOT = "Dot"
    LPAREN = "L-Paren"
    RPAREN = "R-Paren"
    COLON = "Colon"
    IDENTIFIER = "Identifier"
    LET = "Let"
    IN = "In"
    NUMBER = "Number"


@dataclass(frozen=True, slots=True)
class Token:
    position: SourcePosition
    category: TokenCategory

    @property
    def content(self) -> str:
        return self.position.content

    def __repr__(self) -> str:
        return f"{self.category.value} at {self.position}"


@dataclass(slots=True)
class SourceReader:
    source: Source
    current_position: SourcePosition

    def peek(self) -> str:
        return self.current_position.content

    def forward(self) -> None:
        self.current_position = self.current_position.next()

    def eat(self) -> SourcePosition:
        position = self.current_position
        self.peek()
        self.forward()
        return position

    def tokenize_one(self, category: TokenCategory) -> Token:
        return Token(
            self.eat(),
            category,
        )

    def tokenize_while(
        self, category: TokenCategory, predicate: Callable[[str], bool]
    ) -> Token:
        position = self.eat()

        while not self.current_position.eof() and predicate(self.peek()):
            position = position.grow()
            self.forward()
        return Token(position, category)


ONE_CHARACTER_TOKENS = {
    "\\": TokenCategory.LAMBDA,
    ".": TokenCategory.DOT,
    "(": TokenCategory.LPAREN,
    ")": TokenCategory.RPAREN,
    ":": TokenCategory.COLON,
}


def lex(source: Source) -> list[Token]:
    reader = SourceReader(source, SourcePosition(source, 0, 0))
    tokens = []
    while not reader.current_position.eof():
        char = reader.peek()

        if char in {"\n", " ", "\t", "\r", "\f", "\v"}:
            reader.forward()

        elif char in ONE_CHARACTER_TOKENS:
            tokens.append(reader.tokenize_one(ONE_CHARACTER_TOKENS[char]))

        elif char in "0123456789":
            tokens.append(
                reader.tokenize_while(TokenCategory.NUMBER, lambda c: c in "0123456789")
            )

        elif char.isalpha():
            token = reader.tokenize_while(
                TokenCategory.IDENTIFIER, lambda c: c.isalpha()
            )
            if token.content == "let":
                token = Token(token.position, TokenCategory.LET)

            elif token.content == "in":
                token = Token(token.position, TokenCategory.IN)

            tokens.append(token)

    return tokens


if __name__ == "__main__":
    while True:
        try:
            source = Source([input("> ") + "\n"])
        except (KeyboardInterrupt, EOFError):
            print("\nQuitting...")
            exit(0)

        tokens = lex(source)
        for token in tokens:
            print(token)
