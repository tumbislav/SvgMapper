# encoding: utf-8
__author__ = 'Marko Čibej'

import svgfig_mc
import logging
from itertools import chain


logger = logging.getLogger('SvgMapper')


def get_or_default(d, key, default, delete=False):
    """ Returns the value specified by the key or the specified default. """
    if key in d:
        k = d[key]
        if delete:
            del d[key]
        return k
    else:
        return default


def pairwise(lst):
    """ Iterate over pairs of values from a list """
    i = iter(lst)
    while True:
        yield (i.next(), i.next())


def inner_pairs(lst):
    """ Iterate over dictionaries inside a list """
    i = iter(lst)
    while True:
        (k, v), = i.next().items()
        yield k, v


class MatchIterator:
    """
    Replacement for svgfig depth iterator that does pattern matching.
    """

    def __init__(self, svg, match):
        self.svg = svg
        self.shown = False
        self.match = match
        self.iterators = None
        self.matched = False

    def __iter__(self):
        return self

    def next(self):
        if not isinstance(self.svg, svgfig_mc.SVG):
            raise StopIteration

        self.matched = self.match(self.svg)
        if not self.shown:
            self.shown = True
            return self.matched, self.svg

        # prune branches that match
        if self.matched:
            raise StopIteration

        if not self.iterators:
            self.iterators = [MatchIterator(_, self.match) for _ in self.svg.sub]
            self.iterators = chain(*self.iterators)

        return self.iterators.next()


def matched_only(svg, matcher):
    i = MatchIterator(svg, matcher)
    while True:
        m, s = i.next()
        if m:
            yield s


def svg_center(svg):
    """ Find and return the center of a svg path or group. Only path elements are considered. """
    if svg.t == 'path':
        bounding_box = path_bounding_box(svgfig_mc.pathtoPath(svg))
    else:
        bounding_box = None
        for i, p in svg:
            if isinstance(p, svgfig_mc.SVG) and p.t == 'path':
                bounding_box = path_bounding_box(svgfig_mc.pathtoPath(p), start_from=bounding_box)
    return (bounding_box[0] + bounding_box[2])/2, (bounding_box[1] + bounding_box[3])/2


def svg_transform(svg, x0, y0, x1, y1, xs=1.0, ys=1.0):
    """ Wrap an svg element in a group and apply a transformation, mapping x0,y0 to x1, y1 and scaling xs and ys."""
    return svgfig_mc.SVG('g', svg, transform='matrix({:f},0,0,{:f},{:f},{:f})'.format(xs, ys, x1 - xs*x0, y1 - ys*y0))


def svg_get_matrix(trans):
    """ Extracts the elements of 'matrix()' from a svg transform, or returns the identity matrix. """
    start = trans.find('matrix(') + 7
    if start > 6:
        end = trans.find(')', start)
        return [float(_.strip()) for _ in trans[start:end].split(',')]
    start = trans.find('translate(') + 10
    if start > 9:
        end = trans.find(')', start)
        x, y = (float(_.strip()) for _ in trans[start:end].split(','))
        return [1., 0., 0., 1., x, y]
    return [1., 0., 0., 1., 0., 0.]


def path_bounding_box(p, start_from=None):
    """ Measure a svg path and return its bounding box. Only moves and line segments are considered """
    if start_from is None:
        x0 = y0 = x1 = y1 = None
    else:
        x0, y0, x1, y1 = start_from
    for dt in p.d:
        command = dt[0]
        if command in ("H", "h"):
            x0, x1 = extend_interval(dt[1], x0, x1)
        elif command in ("V", "v"):
            y0, y1 = extend_interval(dt[1], y0, y1)
        elif command in ("M", "m", "L", "l", "T", "t"):
            x0, x1 = extend_interval(dt[1], x0, x1)
            y0, y1 = extend_interval(dt[2], y0, y1)
    return x0, y0, x1, y1


def extend_interval(t, t_min, t_max):
    """
    Helper function that extends an interval based on the next input value.
    If the interval is undefined, both ends are set to the input. Otherwise,
    if the input falls outside the interval, its boundary is extended appropriately
    """
    if t_min is None or t_max is None:
        return t, t
    if t < t_min:
        return t, t_max
    elif t > t_max:
        return t_min, t
    else:
        return t_min, t_max


def float_to_dms(t, is_latitude, mngr, prefix=''):
    """
    Transform the given floating point number into a dictionary that can be used with a string.format()
    function to produce output such as 15°13'47"E.

    Longitude can wrap around by as much as 180-\epsilon degrees and is normalized.
    """
    d = {}
    if is_latitude:
        if not (-90 <= t <= 90):
            raise MapperException(MX_WRONG_VALUE, 'float-to-dms', 'latitude', t)
        if t > 0:
            d[prefix + 'card'] = mngr.get_string('cardinal-north')
        else:
            d[prefix + 'card'] = mngr.get_string('cardinal-south')
    else:
        if not (-360 < t < 360):
            raise MapperException(MX_WRONG_VALUE, 'float-to-dms', 'longitude', t)
        if t > 180:
            t = t - 360
        if t < -180:
            t = 360 + t
        if t > 0:
            d[prefix + 'card'] = mngr.get_string('cardinal-east')
        else:
            d[prefix + 'card'] = mngr.get_string('cardinal-west')
    t = abs(t)
    d[prefix + 'deg'] = int(t)
    t = (t - int(t)) * 60
    d[prefix + 'min'] = int(t)
    d[prefix + 'sec'] = (t - int(t)) * 60
    return d


class MapperException(Exception):
    """
    All exceptions that we know what to do about.
    """
    def __init__(self, reason, raised, name, value):
        Exception.__init__(self)
        self.reason = reason
        self.raised = raised
        self.name = name
        self.value = value

    def __str__(self):
        if self.reason == MX_UNEXPECTED:
            return u'{}: this should not happen: {} {}'.format(self.raised, self.name, self.value)
        elif self.reason == MX_CONFIG_ERROR:
            return u'{}: config error "{}" {} '.format(self.raised, self.name, self.value)
        elif self.reason == MX_UNRESOLVED_REFERENCE:
            return u'{}: cannot find {} named {}'.format(self.raised, self.name, self.value)
        elif self.reason == MX_UNEXPECTED_PARAMETER:
            return u'{}: {} is unexpected in {}'.format(self.raised, self.name, self.value)
        elif self.reason == MX_MISSING_PARAMETER:
            return u'{}: missing parameter {} in {}'.format(self.raised, self.name, self.value)
        elif self.reason == MX_MISSING_SVG:
            return u'{}: svg element {} not found in {}'.format(self.raised, self.name, self.value)
        elif self.reason == MX_WRONG_VALUE:
            if self.name is None:
                return u'{}: wrong value: {}'.format(self.raised, self.value)
            else:
                return u'{}: wrong value "{}" for parameter {}'.format(self.raised, self.value, self.name)


# Unexpected condition: value=description
MX_UNEXPECTED = 1
# Error in parsing config files: name=filename, value=description
MX_CONFIG_ERROR = 2
# An element that is referred to is not found: name=type of element, value=reference
MX_UNRESOLVED_REFERENCE = 3
# A parameter that is not expected in a particular context: name=parameter, value=context
MX_UNEXPECTED_PARAMETER = 4
# A parameter that is required is missing: name=parameter, value=context
MX_MISSING_PARAMETER = 5
# A svg element was not found: name=element identifier(s), value=source file
MX_MISSING_SVG = 6
# There is something wrong with a parameter somewhere: name=parameter, value=value
MX_WRONG_VALUE = 7
