from pymcf import logger as logger
from pymcf._frontend import MCFContext
from pymcf._frontend.context import MCFFile
from pymcf.mcversions import MCVer as MCVer
from pymcf.util import staticproperty as staticproperty, staticclass
from typing import Optional, List, Dict, Any


@staticclass
class Project:
    mc_version: MCVer
    output_dir: str
    generated: bool
    ctxs: Dict[str, MCFContext]
    mcfs: Dict[str, MCFFile]
    config: Dict[str, Any]
    def __init__(self) -> None: ...
    @staticmethod
    def init(namespace: Optional[str] = ..., mc_version: Optional[MCVer] = ..., output_dir: Optional[str] = ..., config: Dict[str, Any] | None = ...): ...
    def add_ctx(self, ctx) -> None: ...
    def add_mcf(self, mcf) -> None: ...
    @staticmethod
    def build() -> None: ...
    namespace: str
