from typing import Any

from pymcf import MCFContext
from pymcf.entity import Identifier, Entity
from pymcf.entity import Self
from pymcf.operations import ExecuteOp


class execute:

    def __init__(self):
        self.chain = []

    def __enter__(self):
        MCFContext.new_file(executor=self.executor)

    def __exit__(self, exc_type, exc_val, exc_tb):
        MCFContext.exit_file()
        ExecuteOp()

    def as_(self, entity: Entity | Identifier | Any) -> "execute":
        self.chain.append(f"as {entity}")
        return self

    def at(self, entity: Entity | Identifier | Any) -> "execute":
        self.chain.append(f"at {entity}")
        return self

    def positioned(self, pos: Any) -> "execute":
        self.chain.append(f"positioned {pos}")
        return self

    def positioned_as(self, entity: Entity | Identifier | Any) -> "execute":
        self.chain.append(f"positioned as {entity}")
        return self

    def align(self, axis: str) -> "execute":
        self.chain.append(f"align {axis}")
        return self

    def anchored(self, anchor: str) -> "execute":
        self.chain.append(f"anchored {anchor}")
        return self