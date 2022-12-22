import logging
import os
from collections import defaultdict
from typing import Optional, Dict, Any

from pymcf.mcversions import MCVer
from pymcf.util import staticclass
from pymcf import logger


@staticclass
class Project:

    def __init__(self):
        self.namespace: str = None
        self.mc_version: MCVer = None
        self.output_dir: str = None

        self.generated = False

        self.ctxs = {}
        self.mcfs = {}

        self.config = defaultdict(bool)

    def init(self, namespace: Optional[str] = "minecraft", mc_version: Optional[MCVer] = None, output_dir: Optional[str] = None, config: Dict[str, Any] | None = None):
        self.config = defaultdict(bool, config) if config is not None else defaultdict(bool)
        self.namespace = namespace
        self.mc_version = mc_version if mc_version is not None else MCVer.JE_1_19_2
        self.output_dir = (output_dir if output_dir is not None else os.getcwd()) + '\\' + namespace + "\\functions\\"
        logging.info(f"""Project "{self.namespace}" initialized, for minecraft {self.mc_version}.""")
        logging.info(f"Output directory set to: {self.output_dir}.")

    def add_ctx(self, ctx):
        from pymcf._frontend.context import MCFContext
        ctx: MCFContext
        self.ctxs[ctx.name] = ctx

    def add_mcf(self, mcf):
        self.mcfs[mcf.name] = mcf

    def build(self):
        if self.generated:
            logger.warning("project already generated, skipped second build.")
            return
        self.generated = True
        for mcf in self.mcfs.copy().values():
            if mcf.ep:
                mcf.gen_ep()
        for ctx in self.ctxs.values():
            ctx.gen_files()

    def __repr__(self):
        return f"Project: {self.namespace} (mcv: {self.mc_version})"

