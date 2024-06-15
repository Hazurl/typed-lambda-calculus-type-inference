import readline  # noqa: F401
from argparse import ArgumentParser

from typed_lambda_calculus.lexer import Source, Token, TokenCategory, lex
from typed_lambda_calculus.parser import ExpectedTokenError, parse, print_expression
from typed_lambda_calculus.type_checker import infer_type


def get_source_from_input() -> Source:
    content = ""
    tokens: list[Token] = []
    balanced_count = 0

    def expecting_more():
        # If there are no tokens, we are expecting more input
        if len(tokens) == 0:
            return True

        # If it's unbalanced, either it is an incorrect program (example `())`), or we are expecting more input (example `(\x -> x`)
        if balanced_count < 0:
            return False
        if balanced_count > 0:
            return True

        # These tokens should always be followed by an expression
        return tokens[-1].category in {
            TokenCategory.IN,
            TokenCategory.DOT,
            TokenCategory.EQUALS,
            TokenCategory.ARROW,
        }

    while expecting_more():
        content += input("> " if len(tokens) == 0 else "| ") + "\n"

        source = Source.from_string(content)
        tokens = lex(source)

        balanced_count = 0
        for token in tokens:
            match token.category:
                case (
                    TokenCategory.PAREN_LEFT
                    | TokenCategory.LET
                    | TokenCategory.LAMBDA
                ):
                    balanced_count += 1
                case TokenCategory.PAREN_RIGHT | TokenCategory.IN | TokenCategory.DOT:
                    balanced_count -= 1

    return Source.from_string(content)


if __name__ == "__main__":
    argument_parser = ArgumentParser(
        prog="lambda-calculus",
        description="A simple lambda calculus interpreter with type inference",
    )

    argument_parser.add_argument(
        "--print-tokens",
        action="store_true",
        help="Print the tokens generated by the lexer",
    )

    argument_parser.add_argument(
        "--print-ast",
        action="store_true",
        help="Print the AST generated by the parser",
    )

    argument_parser.add_argument(
        "--print-type",
        action="store_true",
        help="Print the type of the expression",
    )

    args = argument_parser.parse_args()

    while True:
        try:
            source = get_source_from_input()
        except (KeyboardInterrupt, EOFError):
            print("\nQuitting...")
            exit(0)

        tokens = lex(source)
        if args.print_tokens:
            for token in tokens:
                print(token)

        try:
            expression = parse(tokens)
            if args.print_ast:
                print_expression(expression)
        except ExpectedTokenError as e:
            print(e)

            if e.got is not None:
                position = e.got.position
                print(position.full_line)
                print(" " * position.column + "^" + "~" * (position.length - 1))

            exit(1)

        if args.print_type:
            print(f"of type: {infer_type(expression)}")
