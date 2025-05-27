import importlib
import json
import zipfile
from collections import defaultdict
from contextvars import ContextVar
from pathlib import Path
from shutil import rmtree

from pymcf import exceptions
from pymcf.config import Config
from pymcf.ir import Compiler
from pymcf.mc.code_gen import Translator
from pymcf.mcfunction import mcfunction


class ProjectCfg(Config):
    prj_tmp_dir: Path = Path("./.pymcf_tmp")
    prj_install_path: Path = Path("./pymcf_out")
    dbg_viz_ir: bool = False
    dbg_viz_ast: bool = False


class Project:

    def __init__(self, name):
        self.name = name
        self._config: ProjectCfg = Config()

    @staticmethod
    def current() -> "Project":
        return _project.get()

    def config(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self._config, k, v)

    def add_module(self, name):
        _project.set(self)
        importlib.import_module(name)

    def build(self):
        if self._config.ir_bf is None:
            from pymcf.data import Score
            self.config(ir_bf = Score("$bf", "__sys__"))

        rmtree(self._config.prj_tmp_dir, ignore_errors=True)

        pack_path = self._config.prj_install_path / f"{self.name}.zip"
        pack_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.PyZipFile(pack_path, 'w', zipfile.ZIP_DEFLATED) as pack:

            function_tags = defaultdict(list)

            for mcf in mcfunction._all:
                if mcf._entrance:
                    mcf()
                    for tag in mcf._tags:
                        function_tags[tag].append(mcf.name)

            exceptions.confirm()

            for mcf in mcfunction._all:
                for i, scope in enumerate(mcf._arg_scope.values()):
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
                        arch_path = Path("data") / self.name / "function" / f"{mcf.name}.mcfunction"
                        file_path = self._config.prj_tmp_dir / "datapack" / arch_path
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(file_path, "wt") as f:
                            f.write(mcf.gen_code())
                        pack.write(file_path, arch_path)

            for tag, functions in function_tags.items():
                arch_path = Path("data") / self.name / "tags" / f"{tag}.json"
                file_path = self._config.prj_tmp_dir / "datapack" / arch_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                json.dump(functions, open(file_path, "wt"), indent=4)
                pack.write(file_path, arch_path)


_project: ContextVar[Project | None] = ContextVar("project", default=None)
