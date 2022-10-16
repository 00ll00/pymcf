import logging
import os
import shutil
from typing import Dict, Optional
from pymcf.mcversions import MCVer
from pymcf.util import staticproperty


class Project:
    _instance = None

    def __init__(self):
        self.name: str = None
        self.mc_version: MCVer = None
        self.output_dir: str = None

        self.mcf_load = set()
        self.mcf_tick = set()

        self.ctxs = {}

    @staticmethod
    def init(name: str, mc_version: Optional[MCVer] = None, output_dir: Optional[str] = None):
        proj = Project.INSTANCE
        proj.name = name
        proj.mc_version = mc_version if mc_version is not None else MCVer.JE_1_19_2
        proj.output_dir = output_dir if output_dir is not None else os.getcwd() + '\\' + name + '\\'

        if os.path.exists(proj.output_dir):
            shutil.rmtree(proj.output_dir)
        os.mkdir(proj.output_dir)

        logging.info(f"Project {proj.name} initialized, for minecraft {proj.mc_version}.")
        logging.info(f"Output directory set to {proj.output_dir}.")

    def add_ctx(self, ctx):
        from pymcf.context import MCFContext
        ctx: MCFContext
        self.ctxs[ctx.name] = ctx

    def __repr__(self):
        return f"Project: {self.name} (mcv: {self.mc_version})"

    # noinspection PyMethodParameters
    @staticproperty
    def INSTANCE():
        if Project._instance is None:
            Project._instance = Project()
        return Project._instance
