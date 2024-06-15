import readline  # noqa: F401
from lexer import lex, Source, Token, TokenCategory
from parser import parse, print_expression, ExpectedTokenError


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
        }

    while expecting_more():
        content += input("> " if len(tokens) == 0 else "| ") + "\n"

        source = Source.from_string(content)
        tokens = lex(source)

        balanced_count = 0
        for token in tokens:
            match token.category:
                case TokenCategory.LPAREN | TokenCategory.LET | TokenCategory.LAMBDA:
                    balanced_count += 1
                case TokenCategory.RPAREN | TokenCategory.IN | TokenCategory.DOT:
                    balanced_count -= 1

    return Source.from_string(content)


if __name__ == "__main__":
    while True:
        try:
            source = get_source_from_input()
        except (KeyboardInterrupt, EOFError):
            print("\nQuitting...")
            exit(0)

        tokens = lex(source)
        # for token in tokens:
        #     print(token)

        try:
            expression = parse(tokens)
            print_expression(expression)
        except ExpectedTokenError as e:
            print(e)

            if e.got is not None:
                position = e.got.position
                print(position.full_line)
                print(" " * position.column + "^" + "~" * (position.length - 1))
