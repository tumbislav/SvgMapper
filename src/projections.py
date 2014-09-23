# encoding: utf-8
from math import *
from mapper_helper import logger
#from scipy.interpolate import interp1d


epsilon = 0.0001


class Aitoff:
    def __init__(self, x0):
        self.x0 = x0

    def project(self, x, y):
        a = acos(cos(y)*cos((x-self.x0)/2))
        if abs(a) < epsilon:
            sinc = 1
        else:
            sinc = a/sin(a)
        return 2*cos(y)*sin((x-self.x0)/2)*sinc, sin(y)*sinc


class Albers:
    def __init__(self, x0, y0, **kwargs):
        self.x0 = x0
        self.n = (sin(kwargs['reference-parallel-1']) + sin(y2))/2
        self.c = cos(y1)**2 + 2 * self.n * sin(y1)
        self.r0 = sqrt(self.c - 2 * self.n * sin(y0))/self.n

    def project(self, x, y):
        r = sqrt(self.c - 2*self.n*sin(y))/self.n
        t = self.n*(x - self.x0)
        return r*sin(t), self.r0 - r*cos(t)


class Bonne:
    def __init__(self, x0, y1):
        assert y1 != 0
        self.x0 = x0
        self.y1 = y1

    def project(self, x, y):
        r = 1/tan(self.y1) + self.y1 - y
        t = (x - self.x0)*cos(y)/r
        return r*sin(t), 1/tan(self.y1) - y*cos(t)


class Bottomley:
    def __init__(self, x0, y0):
        self.sy0 = sin(y0)
        self.x0 = x0

    def project(self, x, y):
        r = pi/2 - y
        t = x*self.sy0*sin(r)/r
        return r*sin(t), pi/2 - r*cos(t)


class Cassini:
    def __init__(self, x0):
        self.x0 = x0

    def project(self, x, y):
        return asin(cos(y)*sin(x - self.x0)), atan2(sin(y), cos(y)*cos(x - self.x0))


class EquidistantConic:
    def __init__(self, x0, y0, y1, y2):
        self.x0 = x0
        self.n = (sin(y1) + sin(y2))/2
        self.c = cos(y1)**2 + 2 * self.n * sin(y1)
        self.r0 = sqrt(self.c - 2 * self.n * sin(y0))/self.n

    def project(self, x, y):
        r = sqrt(self.c - 2*self.n*sin(y))/self.n
        t = self.n*(x - self.x0)
        return r*sin(t), self.r0 - r*cos(t)


class Sinusoidal:
    def __init__(self, x0):
        self.x0 = x0

    def project(self, x, y):
        return (x - self.x0)*cos(y), y


class Gnomonic:
    def __init__(self, x0, y0):
        self.sy = sin(y0)
        self.cy = cos(y0)
        self.x0 = x0

    def project(self, x, y):
        cc = self.sy*sin(y) + self.cy*cos(y)*cos(x - self.x0)
        return cos(y)*sin(x - self.x0)/cc, (self.cy*sin(y) - self.sy*cos(y)*cos(x - self.x0))/cc


class Hammer:
    def __init__(self, x0):
        self.x0 = x0

    def project(self, x, y):
        d = sqrt(2/(1 + cos(y)*sin((x - self.x0)/2)))
        return 2*cos(y)*sin((x - self.x0)/2)*d, sin(y)*d


class KavrayskiyVII:
    def __init__(self, x0):
        self.x0 = x0

    def project(self, x, y):
        return 3*(x - self.x0)*sqrt(1./3 - (y/pi)**2)/2, y


class Mercator:
    def __init__(self, x0):
        self.x0 = x0

    def project(self, x, y):
        return x - self.x0, log((1 + sin(y))/(1-sin(y)))


class PlateCarree:
    def __init__(self, x0, y0):
        self.x0 = x0
        self.y0 = y0

    def project(self, x, y):
        return x - self.x0, y - self.y0


class Mollweide:
    def __init__(self, x0):
        self.x0 = x0

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
        return 2*sqrt(2)*(x - self.x0)*ct/pi, sqrt(2)*st


class WinkelTripel:
    def __init__(self, x0, y0):
        self.x0 = x0
        self.y0 = y0

    def project(self, x, y):
        a = acos(cos(y)*cos((x-self.x0)/2))
        if abs(a) < epsilon:
            sinc = 1
        else:
            sinc = a/sin(a)
        return ((x-self.x0)*cos(self.y0) + 2*cos(y)*sin((x-self.x0)/2)*sinc)/2, (y + sin(y)*sinc)/2


def create_projection(name, x0, y0, d):
    logger.info('Creating `{}` centered ({:.2f}, {:.2f},) with {}'.format(name, x0, y0, d))
    if name == 'Aitoff':
        return Aitoff(x0)
    elif name == 'Albers':
        return Albers(x0, y0, **d)
    elif name == 'Bonne':
        return Bonne(x0, y0)
    elif name == 'Bottomley':
        return Bottomley(x0, y0)
    elif name == 'Cassini':
        return Cassini(x0)
    elif name == 'Gnomonic':
        return Gnomonic(x0, y0)
    elif name == 'Hammer':
        return Hammer(x0)
    elif name == 'KavrayskiyVII':
        return KavrayskiyVII(x0)
    elif name == 'Mercator':
        return Mercator(x0)
    elif name == 'Mollweide':
        return Mollweide(x0)
    elif name == 'PlateCarree':
        return PlateCarree(x0, y0)
    elif name == 'Sinusoidal':
        return Sinusoidal(x0)
    elif name == 'WinkelTripel':
        return WinkelTripel(x0, y0)
    else:
        logger.error('Projection `{}` is not known'.format(name))
