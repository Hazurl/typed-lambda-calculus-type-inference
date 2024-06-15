from dataclasses import dataclass
from lexer import Token, TokenCategory


@dataclass(frozen=True, slots=True)
class LetIn:
    let_token: Token
    identifier_token: Token
    equal_token: Token
    expression: "Expression"
    in_token: Token
    body: "Expression"


@dataclass(frozen=True, slots=True)
class Lambda:
    lambda_token: Token
    identifier_token: Token
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


def parse_lambda(reader: TokenReader) -> Lambda:
    lambda_token = reader.eat(TokenCategory.LAMBDA)
    identifier_token = reader.eat(TokenCategory.IDENTIFIER)
    dot_token = reader.eat(TokenCategory.DOT)

    body = parse_expression(reader)
    return Lambda(lambda_token, identifier_token, dot_token, body)


def parse_parenthesized(reader: TokenReader) -> Expression:
    reader.eat(TokenCategory.LPAREN)
    expression = parse_expression(reader)
    reader.eat(TokenCategory.RPAREN)
    return expression


def parse_identifier(reader: TokenReader) -> Identifier:
    identifier_token = reader.eat(TokenCategory.IDENTIFIER)
    return Identifier(identifier_token)


def parse_literal(reader: TokenReader) -> Literal:
    identifier_token = reader.eat(TokenCategory.NUMBER)
    return Literal(identifier_token)


def parse_let_in(reader: TokenReader) -> LetIn:
    let_token = reader.eat(TokenCategory.LET)
    identifier_token = reader.eat(TokenCategory.IDENTIFIER)
    equal_token = reader.eat(TokenCategory.EQUALS)
    expression = parse_expression(reader)
    in_token = reader.eat(TokenCategory.IN)
    body = parse_expression(reader)
    return LetIn(let_token, identifier_token, equal_token, expression, in_token, body)


def try_parse_non_application_expression(reader: TokenReader) -> Expression | None:
    token = reader.peek()

    match token.category if token else None:
        case TokenCategory.LAMBDA:
            return parse_lambda(reader)
        case TokenCategory.LPAREN:
            return parse_parenthesized(reader)
        case TokenCategory.IDENTIFIER:
            return parse_identifier(reader)
        case TokenCategory.NUMBER:
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
                TokenCategory.LPAREN,
                TokenCategory.IDENTIFIER,
                TokenCategory.NUMBER,
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

    def _print_expression(expression: Expression):
        nonlocal indent

        match expression:
            case LetIn(_, identifier_token, _, expression, _, body):
                print(" " * indent + "let")
                indent += 2
                print(" " * indent + f"{identifier_token.content}:var =")
                _print_expression(expression)
                print(" " * indent + "in")
                _print_expression(body)
                indent -= 2
            case Lambda(_, identifier_token, _, body):
                print(" " * indent + "λ" + identifier_token.content + ":var .")
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
                print(" " * indent + identifier_token.content + ":ident")
            case Literal(literal_token):
                print(" " * indent + literal_token.content + ":literal")

    _print_expression(expression)
