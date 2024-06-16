from dataclasses import dataclass
from typing import Callable, TypeVar
from .lexer import Token, TokenCategory


@dataclass(frozen=True, slots=True)
class TypFunction:
    argument: "Typ"
    arrow_token: Token
    result: "Typ"


@dataclass(frozen=True, slots=True)
class TypVariable:
    type_token: Token


Typ = TypFunction | TypVariable


@dataclass(frozen=True, slots=True)
class TypeAnnotation:
    colon_token: Token
    typ: Typ


@dataclass(frozen=True, slots=True)
class LetIn:
    let_token: Token
    identifier_token: Token
    type_annotation: TypeAnnotation | None
    equal_token: Token
    expression: "Expression"
    in_token: Token
    body: "Expression"


@dataclass(frozen=True, slots=True)
class Lambda:
    lambda_token: Token
    identifier_token: Token
    type_annotation: TypeAnnotation | None
    dot_token: Token
    body: "Expression"


@dataclass(frozen=True, slots=True)
class Application:
    function: "Expression"
    argument: "Expression"


@dataclass(frozen=True, slots=True)
class Identifier:
    identifier_token: Token


@dataclass(frozen=True, slots=True)
class Literal:
    literal_token: Token


Expression = LetIn | Lambda | Application | Identifier | Literal


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
    return Lambda(lambda_token, identifier_token, type_annotation, dot_token, body)


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
    return Identifier(identifier_token)


def parse_literal(reader: TokenReader) -> Literal:
    identifier_token = reader.eat(TokenCategory.LITERAL)
    return Literal(identifier_token)


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

        expr = Application(expr, next_expr)


def parse(tokens: list[Token]) -> Expression:
    token_reader = TokenReader(tokens, 0)
    expr = parse_expression(token_reader)
    if not token_reader.eof():
        raise ExpectedTokenError([], token_reader.peek())
    return expr


def print_expression(expression: Expression):
    indent = 0

    def _typ_to_str(typ: Typ, use_parenthesis: bool = False) -> str:
        match typ:
            case TypVariable(type_token):
                return type_token.content
            case TypFunction(argument, _, result):
                argument_str = _typ_to_str(argument, use_parenthesis=True)
                result_str = _typ_to_str(result)
                return (
                    f"({argument_str} -> {result_str})"
                    if use_parenthesis
                    else f"{argument_str} -> {result_str}"
                )

    def _print_expression(expression: Expression):
        nonlocal indent

        match expression:
            case LetIn(_, identifier_token, type_annotation, _, expression, _, body):
                type_annotation_str = (
                    f":{_typ_to_str(type_annotation.typ)}" if type_annotation else ""
                )
                print(
                    " " * indent
                    + f"let [{identifier_token.content}{type_annotation_str}] ="
                )
                indent += 2
                _print_expression(expression)
                print(" " * indent + "in")
                _print_expression(body)
                indent -= 2
            case Lambda(_, identifier_token, type_annotation, _, body):
                type_annotation_str = (
                    f":{_typ_to_str(type_annotation.typ)}" if type_annotation else ""
                )
                print(
                    " " * indent
                    + f"λ [{identifier_token.content}{type_annotation_str}] ."
                )
                indent += 2
                _print_expression(body)
                indent -= 2
            case Application(function, argument):
                print(" " * indent + "app")
                indent += 2
                _print_expression(function)
                _print_expression(argument)
                indent -= 2
            case Identifier(identifier_token):
                print(" " * indent + f"ident[{identifier_token.content}]")
            case Literal(literal_token):
                print(" " * indent + f"literal[{literal_token.content}]")

    _print_expression(expression)
