import logging

from pymcf.mcversions import MCVer

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] %(filename)s:%(lineno)d - %(message)s"
)
logger = logging.getLogger(__name__)
logger.info(f"PYMCF version 0.1, support minecraft {MCVer.JE_1_19_1} - {MCVer.JE_1_19_2}")

from pymcf.project import Project
from pymcf.mcfunction import mcfunction
from pymcf import datas

del logging
