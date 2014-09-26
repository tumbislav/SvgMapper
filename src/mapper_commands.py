# encoding: utf-8
__author__ = 'Marko Čibej'
from mapper_resources import *
from math import pi
from mapper_helper import logger

from itertools import izip_longest


class Command:
    def __init__(self, d, default_style=None):
        """
        Most commands can be styled and all have a target layer, so take care of this in the base class.
        Default style depends on the subclass.
        """
        if 'style' in d:
            if isinstance(d['style'], basestring):
                self.style = d['style']
            else:
                self.style = Style(d['style'])
        elif default_style is not None:
            self.style = default_style
        else:
            self.style = None
        self.target = get_or_default(d, 'target', 'default')

    def require_style(self, s, the_map):
        """ Resolve and return the style. If it is named, it must exist. If it's None, an empty style will do. """
        if s is None:
            return Style(None)
        st = the_map.get_style(s)
        if st is None:
            raise MapperException(MX_UNRESOLVED_REFERENCE, self.__class__.__name__ + '.require_style', 'style', s)
        return st

    def require_match(self, m, the_map):
        """ Resolve and return the match. An empty match must is not possible. """
        if m is None:
            raise MapperException(MX_UNRESOLVED_REFERENCE,
                                  self.__class__.__name__ + '.require_match', 'empty match', 'None')
        mt = the_map.get_match(m)
        if mt is None:
            raise MapperException(MX_UNRESOLVED_REFERENCE, self.__class__.__name__, 'match', m)
        return mt


class Project(Command):
    """
    Take either a set of paths, or texts, or symbols (which can be paths or groups of paths)
    selected by the match argument and map them to the target file, possibly applying a style to them.
    If symbols are selected, they can optionally be replaced by a replacement symbol from a library.

    To construct it we need a dictionary of the form
        {'what': project_what, 'match': the_match, 'replacement-symbol': symbol, 'style': style, 'target': target_layer}
    """

    content_types = {'paths': 'path', 'texts': 'text', 'marks': 'g'}


    def __init__(self, d):
        Command.__init__(self, d)
        try:
            self.what = d['what']
            self.match = d['match']
            self.replacement = get_or_default(d, 'replacement-symbol', None)
        except KeyError as ke:
            raise MapperException(MX_MISSING_PARAMETER, 'Project.__init__', 'project', ke)
        if not self.what in self.content_types:
            raise MapperException(MX_WRONG_VALUE, 'Project.__init__', name='Project', value=self.what)
        logger.info(u'Loaded Project {}'.format(self.what))

    def run(self, the_map):
        """
        Select the matching items and project them to the output file.
        """
        self.style = self.require_style(self.style, the_map)
        self.match = self.require_match(self.match, the_map)
        self.match.set_svg_type(self.content_types[self.what])
        if self.replacement is not None:
            self.replacement = the_map.get_symbol(self.replacement)

        for p in self.match.iter(the_map.input_svg):
            #TODO: handle multiple and nested transforms.
            pp = p.clone()
            if pp.t == 'path':
                # Paths are easy, since svgfig does most of the work for us
                # Caution: any svg transformations are passed on unchanged
                # (although the style attribute could be used in a sneaky way to override that)
                self.style.apply(pp)
                pp = svgfig.pathtoPath(pp).SVG(the_map.project)
            elif pp.t == 'text':
                # for texts, we have to consider existing transforms
                x, y = float(pp.attr['x']), float(pp.attr['y'])
                m = svg_get_matrix(get_or_default(pp.attr, 'transform', ''))
                x0, y0 = m[0]*x + m[2]*y + m[4], m[1]*x + m[3]*y + m[5]
                x1, y1 = the_map.project(x0, y0)
                m[4] += x1 - x0
                m[5] += y1 - y0
                pp.attr['transform'] = 'matrix({:f},{:f},{:f},{:f},{:f},{:f})'.format(*m)
            elif pp.t == 'g':
                # For markers, the Symbol class together with svg_transform
                # does most of the work of sizing, centering and placing the symbol
                x, y = svg_center(pp)
                x1, y1 = the_map.project(x, y)
                if self.replacement:
                    pp = svg_transform(self.replacement.get_svg(), self.replacement.anchor[0],
                                       self.replacement.anchor[1], x1, y1, self.replacement.scale,
                                       self.replacement.scale)
                else:
                    pp = svg_transform(pp, x, y, x1, y1)
            the_map.add_to_layer(self.target, pp)
        logger.info(u'Project.run: finished mapping: {}'.format(self.what))


class Place(Command):
    """
    Places a set of items on the page. It can add a symbol at each spot, it can connect them with lines and
    it can add text labels. The symbols and markers can be different at each location.

    Place command has the following options:
    mode: this is a list of keywords which control how the drawing is made, as follows:
        [ absolute | relative ] The first point is always given as a pair of geographic coordinates. The
             subsequent points are ether geographical coordinates (absolute, the default) or offsets from the
             reference point (relative) given as distance and angle from due east.
        [ central | sequential ] If central, the reference point is always the first one. If sequential, each point
              drawn becomes the reference for the next one.
    target: target layer
    unit: the unit used for measuring distances. Defaults to no-unit
    line: the name of the line style. If the parameter is missing, no line is drawn.
    symbol: the name of a symbol to be drawn, or a list of different ones to be placed at succeeding locations.
        If the list is shorter than the list of locations, the last symbol is repeated (can be set to empty string)
    label: a dictionary that defines the text to be placed at each point:
        style: defaults to default-text-style
        format: a pythonic format string that uses the values defined by the command, or a list of
            strings that behaves analogously to the symbol
        nudge: an x, y pair in unit coordinates that defines the offset of the text from the point.
            Defaults to [0, 0]
    at: a list of coordinates to be interpreted as defined by mode

    The values available to the format string are:
        unit: unit name
        length: the length of the last segment in units (0 for the first point)
        [x|y]_[deg|min|sec|card]: degrees, minutes, seconds, cardinal direction of longitude or latitude
        count: the sequential number of the point. Starts with 0
    """
    def __init__(self, d):
        Command.__init__(self, d)
        try:
            self.mode = get_or_default(d, 'mode', 'absolute')
            self.unit = get_or_default(d, 'unit', 'no-unit')
            self.line = get_or_default(d, 'line', None)
            if self.line:
                self.line_style = get_or_default(self.line, 'style', 'default-line-style')
            self.symbol = get_or_default(d, 'symbol', None)
            self.label = get_or_default(d, 'label', None)
            if self.label:
                self.label_style = get_or_default(self.label, 'style', 'default-text-style')
                self.fmt = get_or_default(self.label, 'format', 'default-label-format')
                self.nudge = [_*pi/180 for _ in get_or_default(self.label, 'nudge', [0.0, 0.0])]
            self.at = d['at']
            self.points = len(self.at)//2
        except KeyError as ke:
            raise MapperException(MX_MISSING_PARAMETER, 'Place.__init__', str(ke), 'place')
        except ValueError as ve:
            raise MapperException(MX_WRONG_VALUE, 'Marks.__init__', ve.message, 'place')
        if isinstance(self.mode, basestring):
            self.mode = {self.mode}
        else:
            self.mode = set(self.mode)
        logger.info(u'Loaded marks {}'.format(self.symbol))

    def run(self, the_map):
        """
        Draw the lines and place the symbols and the labels.

        Lines are drawn first, followed by symbols and finally text.
        """
        # Start by building a list of absolute positions in world coordinates.
        self.unit = the_map.get_unit(self.unit)
        x, y = self.at[0]*pi/180, self.at[1]*pi/180
        world = [(x, y, 0)]
        for l in pairwise(self.at[2:]):
            try:
                if 'absolute' in self.mode:
                    x1 = l[0]*pi/180
                    y1 = l[1]*pi/180
                    d = self.unit.measure(x, y, x1, y1)
                else:
                    d = l[0]
                    x1, y1 = self.unit.move_to(x, y, l[0], l[1]*pi/180)
            except IndexError:
                raise MapperException(MX_WRONG_VALUE, 'Place.run', 'at array', self.at)
            world.append((x1, y1, d))
            if 'sequential' in self.mode:
                x, y = x1, y1

        # Draw the lines, if any, in world coordinates and project it, so it's curved if it needs to be.
        if self.line:
            self.line_style = self.require_style(self.line_style, the_map)
            x, y, d = world[0]
            for w in world[1:]:
                path = svgfig.Line(x, y, w[0], w[1], **self.line_style.attributes)
                the_map.add_to_layer(self.target, path.SVG(the_map.project_inner))
                if 'sequential' in self.mode:
                    x, y = w[0], w[1]

        # Place the symbols next
        #TODO: handle <defs> in the symbol source file to get blends right. Fairly tricky to do.
        if self.symbol:
            # replace symbol names with objects and make the list of symbols as long as the list of points
            if isinstance(self.symbol, basestring):
                self.symbol = [self.symbol]
            if len(self.symbol) > len(world):
                logger.warn('More symbols than points, discarding extra symbols')
                self.symbol = self.symbol[:len(world)]
            for i, s in enumerate(self.symbol):
                if s == '':
                    self.symbol[i] = None
                else:
                    sym = the_map.get_symbol(s)
                    if sym is None:
                        raise MapperException(MX_UNRESOLVED_REFERENCE, 'Place.run', 'symbol', s)
                    else:
                        self.symbol[i] = the_map.get_symbol(s)
            # place the symbols
            for s, (x, y, d) in izip_longest(self.symbol, world, fillvalue=self.symbol[-1]):
                if s is None:
                    continue
                x, y = the_map.project_inner(x, y)
                svg = svg_transform(s.get_svg(), s.anchor[0], s.anchor[1], x, y, s.scale, s.scale)
                the_map.add_to_layer(self.target, svg)

        # then the labels
        if self.label:
            if isinstance(self.fmt, basestring):
                self.fmt = [self.fmt]
            if len(self.fmt) > len(world):
                logger.warn('More labels than points, discarding extra labels')
                self.fmt = self.fmt[:len(world)]
            for i, s in enumerate(self.fmt):
                self.fmt[i] = the_map.translate_string(s)

            self.label_style = self.require_style(self.label_style, the_map)

            # prepare the list of page coordinates and label strings and place the labels
            strings = {}
            strings.update(the_map.strings)
            for (i, (x, y, d)), f in izip_longest(enumerate(world), self.fmt, fillvalue=self.fmt[-1]):
                strings.update({'length': d, 'unit': self.unit, 'count': i, 'x-pos': x*180/pi, 'y-pos': y*180/pi})
                strings.update(float_to_dms(x, False, the_map, prefix='x-'))
                strings.update(float_to_dms(y, True, the_map, prefix='y-'))
                x, y = the_map.project_inner(x + self.nudge[0], y + self.nudge[1])
                try:
                    txt = f.format(**strings)
                except KeyError as ke:
                    raise MapperException(MX_UNRESOLVED_REFERENCE, 'Project.run', 'label format value', str(ke))
                svg = svgfig.Text(x, y, txt, **self.label_style.attributes).SVG(None)
                the_map.add_to_layer(self.target, svg)

        logger.info(u'Place.run: drew {} points'.format(len(world)))


class Graticules(Command):
    """
    Draw a set of major and minor graticules in the output file. The graticules can be either horizontal or vertical
    (i.e. parallels or meridians) and can be labelled or not. Different styles are applied to major and minor
    graticules and their labels. They are clipped to a rectangle which defaults to the viewport, but this can
    be overridden.
    """

    class OneLine(Command):
        """
        Major and minor graticules are treated similarly. This class encapsulates common functionality.
        """
        def __init__(self, d):
            Command.__init__(self, d, 'default-line-style')
            self.span = d['span']
            self.labels = get_or_default(d, 'labels', None)
            if self.labels:
                self.pos = get_or_default(self.labels, 'position', 'start')
                self.l_style = get_or_default(self.labels, 'style', 'default-text-style')
                self.fmt = get_or_default(self.labels, 'format', 'default-label-format')

        def initialize(self, the_map, s0, s1):
            """ Get the styles and the formats and set the endpoints """
            self.style = self.require_style(self.style, the_map)
            self.s0, self.s1 = s0, s1
            if self.labels:
                self.l_style = self.require_style(self.l_style, the_map)
                self.fmt = the_map.translate_string(self.fmt)
                if self.pos == 'start':
                    self.pos = s0
                elif self.pos == 'end':
                    self.pos = s1
                elif self.pos == 'mid':
                    self.pos = (s1 + s0)/2
                else:
                    raise MapperException(MX_WRONG_VALUE, 'OneLine.initialize', 'position', self.pos)

        def hline(self, t):
            return svgfig.HLine(self.s0, self.s1, t, style=self.style.style())

        def vline(self, t):
            return svgfig.VLine(self.s0, self.s1, t, style=self.style.style())

        def get_label(self, x, y, strings):
            try:
                txt = self.fmt.format(**strings)
            except KeyError as ke:
                raise MapperException(MX_UNRESOLVED_REFERENCE, 'OneLine.run', 'label format value', str(ke))
            return svgfig.SVG('text', txt, x=x, y=y, **self.l_style.attributes)

    def __init__(self, d):
        Command.__init__(self, d)
        try:
            self.horizontal = get_or_default(d, 'direction', 'horizontal') == 'horizontal'
            self.clip = get_or_default(d, 'clip-to', None)
            self.lines = []
            last_span = None
            for div in d['divisions']:
                l = self.OneLine(div)
                self.lines.append(l)
                # Succeeding spans must evenly divide each other
                if last_span and last_span % l.span != 0:
                    raise MapperException(MX_WRONG_VALUE, 'Graticules.__init__', l.span, 'span')
                last_span = l.span
        except KeyError as ke:
            raise MapperException(MX_MISSING_PARAMETER, 'Graticules.__init__', str(ke), 'graticules')
        logger.info(u'Loaded {} graticules'.format('horizontal' if self.horizontal else 'vertical'))

    def run(self, the_map):
        """
        Draws meridians or parallels on the named layer. dt gives the degree separation of major to, subdiv
        gives the number of subdivisions. If r is given, the graticules are clipped this rectangle, otherwise the
        entire viewport is used. Subdiv is assumed to be (and in fact silently coerced to) an integer.
        Labels can be 'none', 'minor', 'major' or 'both'.
        """
        # If the clipping rectangle is not given, default to the viewport.
        if self.clip is None:
            self.clip = the_map.rect_world
        else:
            self.clip = the_map.get_rectangle(self.clip)
        # Set up the clipping values in a way that is neutral with respect to direction
        # t0, t1 are the starting and ending values, s0, s1 are the endpoints of each line
        if self.horizontal:
            t0, t1, s0, s1 = self.clip.y0, self.clip.y1, self.clip.x0*pi/180, self.clip.x1*pi/180
        else:
            t0, t1, s0, s1 = self.clip.x0, self.clip.x1, self.clip.y0*pi/180, self.clip.y1*pi/180

        # Initialize the lines and the format strings
        for l in self.lines:
            l.initialize(the_map, s0, s1)
        strings = {}
        strings.update(the_map.strings)

        # walk over the interval [t0 .. t1] using the smallest subdivision and draw the highest-level line
        # at each division. We use degrees for iteration and convert to radians for drawing
        span = self.lines[-1].span

        for n in xrange(int(ceil(t0/span)), int(floor(t1/span))+1):
            # find the highest level line that is evenly divided into current position
            for l in self.lines:
                if (span * n) % l.span == 0:
                    break
            t = span*n*pi/180
            strings.update({'pos': span*n})
            strings.update(float_to_dms(span*n, self.horizontal, the_map))
            if self.horizontal:
                the_map.add_to_layer(self.target, l.hline(t).SVG(the_map.project_inner))
                if l.labels:
                    x, y = the_map.project_inner(l.pos, t)
                    the_map.add_to_layer(self.target, l.get_label(x, y, strings))
            else:
                the_map.add_to_layer(self.target, l.vline(t).SVG(the_map.project_inner))
                if l.labels:
                    x, y = the_map.project_inner(t, l.pos)
                    the_map.add_to_layer(self.target, l.get_label(x, y, strings))
        logger.info('Graticules.run: drew {} graticules'.format('horizontal' if self.horizontal else 'vertical'))
