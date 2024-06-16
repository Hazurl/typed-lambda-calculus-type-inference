from dataclasses import dataclass
from .lexer import Token
from .typ import MonoTyp


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


@dataclass(slots=True)
class LetIn:
    let_token: Token
    identifier_token: Token
    type_annotation: TypeAnnotation | None
    equal_token: Token
    expression: "Expression"
    in_token: Token
    body: "Expression"

    inferred_typ: MonoTyp


@dataclass(slots=True)
class Lambda:
    lambda_token: Token
    identifier_token: Token
    type_annotation: TypeAnnotation | None
    dot_token: Token
    body: "Expression"

    inferred_typ: MonoTyp


@dataclass(slots=True)
class Application:
    function: "Expression"
    argument: "Expression"

    inferred_typ: MonoTyp


@dataclass(slots=True)
class Identifier:
    identifier_token: Token

    inferred_typ: MonoTyp


@dataclass(slots=True)
class Literal:
    literal_token: Token

    inferred_typ: MonoTyp


Expression = LetIn | Lambda | Application | Identifier | Literal
