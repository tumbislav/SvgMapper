# encoding: utf-8
__author__ = 'Marko Čibej'


import svgmapper
from os import sep
import logging


_samples = {
    '01 minimal': False,
    '02 copy_all': False,
    '03 recolour': False,
    '04 all projections': True
}


svgmapper.set_logging([0, 'regression.log'], 1)
for c in _samples:
    if _samples[c]:
        svgmapper.main(c)
