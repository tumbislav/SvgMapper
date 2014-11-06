# encoding: utf-8
from math import *
from mapper_helper import *
try:
    from scipy.interpolate import interp1d
except ImportError:
    interp1d = None


epsilon = 0.0001


def sinc(a):
    if abs(a) < epsilon:
        return 1
    else:
        return a/sin(a)


def oblique(x, y, x_p, y_p):
    #TODO: unroll the Riemann sheets properly, clip and move the overhangs, smooth over the simgularities
    a = sin(y_p)*sin(y) - cos(y_p)*cos(y)*cos(x)
    y1 = asin(a)
    if sin(y_p)*cos(y) + cos(y_p)*sin(y)*cos(x)<0:
        if y > 0:
            y1 = pi - y1
        else:
            y1 = -pi - y1
    x1 = asin(cos(y)*sin(x)/cos(y1)) - x_p

    if cos(x) < -tan(y1)*cos(y_p)*sin(x):
        x1 = pi - x1
    if y1 > pi/2:
        y1 -= pi
    if y1 < -pi/2:
        y1 += pi

    return x1, y1


class Aitoff:
    def __init__(self, y_ref, y_0, y_1, d):
        pass

    def project(self, x, y):
        a = sinc(acos(cos(y)*cos(x/2)))
        return 2*cos(y)*sin(x/2)*a, sin(y)*a


class Albers:
    def __init__(self, y_ref, y_0, y_1, d):
        self.n = (sin(y_0) + sin(y_1))/2
        self.c = cos(y_0)**2 + 2 * self.n * sin(y_0)
        self.r0 = sqrt(self.c - 2 * self.n * sin(y_ref))/self.n

    def project(self, x, y):
        r = sqrt(self.c - 2*self.n*sin(y))/self.n
        t = self.n*x
        return r*sin(t), self.r0 - r*cos(t)


class Bonne:
    def __init__(self, y_ref, y_0, y_1, d):
        self.y1 = y_ref
        self.coty = 1/tan(y_ref)

    def project(self, x, y):
        r = self.coty + self.y1 - y
        t = x*cos(y)/r
        return r*sin(t), self.coty - r*cos(t)


class Bottomley:
    def __init__(self, y_ref, y_0, y_1, d):
        self.sy_ref = sin(y_ref)

    def project(self, x, y):
        r = pi/2 - y
        if abs(r) < epsilon:
            t = x*self.sy_ref
        else:
            t = x*self.sy_ref*sin(r)/r
        return r*sin(t), pi/2 - r*cos(t)


class Cassini:
    def __init__(self, y_ref, y_0, y_1, d):
        pass

    def project(self, x, y):
    #TODO: fix the projection for objects that extend across 180th meridian
        return asin(cos(y)*sin(x)), atan2(tan(y), cos(x))


class Cylindrical:
    def __init__(self, y_ref, y_0, y_1, d):
        self.y_ref = y_ref
        variant = get_or_default(d, 'variant', 'Plate-Carree')
        if variant == 'Lambert':
            self.fy = lambda y: sin(y)
        elif variant == 'Plate-Carree':
            self.fy = lambda y: y
        elif variant == 'Central':
            self.fy = lambda y: tan(y)
        else:
            raise MapperException(MX_WRONG_VALUE, 'Cylindrical.__init__', 'variant', variant)

    def project(self, x, y):
        return x, self.fy(y - self.y_ref)


class EquidistantConic:
    def __init__(self, y_ref, y_0, y_1, d):
        self.n = (sin(y_0) + sin(y_1))/2
        self.c = cos(y_0)**2 + 2 * self.n * sin(y_0)
        self.r0 = sqrt(self.c - 2 * self.n * sin(y_ref))/self.n

    def project(self, x, y):
        r = sqrt(self.c - 2*self.n*sin(y))/self.n
        t = self.n*x
        return r*sin(t), self.r0 - r*cos(t)


class Gnomonic:
    def __init__(self, y_ref, y_0, y_1, d):
        self.sy = sin(y_ref)
        self.cy = cos(y_ref)

    def project(self, x, y):
        cc = self.sy*sin(y) + self.cy*cos(y)*cos(x)
        return cos(y)*sin(x)/cc, (self.cy*sin(y) - self.sy*cos(y)*cos(x))/cc


class Hammer:
    def __init__(self, y_ref, y_0, y_1, d):
        pass

    def project(self, x, y):
        d = sqrt(2/(1 + cos(y)*cos(x/2)))
        return 2*cos(y)*sin(x/2)*d, sin(y)*d


class KavrayskiyVII:
    def __init__(self, y_ref, y_0, y_1, d):
        pass

    def project(self, x, y):
        return 3*x*sqrt(1./3 - (y/pi)**2)/2, y


class Mercator:
    def __init__(self, y_ref, y_0, y_1, d):
        if 'oblique' in d:
            self.x_pole, self.y_pole = d['oblique']
            self.project = self.oblique
        elif 'transverse' in d:
            self.project = self.transverse
        else:
            self.project = self.normal
        self.cutoff = get_or_default(d, 'cutoff', 80)
        self.cutoff *= pi/180

    def transverse(self, x, y):
        a = cos(y)*sin(x)
        a = max(min(a, self.cutoff), -self.cutoff)
        return log((1+a)/(1-a))/2, atan2(tan(y), cos(x))

    def oblique(self, x, y):
        a = sin(self.y_pole)*sin(y) + cos(self.y_pole)*cos(y)*cos(x-self.x_pole)
        a = max(min(a, self.cutoff), -self.cutoff)
        return log((1+a)/(1-a))/2, atan2(cos(self.y_pole)*sin(y) - sin(self.y_pole)*cos(y)*cos(x-self.x_pole),
                                         cos(y)*sin(x-self.x_pole))

    def normal(self, x, y):
        y = max(min(y, self.cutoff), -self.cutoff)
        return x, log(tan(pi/4 + y/2))


class Mollweide:
    def __init__(self, y_ref, y_0, y_1, d):
        pass

    def theta(self, y):
        if abs(cos(2*y) + 1) < epsilon:
            return y
        t0 = t1 = y
        while True:
            try:
                t1 = t0 - (2*t0 + sin(2*t0) - pi*sin(y))/(2 + 2*cos(2*t0))
            except ValueError:
                exit()
            if abs(t1 - t0) < epsilon:
                break
            t0 = t1
        return t1

    def project(self, x, y):
        t = self.theta(y)
        return 2*sqrt(2)*x*cos(t)/pi, sqrt(2)*sin(t)


class Robinson:
    _a = [0.8487, 0.84751182, 0.84479598, 0.840213, 0.83359314, 0.8257851, 0.814752, 0.80006949, 0.78216192, 0.76060494,
          0.73658673, 0.7086645, 0.67777182, 0.64475739, 0.60987582, 0.57134484, 0.52729731, 0.48562614, 0.45167814]
    _b = [0, 0.0838426, 0.1676852, 0.2515278, 0.3353704, 0.419213, 0.5030556, 0.5868982, 0.67182264, 0.75336633,
          0.83518048, 0.91537187, 0.99339958, 1.06872269, 1.14066505, 1.20841528, 1.27035062, 1.31998003, 1.3523]
    _y = [0.0, 0.08726646259971647, 0.17453292519943295, 0.2617993877991494, 0.3490658503988659, 0.4363323129985824,
          0.5235987755982988, 0.6108652381980153, 0.6981317007977318, 0.7853981633974483, 0.8726646259971648,
          0.9599310885968813, 1.0471975511965976, 1.1344640137963142, 1.2217304763960306, 1.3089969389957472,
          1.3962634015954636, 1.4835298641951802, 1.57079632679]

    def __init__(self, y_ref, y_0, y_1, d):
        if interp1d:
            self.interpolate = self.interpolate_quadratic
            self.inter_a = interp1d(self._y, self._a, 'quadratic', copy=False, assume_sorted=True)
            self.inter_b = interp1d(self._y, self._b, 'quadratic', copy=False, assume_sorted=True)
        else:
            logger.warn("Robinson projection: sciPy not installed, defaulting to linear interpolation.")
            self.interpolate = self.interpolate_linear

    def interpolate_linear(self, y):
        i = int(y*36/pi)
        if i == 18:
            return self._a[i], self._b[i]
        else:
            dy = y*36/pi - float(i)
            return self._a[i] + (self._a[i + 1] - self._a[i])*dy, self._b[i] + (self._b[i + 1] - self._b[i])*dy

    def interpolate_quadratic(self, y):
        return self.inter_a(y), self.inter_b(y)

    def project(self, x, y):
        """ inter1d is sensitive to out-of-bounds conditions, and it uses higher precision arithmetic internally.
        To avoid rounding errors around y=pi/2, clip the latitude. """
        f_a, f_b = self.interpolate(min(abs(y), 1.57079632679))
        return x*f_a, copysign(f_b, y)


class Sinusoidal:
    def __init__(self, y_ref, y_0, y_1, d):
        pass

    def project(self, x, y):
        return x*cos(y), y


class WinkelTripel:
    def __init__(self, y_ref, y_0, y_1, d):
        self.y_ref = y_ref

    def project(self, x, y):
        a = sinc(acos(cos(y)*cos(x/2)))
        return (x*cos(self.y_ref) + 2*cos(y)*sin(x/2)*a)/2, (y + sin(y)*a)/2


projection_classes = {'Aitoff': Aitoff,
    'Albers': Albers,
    'Bonne': Bonne,
    'Bottomley': Bottomley,
    'Cassini': Cassini,
    'Cylindrical': Cylindrical,
    'Equidistant-Conic': EquidistantConic,
    'Gnomonic': Gnomonic,
    'Hammer': Hammer,
    'Kavrayskiy-VII': KavrayskiyVII,
    'Mercator': Mercator,
    'Mollweide': Mollweide,
    'Robinson': Robinson,
    'Sinusoidal': Sinusoidal,
    'Winkel-Tripel': WinkelTripel}
