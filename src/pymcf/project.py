import importlib
import json
import os
import zipfile
from collections import defaultdict
from pathlib import Path
from shutil import rmtree
from typing import final, Any

from pymcf import exceptions
from pymcf.ast_ import Constructor, Scope
from pymcf.config import Config
from pymcf.ir import Compiler
from pymcf.mc.code_gen import Translator
from pymcf.mc.scope import MCFScope
from pymcf.mcfunction import mcfunction


class ProjectCfg(Config):
    prj_tmp_dir: Path = Path("./.pymcf_tmp")
    prj_install_dir: Path = Path("./pymcf_out")
    prj_pack_format: int = 71

    tag_func_load: str = "load"
    tag_func_tick: str = "tick"

    dbg_viz_ir: bool = False
    dbg_viz_ast: bool = False


@final
class Project:

    _project = None

    def __init__(self, name, description=None, **config):
        if Project._project is not None:
            raise ValueError("Project already initialized")

        Project._project = self
        self.name = name
        self.description = description or name

        self._config: ProjectCfg = Config(**config)

        self.scb_rec: dict[str, tuple[str, Any]] = {}
        self.scb_init_constr = Constructor(
            name=f"__init__/scoreboard",
            scope=MCFScope(name=f"__init__/scoreboard", tags={self._config.tag_func_load}, executor=None),
            inline=False,
        )

        self.const_rec: dict[int, "Score"] = {}

    @staticmethod
    def instance() -> "Project":
        return Project._project

    @staticmethod
    def add_module(name):
        importlib.import_module(name)

    def build(self):
        if self._config.ir_bf is None:
            from pymcf.data import Score
            self._config.ir_bf = Score("$bf", "__sys__")

        rmtree(self._config.prj_tmp_dir, ignore_errors=True)

        function_tags = defaultdict(list)

        # start construct
        for mcf in mcfunction._all:
            if mcf._entrance:
                mcf()

        # TODO namespace
        for scope in Scope._all:
            scope.namespace = self.name

        # confirm errno
        exceptions.confirm()

        pack_dir_path = self._config.prj_tmp_dir / "datapack"

        def build_scope(scope: MCFScope):
            assert scope.finished
            if self._config.dbg_viz_ast:
                from pymcf.visualize import dump_context
                doc = dump_context(scope)
                path = self._config.prj_tmp_dir / "viz" / self.name / "ast" / f"{scope.name}.html"
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("w", encoding="utf-8") as f:
                    f.write(doc)

            compiler = Compiler(self._config)
            cbs = compiler.compile(scope)

            if self._config.dbg_viz_ir:
                from pymcf.visualize import draw_ir
                path = self._config.prj_tmp_dir / "viz" / self.name / "ir" / f"{scope.name}.dot"
                path.parent.mkdir(parents=True, exist_ok=True)
                draw_ir(cbs[0]).save(path)

            tr = Translator(scope)

            for cb in cbs:
                mcf = tr.translate(cb)
                file_path = pack_dir_path / "data" / self.name / "function" / f"{mcf.name}.mcfunction"
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "wt") as f:
                    f.write(mcf.gen_code())

        for s in Scope._all:
            s: MCFScope
            for tag in s.tags:
                function_tags[tag].append(f"{s.namespace}:{s.name}")
            if s is self.scb_init_constr.scope:
                continue  # 未构建完成
            build_scope(s)

        self.scb_init_constr.finish()
        build_scope(self.scb_init_constr.scope)

        # 整理 tags
        for tag, functions in function_tags.items():
            assert type(tag) is str
            file_path = pack_dir_path / "data" / self.name / "tags" / "function" / f"{tag}.json"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            json.dump({"values": functions}, open(file_path, "wt"), indent=4)

        # 写 pack.mcmeta
        json.dump(
            {
                "pack": {
                    "description": self.description,
                    "pack_format": self._config.prj_pack_format,
                }
            },
            (pack_dir_path / "pack.mcmeta").open("wt"),
            indent=4,
        )

        # 添加 minecraft:#tick/load
        mc_func_tag_path = pack_dir_path / "data/minecraft/tags/function/"
        mc_func_tag_path.mkdir(parents=True, exist_ok=True)
        json.dump({"values": [f"#{self.name}:tick"]}, open(mc_func_tag_path / "tick.json", "w"), indent=4)
        json.dump({"values": [f"#{self.name}:load"]}, open(mc_func_tag_path / "load.json", "w"), indent=4)

        # 打包 zip
        arch_path = self._config.prj_install_dir / f"{self.name}.zip"
        arch_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.PyZipFile(arch_path, 'w', zipfile.ZIP_DEFLATED) as pack:
            for root, dirs, files in os.walk(pack_dir_path):
                for file in files:
                    abs_file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_file_path, start=pack_dir_path)
                    pack.write(abs_file_path, arcname=rel_path)
