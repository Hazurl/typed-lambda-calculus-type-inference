import readline  # noqa: F401
from lexer import lex, Source, Token, TokenCategory


def get_source_from_input() -> Source:
    content = ""
    tokens: list[Token] = []
    parenthesized = 0

    while parenthesized > 0 or len(tokens) == 0:
        content += input("> " if len(tokens) == 0 else "| ") + "\n"

        source = Source.from_string(content)
        print(source)
        tokens = lex(source)

        for token in tokens:
            if token.category == TokenCategory.LPAREN:
                parenthesized += 1
            elif token.category == TokenCategory.RPAREN:
                parenthesized -= 1

    return Source.from_string(content)


if __name__ == "__main__":
    while True:
        try:
            source = get_source_from_input()
        except (KeyboardInterrupt, EOFError):
            print("\nQuitting...")
            exit(0)

        tokens = lex(source)
        for token in tokens:
            print(token)
