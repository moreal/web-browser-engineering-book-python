from typing import NamedTuple


class SpecificityWeight(NamedTuple):
    id_column: int
    class_column: int
    type_column: int

    def __add__(self, other: "SpecificityWeight") -> "SpecificityWeight":
        return SpecificityWeight(
            self.id_column + other.id_column,
            self.class_column + other.class_column,
            self.type_column + other.type_column,
        )
