import logging
import sys

from .mcversions import MCVer

_version = "dev-1.0"

_debugging = True

logging.basicConfig(
    level=logging.DEBUG if _debugging else logging.INFO,
    format="[%(levelname)s] %(filename)s:%(lineno)d - %(message)s" if _debugging else "[%(levelname)s] - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
logger.info(f"PYMCF {_version}, support minecraft {MCVer.JE_1_19_1} - {MCVer.JE_1_19_2}")

if sys.version_info.major != 3 or sys.version_info.minor != 10:
    logger.error(f"PYMCF {_version} only work with python 3.10.x, but your python version is {sys.version}. Unknown errors will occurred.")

from ._project import Project
from ._mcfunction import mcfunction
from .operations import raw
from ._frontend import MCFContext

__all__ = [
    "MCVer",
    "Project",
    "mcfunction",
    "raw",
    "logger",
    "data",
    "entity",
    "math",
    "MCFContext"
]

del logging, sys
