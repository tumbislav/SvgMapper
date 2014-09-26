# encoding: utf-8
from math import *
from mapper_helper import logger
#from scipy.interpolate import interp1d


epsilon = 0.0001


def sinc(a):
    if abs(a) < epsilon:
        return 1
    else:
        return a/sin(a)


class Aitoff:
    def __init__(self, x_ref):
        self.x_ref = x_ref

    def project(self, x, y):
        a = sinc(acos(cos(y)*cos((x-self.x_ref)/2)))
        return 2*cos(y)*sin((x-self.x_ref)/2)*a, sin(y)*a


class Albers:
    def __init__(self, x_ref, y_ref, y_0, y_1):
        self.x_ref = x_ref
        self.n = (sin(y_0) + sin(y_1))/2
        self.c = cos(y_0)**2 + 2 * self.n * sin(y_0)
        self.r0 = sqrt(self.c - 2 * self.n * sin(y_ref))/self.n

    def project(self, x, y):
        r = sqrt(self.c - 2*self.n*sin(y))/self.n
        t = self.n*(x - self.x_ref)
        return r*sin(t), self.r0 - r*cos(t)


class Bonne:
    def __init__(self, x_ref, y1):
        assert y1 != 0
        self.x_ref = x_ref
        self.y1 = y1

    def project(self, x, y):
        r = 1/tan(self.y1) + self.y1 - y
        t = (x - self.x_ref)*cos(y)/r
        return r*sin(t), 1/tan(self.y1) - y*cos(t)


class Bottomley:
    def __init__(self, x_ref, y_ref):
        self.sy_ref = sin(y_ref)
        self.x_ref = x_ref

    def project(self, x, y):
        r = pi/2 - y
        t = x*self.sy_ref*sin(r)/r
        return r*sin(t), pi/2 - r*cos(t)


class Cassini:
    def __init__(self, x_ref):
        self.x_ref = x_ref

    def project(self, x, y):
        return asin(cos(y)*sin(x - self.x_ref)), atan2(sin(y), cos(y)*cos(x - self.x_ref))


class EquidistantConic:
    def __init__(self, x_ref, y_ref, y1, y2):
        self.x_ref = x_ref
        self.n = (sin(y1) + sin(y2))/2
        self.c = cos(y1)**2 + 2 * self.n * sin(y1)
        self.r0 = sqrt(self.c - 2 * self.n * sin(y_ref))/self.n

    def project(self, x, y):
        r = sqrt(self.c - 2*self.n*sin(y))/self.n
        t = self.n*(x - self.x_ref)
        return r*sin(t), self.r0 - r*cos(t)


class Sinusoidal:
    def __init__(self, x_ref):
        self.x_ref = x_ref

    def project(self, x, y):
        return (x - self.x_ref)*cos(y), y


class Gnomonic:
    def __init__(self, x_ref, y_ref):
        self.sy = sin(y_ref)
        self.cy = cos(y_ref)
        self.x_ref = x_ref

    def project(self, x, y):
        cc = self.sy*sin(y) + self.cy*cos(y)*cos(x - self.x_ref)
        return cos(y)*sin(x - self.x_ref)/cc, (self.cy*sin(y) - self.sy*cos(y)*cos(x - self.x_ref))/cc


class Hammer:
    def __init__(self, x_ref):
        self.x_ref = x_ref

    def project(self, x, y):
        d = sqrt(2/(1 + cos(y)*sin((x - self.x_ref)/2)))
        return 2*cos(y)*sin((x - self.x_ref)/2)*d, sin(y)*d


class KavrayskiyVII:
    def __init__(self, x_ref):
        self.x_ref = x_ref

    def project(self, x, y):
        return 3*(x - self.x_ref)*sqrt(1./3 - (y/pi)**2)/2, y


class Mercator:
    def __init__(self, x_ref):
        self.x_ref = x_ref

    def project(self, x, y):
        return x - self.x_ref, log((1 + sin(y))/(1-sin(y)))


class PlateCarree:
    def __init__(self, x_ref, y_ref):
        self.x_ref = x_ref
        self.y_ref = y_ref

    def project(self, x, y):
        return x - self.x_ref, y - self.y_ref


class Mollweide:
    def __init__(self, x_ref):
        self.x_ref = x_ref

    @staticmethod
    def t(y):
        if abs(cos(2*y) + 1) < epsilon:
            return sin(y), cos(y)
        t0 = t1 = y
        while True:
            try:
                t1 = t0 - (2*t0 + sin(2*t0) - pi*sin(y))/(2 + 2 * cos(2*t0))
            except ValueError:
                print y/pi, t0/pi, t1/pi, cos(2*y)
                exit()
            if abs(t1-t0) < epsilon:
                break
            t0 = t1
        return sin(t1), cos(t1)

    def project(self, x, y):
        st, ct = self.t(y)
        return 2*sqrt(2)*(x - self.x_ref)*ct/pi, sqrt(2)*st


class WinkelTripel:
    def __init__(self, x_ref, y_ref):
        self.x_ref = x_ref
        self.y_ref = y_ref

    def project(self, x, y):
        a = sinc(acos(cos(y)*cos((x-self.x_ref)/2)))
        return ((x-self.x_ref)*cos(self.y_ref) + 2*cos(y)*sin((x-self.x_ref)/2)*a)/2, (y + sin(y)*a)/2


def create_projection(name, x_ref, y_ref, x_0, x_1, y_0, y_1, d):
    logger.info('Creating `{}` centered ({:.2f}, {:.2f},) with {}'.format(name, x_ref, y_ref, d))
    if name == 'Aitoff':
        return Aitoff(x_ref)
    elif name == 'Albers':
        return Albers(x_ref, y_ref, y_0, y_1)
    elif name == 'Bonne':
        return Bonne(x_ref, y_ref)
    elif name == 'Bottomley':
        return Bottomley(x_ref, y_ref)
    elif name == 'Cassini':
        return Cassini(x_ref)
    elif name == 'Gnomonic':
        return Gnomonic(x_ref, y_ref)
    elif name == 'Hammer':
        return Hammer(x_ref)
    elif name == 'KavrayskiyVII':
        return KavrayskiyVII(x_ref)
    elif name == 'Mercator':
        return Mercator(x_ref)
    elif name == 'Mollweide':
        return Mollweide(x_ref)
    elif name == 'PlateCarree':
        return PlateCarree(x_ref, y_ref)
    elif name == 'Sinusoidal':
        return Sinusoidal(x_ref)
    elif name == 'WinkelTripel':
        return WinkelTripel(x_ref, y_ref)
    else:
        logger.error('Projection `{}` is not known'.format(name))
