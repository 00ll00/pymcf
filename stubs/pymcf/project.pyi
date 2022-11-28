from pymcf import logger as logger
from pymcf._frontend import MCFContext
from pymcf._frontend.context import MCFFile
from pymcf.mcversions import MCVer as MCVer
from pymcf.util import staticproperty as staticproperty
from typing import Optional, List


class Project:
    mc_version: MCVer
    output_dir: str
    generated: bool
    ctxs: List[MCFContext]
    mcfs: List[MCFFile]
    def __init__(self) -> None: ...
    @staticmethod
    def init(namespace: Optional[str] = ..., mc_version: Optional[MCVer] = ..., output_dir: Optional[str] = ...): ...
    def add_ctx(self, ctx) -> None: ...
    def add_mcf(self, mcf) -> None: ...
    @staticmethod
    def build() -> None: ...
    namespace: str
    INSTANCE: Project
