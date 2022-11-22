import logging
import os
from typing import Optional

from pymcf.mcversions import MCVer
from pymcf.util import staticproperty
from pymcf import logger


class Project:
    _instance = None

    def __init__(self):
        self.namespace: str = None
        self.mc_version: MCVer = None
        self.output_dir: str = None

        self.generated = False

        self.ctxs = {}
        self.mcfs = {}

    @staticmethod
    def init(namespace: Optional[str] = "minecraft", mc_version: Optional[MCVer] = None, output_dir: Optional[str] = None):
        proj = Project.INSTANCE
        proj.namespace = namespace
        proj.mc_version = mc_version if mc_version is not None else MCVer.JE_1_19_2
        proj.output_dir = (output_dir if output_dir is not None else os.getcwd()) + '\\' + namespace + "\\functions\\"

        if not os.path.exists(proj.output_dir):
            os.mkdir(proj.output_dir)

        logging.info(f"Project {proj.namespace} initialized, for minecraft {proj.mc_version}.")
        logging.info(f"Output directory set to {proj.output_dir}.")

    def add_ctx(self, ctx):
        from pymcf.context import MCFContext
        ctx: MCFContext
        self.ctxs[ctx.name] = ctx

    def add_mcf(self, mcf):
        self.mcfs[mcf.name] = mcf

    @staticmethod
    def build():
        inst: Project = Project.INSTANCE
        if inst.generated:
            logger.warn("project already generated, skipped second build.")
            return
        inst.generated = True
        for mcf in inst.mcfs.values():
            if mcf.ep:
                mcf.gen_ep()
        for ctx in inst.ctxs.values():
            ctx.gen_files()

    def __repr__(self):
        return f"Project: {self.namespace} (mcv: {self.mc_version})"

    # noinspection PyMethodParameters
    @staticproperty
    def namespace() -> str:
        return Project._instance.namespace

    # noinspection PyMethodParameters
    @staticproperty
    def INSTANCE():
        if Project._instance is None:
            Project._instance = Project()
        return Project._instance
