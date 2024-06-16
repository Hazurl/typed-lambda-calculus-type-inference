from dataclasses import dataclass
from typing import Callable, TypeVar
from .lexer import Token, TokenCategory
from .ast import (
    Typ,
    TypVariable,
    TypFunction,
    TypeAnnotation,
    LetIn,
    Lambda,
    Application,
    Identifier,
    Literal,
    Expression,
)
from .typ import MonoTyp


class ExpectedTokenError(Exception):
    expected: list[TokenCategory]
    got: Token | None

    def __init__(self, expected: list[TokenCategory], got: Token | None) -> None:
        expected_str = (
            " or ".join(category.value for category in expected) if expected else "EOF"
        )

        if not got:
            super().__init__(f"Expected {expected_str}, got EOF")
        else:
            super().__init__(
                f"Expected {expected_str}, got {got.category.value} at {got.position}"
            )

        self.expected = expected
        self.got = got


@dataclass(slots=True)
class TokenReader:
    tokens: list[Token]
    current_position: int

    def peek(self) -> Token | None:
        return self.tokens[self.current_position] if not self.eof() else None

    def forward(self) -> None:
        self.current_position += 1

    def eat(self, category: TokenCategory) -> Token:
        token = self.peek()

        if token is None or token.category != category:
            raise ExpectedTokenError([category], token)

        self.forward()
        return token

    def eof(self) -> bool:
        return self.current_position >= len(self.tokens)


def parse_non_function_typ(reader: TokenReader) -> Typ:
    token = reader.peek()

    match token.category if token else None:
        case TokenCategory.TYPE:
            return TypVariable(reader.eat(TokenCategory.TYPE))

        case TokenCategory.PAREN_LEFT:
            return parse_parenthesized(reader, parse_typ)

        case _:
            raise ExpectedTokenError(
                [
                    TokenCategory.TYPE,
                    TokenCategory.PAREN_LEFT,
                ],
                token,
            )


def parse_typ(
    reader: TokenReader,
) -> Typ:
    typ: Typ = parse_non_function_typ(reader)

    token = reader.peek()
    match token.category if token else None:
        case TokenCategory.ARROW:
            arrow_token = reader.eat(TokenCategory.ARROW)
            next_typ = parse_typ(reader)
            return TypFunction(typ, arrow_token, next_typ)

        case _:
            return typ


def try_parse_type_annotation(reader: TokenReader) -> TypeAnnotation | None:
    colon_token = reader.peek()
    if colon_token is None or colon_token.category != TokenCategory.COLON:
        return None

    reader.forward()

    typ = parse_typ(reader)

    return TypeAnnotation(colon_token, typ)


def parse_lambda(reader: TokenReader) -> Lambda:
    lambda_token = reader.eat(TokenCategory.LAMBDA)
    identifier_token = reader.eat(TokenCategory.VARIABLE)
    type_annotation = try_parse_type_annotation(reader)
    dot_token = reader.eat(TokenCategory.DOT)

    body = parse_expression(reader)
    return Lambda(
        lambda_token,
        identifier_token,
        type_annotation,
        dot_token,
        body,
        MonoTyp.create(),
    )


T = TypeVar("T")


def parse_parenthesized(
    reader: TokenReader, inner_parser: Callable[[TokenReader], T]
) -> T:
    reader.eat(TokenCategory.PAREN_LEFT)
    parsed = inner_parser(reader)
    reader.eat(TokenCategory.PAREN_RIGHT)
    return parsed


def parse_identifier(reader: TokenReader) -> Identifier:
    identifier_token = reader.eat(TokenCategory.VARIABLE)
    return Identifier(identifier_token, MonoTyp.create())


def parse_literal(reader: TokenReader) -> Literal:
    identifier_token = reader.eat(TokenCategory.LITERAL)
    return Literal(identifier_token, MonoTyp.create())


def parse_let_in(reader: TokenReader) -> LetIn:
    let_token = reader.eat(TokenCategory.LET)
    identifier_token = reader.eat(TokenCategory.VARIABLE)
    type_annotation = try_parse_type_annotation(reader)
    equal_token = reader.eat(TokenCategory.EQUALS)
    expression = parse_expression(reader)
    in_token = reader.eat(TokenCategory.IN)
    body = parse_expression(reader)

    return LetIn(
        let_token,
        identifier_token,
        type_annotation,
        equal_token,
        expression,
        in_token,
        body,
        MonoTyp.create(),
    )


def try_parse_non_application_expression(reader: TokenReader) -> Expression | None:
    token = reader.peek()

    match token.category if token else None:
        case TokenCategory.LAMBDA:
            return parse_lambda(reader)
        case TokenCategory.PAREN_LEFT:
            return parse_parenthesized(reader, parse_expression)
        case TokenCategory.VARIABLE:
            return parse_identifier(reader)
        case TokenCategory.LITERAL:
            return parse_literal(reader)
        case TokenCategory.LET:
            return parse_let_in(reader)
        case _:
            return None


def parse_expression(reader: TokenReader) -> Expression:
    expr: Expression | None = try_parse_non_application_expression(reader)

    if expr is None:
        raise ExpectedTokenError(
            [
                TokenCategory.LAMBDA,
                TokenCategory.PAREN_LEFT,
                TokenCategory.VARIABLE,
                TokenCategory.LITERAL,
                TokenCategory.LET,
            ],
            reader.peek(),
        )

    while True:
        next_expr: Expression | None = try_parse_non_application_expression(reader)
        if next_expr is None:
            return expr

        expr = Application(expr, next_expr, MonoTyp.create())


def parse(tokens: list[Token]) -> Expression:
    token_reader = TokenReader(tokens, 0)
    expr = parse_expression(token_reader)
    if not token_reader.eof():
        raise ExpectedTokenError([], token_reader.peek())
    return expr
