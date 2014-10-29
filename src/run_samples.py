# encoding: utf-8
__author__ = 'Marko Čibej'

import svgmapper
from os import sep

_samples = {
    '01 minimal': True,
    '02 copy_all': False
}

for c in _samples:
    if _samples[c]:
        svgmapper.main('samples' + sep + c)
