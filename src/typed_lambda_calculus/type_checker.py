from dataclasses import dataclass
from .parser import Expression, Literal, Application, Lambda, Identifier
from .lexer import Token, TokenCategory


@dataclass(frozen=True, slots=True)
class KnownTyp:
    name: str


MONO_TYP_COUNTER = 0


@dataclass(frozen=True, slots=True)
class MonoTyp:
    name: str

    @classmethod
    def create(cls) -> "MonoTyp":
        global MONO_TYP_COUNTER
        MONO_TYP_COUNTER += 1
        return cls(f"t{MONO_TYP_COUNTER}")


@dataclass(frozen=True, slots=True)
class LambdaTyp:
    variable_typ: "InferredTyp"
    body_typ: "InferredTyp"


InferredTyp = KnownTyp | LambdaTyp | MonoTyp


@dataclass(frozen=True, slots=True)
class EmptyTypEnvironment:
    def __getitem__(self, variable_name: str) -> InferredTyp | None:
        return None


@dataclass(frozen=True, slots=True)
class LambdaTypEnvironment:
    variable_name: str
    variable_typ: InferredTyp

    inner: "TypEnvironment"

    def __getitem__(self, variable_name: str) -> InferredTyp | None:
        if variable_name == self.variable_name:
            return self.variable_typ
        return self.inner[variable_name]


TypEnvironment = EmptyTypEnvironment | LambdaTypEnvironment


def infer_type(
    expression: Expression, typ_environement: TypEnvironment | None = None
) -> InferredTyp:
    if typ_environement is None:
        typ_environement = EmptyTypEnvironment()

    match expression:
        case Literal(Token(category=TokenCategory.LIT_NUMBER)):
            print(f"{expression} : Number")
            return KnownTyp("Number")

        case Identifier(token):
            typ_from_environement = typ_environement[token.content]
            typ = typ_environement[token.content] or MonoTyp.create()
            print(
                f"{expression} : {typ} {'+' if typ_from_environement is None else '-'}"
            )
            return typ

        case Application(function, argument):
            function_typ = infer_type(function, typ_environement)
            argument_typ = infer_type(argument, typ_environement)

            print(f"{expression} : {function_typ} $ {argument_typ}")

            match function_typ:
                case LambdaTyp(variable_typ, body_typ):
                    unified_type = unify(variable_typ, argument_typ)
                    print(f"-  unified_type: {unified_type}")
                    print(
                        f"-  substitute: {variable_typ} to {unified_type} in {body_typ}"
                    )
                    typ = subsitute(variable_typ, unified_type, body_typ)
                    print(f"-  typ: {typ}")
                    return typ

                case _:
                    raise ValueError(f"Expected a lambda type, got {function_typ}")

        case Lambda(_, _, _, _, body):
            lambda_typ_environment = LambdaTypEnvironment(
                variable_name=expression.identifier_token.content,
                variable_typ=MonoTyp.create(),
                inner=typ_environement,
            )

            body_typ = infer_type(body, lambda_typ_environment)
            print(f"{expression} : {lambda_typ_environment.variable_typ} -> {body_typ}")

            return LambdaTyp(
                variable_typ=lambda_typ_environment.variable_typ,
                body_typ=body_typ,
            )

        case _:
            raise NotImplementedError()


def unify(typ1: InferredTyp, typ2: InferredTyp) -> InferredTyp:
    match (typ1, typ2):
        case (unfied_typ, MonoTyp(_)):
            return unfied_typ
        case (MonoTyp(_), unfied_typ):
            return unfied_typ

        case (KnownTyp(name1), KnownTyp(name2)):
            if name1 == name2:
                return typ1
            raise ValueError(f"Cannot unify known types {name1} with {name2}")

        case _:
            raise ValueError(f"Cannot unify {typ1} with {typ2}")


def equal(typ1: InferredTyp, typ2: InferredTyp) -> bool:
    match (typ1, typ2):
        case (KnownTyp(name1), KnownTyp(name2)):
            return name1 == name2

        case (MonoTyp(name1), MonoTyp(name2)):
            return name1 == name2

        case (
            LambdaTyp(variable_typ1, body_typ1),
            LambdaTyp(variable_typ2, body_typ2),
        ):
            return equal(variable_typ1, variable_typ2) and equal(body_typ1, body_typ2)

        case _:
            return False


def subsitute(
    from_typ: InferredTyp, to_typ: InferredTyp, in_typ: InferredTyp
) -> InferredTyp:
    if equal(from_typ, in_typ):
        return to_typ

    match in_typ:
        case LambdaTyp(variable_typ, body_typ):
            return LambdaTyp(
                variable_typ=subsitute(from_typ, to_typ, variable_typ),
                body_typ=subsitute(from_typ, to_typ, body_typ),
            )

        case KnownTyp(_) | MonoTyp(_):
            return in_typ

        case _:
            raise NotImplementedError()
