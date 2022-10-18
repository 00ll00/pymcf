import logging
import sys

from pymcf.mcversions import MCVer

_debugging = True

logging.basicConfig(
    level=logging.DEBUG if _debugging else logging.INFO,
    format="[%(levelname)s] %(filename)s:%(lineno)d - %(message)s" if _debugging else "[%(levelname)s] - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
logger.info(f"PYMCF version 0.1, support minecraft {MCVer.JE_1_19_1} - {MCVer.JE_1_19_2}")

from pymcf.project import Project
from pymcf.mcfunction import mcfunction
from pymcf.operations import raw
from pymcf import datas


del logging
