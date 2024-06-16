from dataclasses import dataclass
from .ast import Expression, Literal, Application, Lambda, Identifier
from .lexer import Token, TokenCategory
from .typ import KnownTyp, MonoTyp, LambdaTyp, InferredTyp


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
        case Literal(
            Token(category=TokenCategory.LITERAL, literal_category=literal_category),
            inferred_typ,
        ):
            assert literal_category is not None
            print(f"{expression} : {literal_category}")

            known_typ = KnownTyp.from_literal_category(literal_category)
            union_typ = union(known_typ, inferred_typ)
            return inferred_typ.upgrade(union_typ)

        case Identifier(token, inferred_typ):
            typ_from_environement = typ_environement[token.content]
            if typ_from_environement is not None:
                print(f"{expression} : {typ_from_environement}")
                union_typ = union(typ_from_environement, inferred_typ)
                return inferred_typ.upgrade(union_typ)
            return inferred_typ

        case Application(function, argument, inferred_typ):
            function_typ = infer_type(function, typ_environement)
            argument_typ = infer_type(argument, typ_environement)

            print(f"{expression} : {function_typ} $ {argument_typ}")
            return inferred_typ.upgrade(
                infer_application_type(function_typ, argument_typ)
            )

        case Lambda(_, _, _, _, body, inferred_typ):
            lambda_typ_environment = LambdaTypEnvironment(
                variable_name=expression.identifier_token.content,
                variable_typ=MonoTyp.create(),
                inner=typ_environement,
            )

            body_typ = infer_type(body, lambda_typ_environment)
            print(f"{expression} : {lambda_typ_environment.variable_typ} -> {body_typ}")

            true_typ = LambdaTyp(
                variable_typ=lambda_typ_environment.variable_typ,
                body_typ=body_typ,
            )
            union_typ = union(true_typ, inferred_typ)
            return inferred_typ.upgrade(union_typ)

        case _:
            raise NotImplementedError()


def infer_application_type(
    function_typ: InferredTyp, argument_typ: InferredTyp
) -> InferredTyp:
    print(f"inferring {function_typ} $ {argument_typ}")
    function_true_typ = function_typ.tru_typ()
    argument_true_typ = argument_typ.tru_typ()

    match function_true_typ:
        case LambdaTyp(variable_typ, body_typ):
            union_typ = union(variable_typ, argument_true_typ)
            variable_typ.upgrade(union_typ)
            argument_typ.upgrade(union_typ)

            print(f"-  union_typ: {union_typ}")
            print(f"-  substitute: {variable_typ} to {union_typ} in {body_typ}")
            body_typ_substitued = subsitute(variable_typ, union_typ, body_typ)
            print(f"-  body_typ_substitued: {body_typ_substitued}")

            return body_typ_substitued

        case MonoTyp(_):
            print(f"-  ensure {function_typ} is not in {argument_true_typ}")

            new_typ = LambdaTyp(
                variable_typ=argument_true_typ,
                body_typ=MonoTyp.create(),
            )
            print(f"-  new_typ: {new_typ}")
            union_typ = union(function_true_typ, new_typ)
            print(f"-  union_typ: {union_typ}")

            function_typ.upgrade(union_typ)

            return infer_application_type(union_typ, argument_true_typ)

        case _:
            raise ValueError(f"Expected a lambda type, got {function_typ}")


def union(typ1: InferredTyp, typ2: InferredTyp) -> InferredTyp:
    true_typ1 = typ1.tru_typ()
    true_typ2 = typ2.tru_typ()

    if equal(true_typ1, true_typ2):
        return typ1

    match (true_typ1, true_typ2):
        case (unfied_typ, MonoTyp(m)):
            assert not is_in_typ(MonoTyp(m), unfied_typ), "Cannot unify recursive types"
            return unfied_typ
        case (MonoTyp(m), unfied_typ):
            assert not is_in_typ(MonoTyp(m), unfied_typ), "Cannot unify recursive types"
            return unfied_typ

        case (KnownTyp(name1), KnownTyp(name2)):
            if name1 == name2:
                return typ1
            raise ValueError(f"Cannot unify known types {name1} with {name2}")

        case (LambdaTyp(variable_typ1, body_typ1), LambdaTyp(variable_typ2, body_typ2)):
            return LambdaTyp(
                variable_typ=union(variable_typ1, variable_typ2),
                body_typ=union(body_typ1, body_typ2),
            )

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
    true_from_typ = from_typ.tru_typ()
    true_to_typ = to_typ.tru_typ()
    true_in_typ = in_typ.tru_typ()

    if equal(true_from_typ, true_in_typ):
        return true_to_typ

    match true_in_typ:
        case LambdaTyp(variable_typ, body_typ):
            return LambdaTyp(
                variable_typ=subsitute(true_from_typ, true_to_typ, variable_typ),
                body_typ=subsitute(true_from_typ, true_to_typ, body_typ),
            )

        case KnownTyp(_) | MonoTyp(_):
            return true_in_typ

        case _:
            raise NotImplementedError()


def is_in_typ(monotyp: MonoTyp, typ: InferredTyp) -> bool:
    match typ:
        case MonoTyp(other_monotyp):
            return monotyp.name == other_monotyp

        case LambdaTyp(arg_typ, body_typ):
            return is_in_typ(monotyp, body_typ) or is_in_typ(monotyp, arg_typ)

        case KnownTyp(_):
            return False

        case _:
            raise NotImplementedError()
