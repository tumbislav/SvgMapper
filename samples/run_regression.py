# encoding: utf-8
__author__ = 'Marko Čibej'


from svgmapper.main import main, set_logging


_samples = {
    '01 minimal': False,
    '02 copy_all': False,
    '03 recolour': False,
    '04 all projections': True
}


set_logging([0, 'regression.log'], 1)
for c in _samples:
    if _samples[c]:
        main(c)
