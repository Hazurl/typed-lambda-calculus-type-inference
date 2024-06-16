from .typ import InferredTyp, KnownTyp, MonoTyp, LambdaTyp
from .ast import (
    Expression,
    Typ,
    TypFunction,
    TypVariable,
    LetIn,
    Lambda,
    Application,
    Identifier,
    Literal,
)


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
            case LetIn(
                _,
                identifier_token,
                type_annotation,
                _,
                expression,
                _,
                body,
                inferred_typ,
            ):
                type_annotation_str = (
                    f":{_typ_to_str(type_annotation.typ)}" if type_annotation else ""
                )
                print(
                    " " * indent
                    + f"let [{identifier_token.content}{type_annotation_str}] {true_typ_to_str(inferred_typ)} ="
                )
                indent += 2
                _print_expression(expression)
                print(" " * indent + "in")
                _print_expression(body)
                indent -= 2
            case Lambda(_, identifier_token, type_annotation, _, body, inferred_typ):
                type_annotation_str = (
                    f":{_typ_to_str(type_annotation.typ)}" if type_annotation else ""
                )
                print(
                    " " * indent
                    + f"λ [{identifier_token.content}{type_annotation_str}] . {true_typ_to_str(inferred_typ)}"
                )
                indent += 2
                _print_expression(body)
                indent -= 2
            case Application(function, argument, inferred_typ):
                print(" " * indent + f"app {true_typ_to_str(inferred_typ)}")
                indent += 2
                _print_expression(function)
                _print_expression(argument)
                indent -= 2
            case Identifier(identifier_token, inferred_typ):
                print(
                    " " * indent
                    + f"ident[{identifier_token.content}] {true_typ_to_str(inferred_typ)}"
                )
            case Literal(literal_token, inferred_typ):
                print(
                    " " * indent
                    + f"literal[{literal_token.content}] {true_typ_to_str(inferred_typ)}"
                )

    _print_expression(expression)


def typ_to_str(typ: InferredTyp, use_parenthesis: bool = False) -> str:
    match typ.tru_typ():
        case KnownTyp(name):
            return name
        case MonoTyp(name):
            return "'" + name
        case LambdaTyp(variable_typ, body_typ):
            variable_str = typ_to_str(variable_typ, use_parenthesis=True)
            body_str = typ_to_str(body_typ)
            return (
                f"({variable_str} -> {body_str})"
                if use_parenthesis
                else f"{variable_str} -> {body_str}"
            )
        case _:
            raise NotImplementedError()


def true_typ_to_str(typ: InferredTyp) -> str:
    s = typ_to_str(typ)
    # if isinstance(typ, (MonoTyp, LambdaTyp)) and typ.upper_typ:
    #     s += f" => {true_typ_to_str(typ.upper_typ)}"

    return s
