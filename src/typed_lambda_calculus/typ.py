from dataclasses import dataclass
from .lexer import LiteralCategory


@dataclass(frozen=True, slots=True)
class KnownTyp:
    name: str

    @classmethod
    def from_literal_category(cls, literal_category: LiteralCategory) -> "KnownTyp":
        match literal_category:
            case LiteralCategory.NUMBER:
                return cls("Number")
            case LiteralCategory.BOOL:
                return cls("Bool")
            case _:
                raise NotImplementedError()

    def tru_typ(self) -> "InferredTyp":
        return self

    def upgrade(self, upper_typ: "InferredTyp") -> "InferredTyp":
        assert (
            isinstance(upper_typ, KnownTyp) and upper_typ.name == self.name
        ), "Cannot upgrade to a different type"
        return self


MONO_TYP_COUNTER = 0


def reset_mono_typ_counter():
    global MONO_TYP_COUNTER
    MONO_TYP_COUNTER = 0


@dataclass(slots=True)
class MonoTyp:
    name: str

    upper_typ: "InferredTyp | None" = None

    @classmethod
    def create(cls) -> "MonoTyp":
        global MONO_TYP_COUNTER
        MONO_TYP_COUNTER += 1
        return cls(f"t{MONO_TYP_COUNTER}")

    def tru_typ(self) -> "InferredTyp":
        return self.upper_typ.tru_typ() if self.upper_typ else self

    def upgrade(self, upper_typ: "InferredTyp") -> "InferredTyp":
        if self.upper_typ:
            return self.upper_typ.upgrade(upper_typ)
        else:
            if self is upper_typ:
                return self
            self.upper_typ = upper_typ
            return upper_typ


@dataclass(slots=True)
class LambdaTyp:
    variable_typ: "InferredTyp"
    body_typ: "InferredTyp"

    upper_typ: "InferredTyp | None" = None

    def tru_typ(self) -> "InferredTyp":
        return self.upper_typ.tru_typ() if self.upper_typ else self

    def upgrade(self, upper_typ: "InferredTyp") -> "InferredTyp":
        if self.upper_typ:
            return self.upper_typ.upgrade(upper_typ)
        else:
            if self is upper_typ:
                return self
            self.upper_typ = upper_typ
            return upper_typ


InferredTyp = KnownTyp | LambdaTyp | MonoTyp
