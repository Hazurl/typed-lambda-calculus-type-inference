from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from typing import Callable

DEBUG_FUNCTION_INDENT = 0


@dataclass(frozen=True, slots=True)
class Source:
    lines: list[str]

    @classmethod
    def from_string(cls, string: str) -> "Source":
        lines = string.splitlines()
        while lines and len(lines[-1]) == 0:
            lines.pop()
        return cls(lines)


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

    @classmethod
    def create_valid_position(
        cls, source: Source, line: int, column: int
    ) -> "SourcePosition":
        position = cls(source, line, column)
        while not position.eof() and position.column >= len(
            source.lines[position.line]
        ):
            position = cls(position.source, position.line + 1, 0)

        return position

    def next(self) -> "SourcePosition":
        return self.create_valid_position(
            self.source, self.line, self.column + self.length
        )

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
    PAREN_RIGHT = "R-Paren"
    PAREN_LEFT = "L-Paren"
    COLON = "Colon"
    VARIABLE = "Variable"
    TYPE = "Type"
    LET = "Let"
    IN = "In"
    LIT_NUMBER = "Number"
    EQUALS = "Equals"
    ARROW = "Arrow"


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
    "(": TokenCategory.PAREN_LEFT,
    ")": TokenCategory.PAREN_RIGHT,
    ":": TokenCategory.COLON,
    "=": TokenCategory.EQUALS,
}


def lex(source: Source) -> list[Token]:
    reader = SourceReader(source, SourcePosition.create_valid_position(source, 0, 0))
    tokens = []
    while not reader.current_position.eof():
        char = reader.peek()

        if char in {"\n", " ", "\t", "\r", "\f", "\v"}:
            reader.forward()

        elif char in ONE_CHARACTER_TOKENS:
            tokens.append(reader.tokenize_one(ONE_CHARACTER_TOKENS[char]))

        elif char in "0123456789":
            tokens.append(
                reader.tokenize_while(
                    TokenCategory.LIT_NUMBER, lambda c: c in "0123456789"
                )
            )

        elif char.isalpha():
            token = reader.tokenize_while(TokenCategory.VARIABLE, lambda c: c.isalpha())
            if token.content == "let":
                token = Token(token.position, TokenCategory.LET)

            elif token.content == "in":
                token = Token(token.position, TokenCategory.IN)

            elif token.content[0].isupper():
                token = Token(token.position, TokenCategory.TYPE)

            tokens.append(token)

        elif (arrow_position := reader.current_position.grow()).content == "->":
            tokens.append(Token(arrow_position, TokenCategory.ARROW))
            reader.forward()
            reader.forward()

        else:
            raise ValueError(f"Unknown character {char} at {reader.current_position}")

    return tokens
