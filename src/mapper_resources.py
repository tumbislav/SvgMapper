# encoding: utf-8
__author__ = 'Marko Čibej'
import copy
from mapper_helper import *
from projections import *
import svgfig
import re
from math import pi
import os


class Resource:
    """
    Base class for all resources. Doesn't do much except to identify the resources as such.
    """
    def __init__(self):
        self.name = None
        pass

    def __str__(self):
        return self.name or '(unnamed)'

    def is_a(self, name):
        return self.__class__.__name__ == name


class Style(Resource):
    """
    Encapsulates an svg style or any set of values that a tag can have.

    __init__ accepts the following kinds of inputs:

    A dict of the form {'name': 'the name', 'attrs': { 'attr': 'value' ...}}. Constructs a fully fledged, named style.

    A dict with only the attribute-value pairs: { 'attr': 'value' ...}. Constructs an anonymous in-line style

    None: constructs an empty style that has no effect on the elements it styles.
    """
    def __init__(self, d):
        Resource.__init__(self)
        if d is None:
            self.name = None
            self.attributes = {}
        elif 'name' in d:
            try:
                self.name = d['name']
                self.attributes = copy.deepcopy(d['attrs'])
            except KeyError as ke:
                raise MapperException(MX_MISSING_PARAMETER, 'Style.__init__', str(ke), self.name or 'style')
        else:
            self.name = None
            self.attributes = copy.deepcopy(d)
        logger.info(u'Loaded style {}'.format(self))

    def style(self):
        if 'style' in self.attributes:
            return self.attributes['style']
        return ''

    def apply(self, svg):
        """ Apply the style to the svg element by updating the defined attributes and leaving the rest unchanged. """
        for k, v in self.attributes.iteritems():
            if k in svg.attr:
                # style attribute is itself a key:value pair collection. Treat it separately.
                if k == 'style':
                    d_sty = {_1[0].strip(): _1[1].strip() for _1 in [_0.split(':') for _0 in v.split(';')]}
                    d_svg = {_1[0].strip(): _1[1].strip() for _1 in [_0.split(':') for _0 in svg.attr[k].split(';')]}
                    d_svg.update(d_sty)
                    v_out = ';'.join('{}:{}'.format(k1, v1) for k1, v1 in d_svg.iteritems())
                else:
                    v_out = v
                svg.attr[k] = v_out


class Library(Resource):
    """
    A wrapper for an svg file that contains zero or more symbols that can be used in the output.
    __init__ expects the input to be a dictionary of the form

    {'name': library_name, 'filename', svg_filename, 'path', initial_path, 'symbols': {symbol definitions ...}}

    """
    def __init__(self, d, parent):
        Resource.__init__(self)
        try:
            self.path = d['path']
            self.name = d['name']
            self.filename = d['filename']
            self.symbols = {k: Symbol(v, self) for k, v in d['symbols'].items()}
        except KeyError as ke:
            raise MapperException(MX_MISSING_PARAMETER, 'Library.__init__', str(ke), self.name or 'library')
        self.path = os.path.join(parent.path, self.path)
        self.svg = None
        logger.info(u'Loaded library {}'.format(self))

    def load_symbol(self, name):
        """ Locates and returns the symbol's svg. """
        if self.svg is None:
            self.svg = svgfig.load(os.path.join(self.path, self.filename))
        for k, s in self.svg:
            if isinstance(s, svgfig.SVG):
                if 'id' in s.attr and name == s.attr['id']:
                    return s
        return None

    def get_symbol(self, name):
        try:
            return self.symbols[name]
        except KeyError:
            raise MapperException(MX_UNRESOLVED_REFERENCE, 'Library.get_symbol', 'symbol', name)


class Symbol(Resource):
    """
    Either a single path element or an svg group containing paths and possible sub-groups. A symbol can be placed
    in the output file in a single operation.

    __init__ expects the input to be a dictionary of the form

    {'id': svg_id, 'scale': scale, 'anchor': [x_anchor, y_anchor]}

    If the scale is skipped, it's defaulted to 1.0
    """
    def __init__(self, d, library):
        Resource.__init__(self)
        self.library = library
        self.svg = self.fig = None
        if isinstance(d, dict):
            try:
                self.scale = get_or_default(d, 'scale', 1.0)
                self.anchor = d['anchor']
                if not isinstance(self.anchor, list):
                    raise MapperException(MX_WRONG_VALUE, 'Symbol.__init__', 'anchor', 'list')
                self.id = d['id']
            except KeyError as ke:
                raise MapperException(MX_MISSING_PARAMETER, 'Symbol.__init__', str(ke), 'symbol')
        elif isinstance(d, svgfig.SVG):
            self.svg = d
        logger.info(u'Loaded symbol {}'.format(self))

    def get_svg(self):
        """ Return the symbol's svg, possibly loading it if needed. """
        if self.svg is None:
            self.svg = self.library.load_symbol(self.id)
        if self.svg is None:
            raise MapperException(MX_MISSING_SVG, 'Symbol.get_svg', self.id, self.library.name)
        return self.svg


class Rectangle(Resource):
    """
    A rectangle. This can be constructed from:

    - a dictionary of the form {'name': name, 'at': [x0, y0, x1, y1]}

    - list of four values of the form [x0, y0, x1, y1]

    - another Rectangle instance

    - an SVG path element which contains attributes 'lon-min', 'lat-min', 'lon-max' and 'lat-max'

    - None, which results in a rectangle [0,0,1,1]
    """
    def __init__(self, d=None):
        Resource.__init__(self)
        if isinstance(d, dict):
            self.__init_named(d)
        elif isinstance(d, list):
            self.__init_anonymous(d)
        elif isinstance(d, Rectangle):
            self.__init_copy(d)
        elif isinstance(d, svgfig.SVG):
            self.__init_svg(d)
        elif d is None:
            self.name = None
            self.x0 = self.y0 = 0.0
            self.x1 = self.y1 = 1.1
        else:
            raise MapperException(MX_UNEXPECTED, 'Rectangle.__init__', 'cannot construct a rectangle from', d)
        logger.info('Loaded rectangle {}'.format(self))

    def __init_named(self, d):
        """ Construct a named rectangle from a dictionary """
        self.name = get_or_default(d, 'name', None)
        try:
            at = d['at']
            self.x0 = float(at[0])
            self.y0 = float(at[1])
            self.x1 = float(at[2])
            self.y1 = float(at[3])
        except KeyError as ke:
            raise MapperException(MX_MISSING_PARAMETER, 'Rectangle.__init__', str(ke), self.name or 'rectangle')
        except IndexError:
            raise MapperException(MX_MISSING_PARAMETER, 'Rectangle.__init__', '(coordinate)', 'rectangle at array')

    def __init_anonymous(self, d):
        """ Construct an anonymous rectangle """
        try:
            self.x0, self.y0, self.x1, self.y1 = d[0], d[1], d[2], d[3]
        except IndexError:
            raise MapperException(MX_MISSING_PARAMETER, 'Rectangle.__init__', '(coordinate)', 'input array')

    def __init_copy(self, d):
        """Duplicate an existing rectangle"""
        self.name = (d.name or '') + ' (copy)'
        self.x0 = d.x0
        self.x1 = d.x1
        self.y0 = d.y0
        self.y1 = d.y1

    def __init_svg(self, d):
        """ Initialize from an SVG path element with bounding attributes """
        try:
            self.x0 = float(d.attr['lon-min'])
            self.y0 = float(d.attr['lat-min'])
            self.x1 = float(d.attr['lon-max'])
            self.y1 = float(d.attr['lat-max'])
        except KeyError as ke:
            raise MapperException(MX_MISSING_PARAMETER, 'Rectangle.__init__', str(ke), 'input path')

    def bounding_box_svg(self, s):
        """ Measure an svg path and set the rectangle to the bounding box """
        p = svgfig.pathtoPath(s)
        self.x0, self.y0, self.x1, self.y1 = path_bounding_box(p)
        return self

    def orient(self, y_negative=False):
        """ Enforce the rectangle's orientation and optionally flip the y axis """
        self.x0, self.x1 = min(self.x1, self.x0), max(self.x1, self.x0)
        if y_negative:
            self.y1, self.y0 = min(self.y1, self.y0), max(self.y1, self.y0)
        else:
            self.y0, self.y1 = min(self.y1, self.y0), max(self.y1, self.y0)
        return self


class Unit(Resource):
    """
    A real world scaling unit defined in the resource file. This is the only way for the system to know
    what a kilometre is, or, conversely, what the circumference of your planet might be. The scale is
    given in radians along the great circle.

    A unit is instantiated from a dictionary of the form {'name': name, 'scale': scale}
    """
    def __init__(self, d):
        Resource.__init__(self)
        try:
            self.name = d['name']
            self.scale = float(d['scale'])
        except KeyError as ke:
            raise MapperException(MX_MISSING_PARAMETER, 'Unit.__init__', str(ke), self.name or 'unit')
        except ValueError as ve:
            raise MapperException(MX_WRONG_VALUE, 'Unit.__init__', self.name, str(ve))
        logger.info(u'Loaded unit `{}` scaled {}'.format(self, self.scale))

    def move_to(self, x, y, d, a):
        """
        Given a starting point (x, y) expressed in radians, find the terminus of a path
        at a distance of d units, along a great circle  which lies at an angle a from due east.

        If (φ0, λ0) is the start and (φ1, λ1) the end point, with θ the starting bearing and δ the angular distance,
        then great-circle distance d is given in terms of unit scale U as
            d = δ / U
        The end point is then given by:
            φ1 = asin(sin φ0 cos δ + cos φ0 sin δ sin θ)
            λ1 = λ0 + atan2(cos θ sin δ cos φ0, cos δ − sin φ0 sin φ1)
        """
        d *= self.scale
        y1 = asin(sin(y)*cos(d) + cos(y)*sin(d)*sin(a))
        x1 = x + atan2(cos(a)*sin(d)*cos(y), cos(d) - sin(y)*sin(y1))
        return x1, y1

    def measure(self, x0, y0, x1, y1):
        """
        Given two points expressed in radians, return the great circle distance between them in
        unit scale. The distance is given as
            d = 2 atan2(√a, √(1−a)) / U
        where
            a = sin²(Δφ/2) + cos φ0 cos φ1 sin²(Δλ/2)
        and φ, λ are longitude and latitude respectively
        """
        a = sin((y1 - y0)/2)**2 + cos(y0)*cos(y1)*(sin((x1 - x0)/2)**2)
        return 2*atan2(sqrt(a), sqrt(1 - a))/self.scale


class Projection(Resource):
    """
    The projection is re-entrant in the sense that a second map may initialize the same projection instance
    with a different world rectangle and use it without issues.

    A projection is constructed from:
    {'name': name, 'class': projection_class, 'center-x', ...}

    The remaining parameters are optional:
            'central-meridian':
            'reference-parallel':
            'center-x':
            'center-y':
            'standard-parallel1':
            'standard-parallel2':
    """
    #TODO: handle optional arguments as kwargs to projection classes
    def __init__(self, d):
        Resource.__init__(self)
        try:
            self.name = get_or_default(d, 'name', None, True)
            self.cls = d['class']
            del d['class']
            self.projection = None
        except KeyError as ke:
            raise MapperException(MX_MISSING_PARAMETER, 'Projection.__init__', str(ke), self.name or 'projection')
        self.y_0 = get_or_default(d, 'standard-parallel-1', None, True)
        self.y_1 = get_or_default(d, 'standard-parallel-2', None, True)
        self.y_0 = get_or_default(d, 'standard-meridian-1', None, True)
        self.x_1 = get_or_default(d, 'standard-meridian-2', None, True)
        self.x_ref = get_or_default(d, 'central-meridian', None, True)
        self.y_ref = get_or_default(d, 'reference-parallel', None, True)
        self.d = d
        logger.info(u'Loaded projection {}'.format(self))

    def initialize(self, the_map):
        """ Figure out a sensible parametrization for the projection, using the data that is given and guessing
        that which is not.

        If central meridian is given, use it
            else, if center-x is specified, set central meridian to world rectangle midpoint
            else, set central meridian to 0
        if projection requires a central parallel, do the same
        if two reference parallels are needed
            if they are given, use them
            if only one is given, set both to that
            else, set them to bottom and top of world rectangle
        if one reference parallel is needed
            if given, use it
            else if a central parallel is given, use that
            else set it to the centre of the world rectangle
        :param the_map: The the_map that is using the projection
        """
        try:
            if self.x_ref is None or (isinstance(self.x_ref, basestring) and self.x_ref == 'center'):
                    self.x_ref = (the_map.rect_world.x0 + the_map.rect_world.x1)*pi/360
            else:
                self.x_ref *= pi/180
            if self.y_ref is None or (isinstance(self.y_ref, basestring) and self.y_ref == 'center'):
                    self.y_ref = (the_map.rect_world.y0 + the_map.rect_world.y1)*pi/360
            else:
                self.y_ref *= pi/180
            self.y_0 = (self.y_0 if self.y_0 else the_map.rect_world.y0)*pi/180
            self.y_1 = (self.y_1 if self.y_1 else the_map.rect_world.y1)*pi/180
            self.x_0 = (self.x_0 if self.x_0 else the_map.rect_world.x0)*pi/180
            self.x_1 = (self.x_1 if self.x_1 else the_map.rect_world.x1)*pi/180
        except:
            raise MapperException(MX_WRONG_VALUE, 'Projection.initialize','reference-parallel', y_ref)

        self.projection =
        return self

    def project(self, x, y):
        return self.projection.project(x, y)


class Match(Resource):
    """
    Given an svg type, the name of a layer and/or a set of attribute matches, return the set of matching
    SVG objects from the source file.

    A dictionary of the following form builds a named Match
    {'name': name, 'rule':{'layer': layer_path, 'pattern':{...}, 'svg-type': type}}

    If only the inner dictionary is present, an anonymous match is created.

    If only a single string it given, the result is a match that looks for an element with that id
    through all layers.
    """

    def __init__(self, d):
        Resource.__init__(self)
        self.name = None
        self.layer = []
        self.is_compiled = False
        if d is None:
            self.pattern = {}
        elif isinstance(d, basestring):
            self.pattern = {'id': d}
            self.svg_type = 'path'
        elif isinstance(d, dict):
            self.name = get_or_default(d, 'name', None)
            if 'rule' in d:
                dd = d['rule']
            else:
                dd = d
            if 'layer' in dd:
                self.layer = dd['layer'].split('::')
            self.svg_type = get_or_default(dd, 'svg-type', 'path')
            self.pattern = get_or_default(dd, 'pattern', {})
        logger.info(u'Loaded match `{}`'.format(self))

    def set_svg_type(self, t):
        """ Set the svg type of objects that are sought. """
        self.svg_type = t

    def compile(self):
        """ Build regexp statements for self.pattern """
        for p in self.pattern:
            self.pattern[p] = re.compile(self.pattern[p])
        self.is_compiled = True

    def locate_layer(self, begin, layer_iterator):
        """
        Recursively climbs to the (sub-)layer defined by layer_iterator (i.e. the underlying self_layer array)
        :param begin: starting layer or the entire svg file
        :param layer_iterator: returns the next element of the layer path
        :return: The layer, or None if the layer is not found
        """
        try:
            layer = layer_iterator.next()
        except StopIteration:
            return begin
        for k, s in begin:
            if isinstance(s, svgfig.SVG) and s.t == 'g' and 'inkscape:groupmode' in s.attr:
                if s.attr['inkscape:label'] == layer:
                    return self.locate_layer(s, layer_iterator)
        return None

    def iter(self, svg_file):
        """
        Returns an iterator over matching objects.
        """
        if not self.is_compiled:
            self.compile()
        start = self.locate_layer(svg_file, iter(self.layer))
        return matched_only(start, self.does_match)

    def does_match(self, s):
        if s.t != self.svg_type:
            return False
        for p in self.pattern:
            if not p in s.attr or self.pattern[p].search(s.attr[p]) is None:
                return False
        return True