# encoding: utf-8
__author__ = 'Marko Čibej'
from mapper_commands import *
from mapper_resources import *
from mapper_helper import *
import svgfig
from math import pi
import os
import argparse
import traceback
import yaml


class ResourceManager():
    """
    ResourceManager is the base class for two other classes which manage resources, the Map class and the
    SvgMapper itself. It provides functionality for loading, finding and keeping track of resources.
    """

    top_statements = {'import', 'run', 'map'}
    resource_statements = {'style', 'match', 'projection', 'unit', 'strings', 'library'}
    command_statements = {'project', 'place', 'graticules'}
    all_statements = top_statements | resource_statements | command_statements

    def __init__(self, parent, path):
        self.styles = {}
        self.libraries = {}
        self.rectangles = {}
        self.units = {}
        self.projections = {}
        self.matches = {}
        self.strings = {}
        self.imports = []
        self.imported = False
        self.parent = parent
        self.path = path
        self.current_file = None

    def add_resource(self, keyword, definition):
        """
        Add the resource to the appropriate dictionary.
        Throw a MX_NOT_A_RESOURCE exception if anything but the definition of a valid resource is passed.
        """
        if keyword not in self.resource_statements:
            raise MapperException(MX_UNEXPECTED_PARAMETER, 'ResourceManager.add_resource', keyword, 'resources')
        if keyword == 'style':
            o = Style(definition)
            if o.name in self.styles:
                logger.warn(u'Overwriting style {}.'.format(o.name))
            self.styles[o.name] = o
        elif keyword == 'library':
            o = Library(definition, self)
            if o.name in self.libraries:
                logger.warn(u'Overwriting library {}.'.format(o.name))
            self.libraries[o.name] = o
        elif keyword == 'rectangle':
            o = Rectangle(definition)
            if o.name in self.rectangles:
                logger.warn(u'Overwriting rectangle {}.'.format(o.name))
            self.rectangles[o.name] = o
        elif keyword == 'unit':
            o = Unit(definition)
            if o.name in self.units:
                logger.warn(u'Overwriting unit {}.'.format(o.name))
            self.units[o.name] = o
        elif keyword == 'projection':
            o = Projection(definition)
            if o.name in self.projections:
                logger.warn(u'Overwriting projection {}.'.format(o.name))
            self.projections[o.name] = o
        elif keyword == 'match':
            o = Match(definition)
            if o.name in self.matches:
                logger.warn(u'Overwriting match {}.'.format(o.name))
            self.matches[o.name] = o
        elif keyword == 'strings':
            self.strings.update(definition)
            self.preprocess_strings()
        else:
            raise MapperException(MX_UNEXPECTED, 'ResourceManager.add_resource', 'unknown statement', keyword)
        return self

    def load(self, filename, path=None, the_filter=None):
        """
        Recursively load a configuration file. Run any import statements as soon as they are encountered and
        return a list of dictionaries that can be instantiated as objects.

        :param filename: the name of the input file, possibly with a path component
        :param path: the path inherited from the outer scope
        :param the_filter: a dictionary of items that are to be loaded or None to load them all.
        :return: list of dicts that can be instantiated as resources, commands and maps
        """

        # Make sure we've actually got a file to read and figure out where we are in the filesystem
        if path is None:
            path = self.path
        fullpath = os.path.join(path, filename)
        localpath = os.path.dirname(fullpath)
        if not os.path.isfile(fullpath):
            fullpath += '.svgmap'
        if not os.path.isfile(fullpath):
            raise MapperException(MX_CONFIG_ERROR, 'ResourceManager.load', fullpath, 'file not found')
        self.current_file = fullpath

        # Get the file contents and run them through yaml
        s = None
        with open(fullpath) as f:
            try:
                s = yaml.load(f)
            except yaml.YAMLError as ye:
                raise MapperException(MX_CONFIG_ERROR, 'ResourceManager.load', fullpath, ye)
            if not isinstance(s, list):
                raise MapperException(MX_CONFIG_ERROR, 'ResourceManager.load', self.current_file,
                                      'file is not a list of statements')

        # Walk through the parsed list and take care of peculiarities
        loaded = []
        for keyword, definition in inner_pairs(s):
            if not keyword in self.all_statements:
                raise MapperException(MX_CONFIG_ERROR, 'ResourceManager.load', self.current_file,
                                      'unknown statement "{}"'.format(unicode(keyword)))
            if keyword == 'import':
                # An import statement is processed immediately and its result appended to the statement list
                loaded += self.load_import(definition, localpath)
            elif keyword == 'map':
                # A map can have local resources and local imports that can load resources and also commands
                loaded.append({'map': self.load_map(definition, localpath)})
            else:
                if the_filter is not None:
                    # Skip anonymous and unlisted statements if we have a filter
                    if not 'name' in definition or not definition['name'] in the_filter:
                        continue
                    # Rename those that pass the filter
                    definition['name'] = the_filter[definition['name']]
                if isinstance(definition, dict):
                    # Tag the objects with local path if they need it
                    definition['path'] = localpath
                loaded.append({keyword: definition})
        return loaded

    def load_import(self, definition, path):
        """
        Handles an import statement while loading a config file.
        """
        if isinstance(definition, basestring):
            return self.load(definition, path, the_filter=None)
        else:
            if not ('from' in definition and 'elements' in definition):
                raise MapperException(MX_CONFIG_ERROR, 'ResourceManager.load_import', self.current_file,
                                      u'cannot understand import statement {}'.format(unicode(definition)))
            return self.load(definition['from'], path, the_filter=definition['elements'])

    def load_map(self, definition, path):
        """
        Handles a map statement while loading a config file. Its 'do' section can contain import statements,
        which can add more resources and commands.
        """
        if not 'do' in definition:
            raise MapperException(MX_CONFIG_ERROR, 'ResourceManager.load_map',
                                  self.current_file, 'map "{}" should have a "do" section'.format(definition['name']))
        # we copy the results to a new list to keep things simple
        loaded = []
        for k, d in inner_pairs(definition['do']):
            if k == 'import':
                # Run the import, then put all our toys in the right boxes
                for k1, d1 in inner_pairs(self.load_import(d, path)):
                    if k1 in (self.command_statements | self.resource_statements):
                        loaded.append({k1: d1})
                    else:
                        raise MapperException(MX_CONFIG_ERROR, 'ResourceManager.load_map',
                                              self.current_file, '"{}" is not understood'.format(unicode(k1)))
            else:
                loaded.append({k: d})
        definition['do'] = loaded
        return definition

    def preprocess_strings(self):
        """ Takes care of special rules for strings. """
        if 'cardinal-directions' in self.strings:
            s = self.strings['cardinal-directions']
            try:
                if isinstance(s, list):
                    self.strings['cardinal-north'] = s[0]
                    self.strings['cardinal-east'] = s[1]
                    self.strings['cardinal-south'] = s[2]
                    self.strings['cardinal-west'] = s[3]
                    del self.strings['cardinal-directions']
            except:
                raise MapperException(MX_WRONG_VALUE, 'ResourceManager.preprocess_strings', 'cardinal-directions', s)

    def get_style(self, d):
        """ Find or construct the requested style. The input parameter must be either the style's name,
        or a json dictionary defining it. If the style is not found, return None and let caller handle it. """
        if isinstance(d, Style):
            # Should be idempotent
            return d
        elif isinstance(d, dict):
            return Style(d)
        elif isinstance(d, basestring):
            if d in self.styles:
                return self.styles[d]
            elif self.parent is not None:
                return self.parent.get_style(d)
            else:
                return None

    def get_match(self, d):
        """
        Find or construct the named Match object. Unlike get_style, this always returns a valid Match
        object: if nothing is found, it constructs a match that looks for id=d. Note that this happens
        at the top of the recursion stack, not the bottom.
        """
        if isinstance(d, Match):
            return d
        elif isinstance(d, dict):
            return Match(d)
        elif isinstance(d, basestring):
            if d in self.matches:
                return self.matches[d]
            elif self.parent is not None:
                return self.parent.get_match(d)
            else:
                return Match(d)

    def get_projection(self, d):
        """ Find the named projection or construct it from the given dictionary. """
        if isinstance(d, Projection):
            return d
        elif isinstance(d, dict):
            return Projection(d)
        if isinstance(d, basestring):
            if d in self.projections:
                return self.projections[d]
            elif self.parent is not None:
                return self.parent.get_projection(d)
            else:
                return None

    def get_unit(self, d):
        """ Find the named unit or return None. """
        if isinstance(d, Unit):
            return d
        if d in self.units:
            return self.units[d]
        elif self.parent is not None:
            return self.parent.get_unit(d)
        else:
            return None

    def get_rectangle(self, d):
        """ Find the named unit or construct it from the given dictionary. If not found, return None. """
        if isinstance(d, basestring):
            if d in self.rectangles:
                return self.rectangles[d]
            elif self.parent is not None:
                return self.parent.get_rectangle(d)
            else:
                logger.warn(u'Rectangle {} not found.'.format(d))
                return None
        else:
            return Rectangle(d)

    def get_symbol(self, d):
        """ Find the named symbol in the named library or return None. """
        if isinstance(d, Symbol):
            return d
        lib_name, sym_name = d.split('::')
        lib = self.get_library(lib_name)
        if lib is None:
            return None
        return lib.get_symbol(sym_name)

    def get_library(self, d):
        """ Find the named library or return None. """
        if isinstance(d, Library):
            return d
        if d in self.libraries:
            return self.libraries[d]
        elif self.parent is not None:
            return self.parent.get_library(d)
        else:
            return None

    def get_string(self, d):
        """ Find the named resource string or return None. """
        if d in self.strings:
            return self.strings[d]
        elif self.parent is not None:
            return self.parent.get_string(d)
        else:
            return None

    def translate_string(self, d):
        """ Replace the incoming string with a string resource, if it exists. If not, return the same value. """
        s = self.get_string(d)
        return d if s is None else s


class SvgMapper(ResourceManager):
    """ Main class that drives the execution. It reads the input configuration file and runs the maps. """

    def __init__(self):
        ResourceManager.__init__(self, None, os.getcwd())
        self.run_list = []
        self.maps = {}
        self.active_config = None
        logger.info(u'SvgMapper.__init__: created mapper')

    def __enter__(self):
        """ Support the with keyword. """
        return self

    def __exit__(self, exception_type, value, trace):
        """ Log the exception and return. """
        if exception_type is not None:
            if isinstance(value, MapperException):
                logger.error(value)
#                logger.error(u'{}: {}'.format(value, traceback.print_tb(trace)))
                return True
            else:
                return False

    def load_config(self, filename, add_resource=None):
        """ Build a list of dictionaries with resource definitions, then instantiate all the objects. """
        # First, load the main config file.
        path, filename = os.path.split(filename)
        self.path = os.path.join(os.getcwd(), path)
        try:
            statements = self.load(filename)
        except ValueError as ve:
            raise MapperException(MX_CONFIG_ERROR, 'SvgMapper.load_config',
                                  self.current_file, u'cannot parse {}'.format(ve))
        # then append any additional resource files
        if add_resource:
            for fn in add_resource:
                statements.append(self.load(fn))
        # finally, instantiate everything
        self.instantiate(statements)

    def instantiate(self, statements):
        """
        Instantiate all the statements defined in the input and map them.
        :param statements: the list of statements
        """
        for keyword, definition in inner_pairs(statements):
            if keyword == 'run':
                if isinstance(definition, basestring):
                    if not definition in self.run_list:
                        self.run_list.append(definition)
                else:
                    for t in definition:
                        if t not in self.run_list:
                            self.run_list.append(t)
            elif keyword == 'map':
                # A map instantiates itself on run
                m = Map(definition, self)
                if m in self.maps:
                    logger.warn(u'Overwriting map {}.'.format(m))
                self.maps[m.name] = m
            elif keyword in self.resource_statements:
                self.add_resource(keyword, definition)
            else:
                raise MapperException(MX_UNEXPECTED_PARAMETER, 'SvgMapper.instantiate', keyword, 'main')

    def replace_targets(self, lst):
        self.run_list = lst

    def run(self, the_map=None):
        if the_map is None:
            for m in self.run_list:
                self.maps[m].run()
        elif the_map in self.maps:
            self.maps[the_map].run()
        else:
            raise MapperException(MX_UNRESOLVED_REFERENCE, 'SvgMapper.run', 'map', the_map)


class Map(ResourceManager):
    def __init__(self, d, parent):
        """
        Store the input dict, but leave the real initialization for when the map is called.
        """
        ResourceManager.__init__(self, parent, parent.path)
        self.commands = []
        self.layers_out = {}
        self.input_svg = self.output_svg = None
        self.rect_world = None
        self.dx_in = self.dy_in = self.x0_in = self.y0_in = None
        self.dx_out = self.dy_out = self.x0_out = self.y0_out = None
        try:
            self.name = d['name']
        except KeyError as ke:
            raise MapperException(MX_MISSING_PARAMETER, 'Map.__init__', str(ke), 'map')
        self.d = d
        logger.info(u'Loaded map `{}`'.format(self.name))

    def initialize(self):
        """
        Initialize the map before running it. This must be done in the right sequence:
        - prepare the output file
        """
        try:
            # first, instantiate the resources and the commands
            self.instantiate(self.d)
            # get the projection
            proj = get_or_default(self.d, 'projection', 'default-projection')
            self.projection = self.resolve_projection(proj)
            if self.projection is None:
                raise MapperException(MX_UNRESOLVED_REFERENCE, 'Map.init_output', 'projection', proj)
            # then load the input file
            filename = os.path.join(self.path, self.d['file-in'])
            self.input_svg = svgfig.load(filename)
            # get the in, out and world rectangle, then initialize the projection and finally set the
            # in and out scaling function
            self.set_scale(self.d['scale'])
            # and then prepare the output file
            self.file_out = os.path.join(self.path, self.d['file-out'])
            self.init_output(get_or_default(self.d, 'append', False))
        except KeyError as ke:
            raise MapperException(MX_MISSING_PARAMETER, 'Map.initialize', str(ke), 'map')

    def instantiate(self, d):
        """ Instantiate resources and commands and map them. """
        for keyword, definition in inner_pairs(d['do']):
            if keyword in self.resource_statements:
                self.add_resource(keyword, definition)
            elif keyword in self.command_statements:
                if keyword == 'project':
                    self.commands.append(Project(definition))
                if keyword == 'place':
                    self.commands.append(Place(definition))
                if keyword == 'graticules':
                    self.commands.append(Graticules(definition))
            else:
                raise MapperException(MX_UNEXPECTED_PARAMETER,
                                      'Map.instantiate', name=keyword, value='command/resource')
        # final trick, merge the parents' strings with ours to get a definitive local copy
        s = copy.deepcopy(self.parent.strings)
        s.update(self.strings)
        self.strings = s

    def set_scale(self, d):
        """
        Get the in, world and out rectangles and define mapping scale.

        Scale transformation is defined as:
            scale rect_in to rect_world. flip y coordinate while you're at it and scale from degrees to radians
            apply projection
            scale to rect_world and flip the y coordinate again.
        Projection output size is not normalized, output scale is determined by projecting the corners of the world
        rectangle and scaling them to the output rectangle.
        """
        # Preferably, read the in_rect from the scaling object, so start by checking if one is defined
        mtc = scaler = None
        if isinstance(d, basestring):
            mtc = self.get_match(d)
            align = [0, 0, 1, 1]
        else:
            align = get_or_default(d, 'align', [0, 0, 1, 1])
            if 'match' in d:
                mtc = self.get_match(d['match'])
        if mtc:
            try:
                scaler = mtc.iter(self.input_svg).next()
            except:
                raise MapperException(MX_MISSING_SVG, 'Map.initialize', d['match'], 'input file')

        # Now we can get the input rectangle from one of the two sources
        if scaler:
            rect_in = Rectangle().bounding_box_svg(scaler)
        else:
            rect_in = self.get_rectangle(d['rect-in'])
        rect_in.orient(True)

        # World rectangle is next: either read it from the scaler or from config. Then initialize the projection.
        if scaler and 'lon-min' in scaler.attr:
            self.rect_world = Rectangle(scaler)
        else:
            self.rect_world = self.get_rectangle(d['rect-world'])
        self.rect_world.orient()
        self.projection.initialize(self)

        # Finally the output rectangle. Here, config takes preference, otherwise copy the input
        if 'rect-out' in d:
            rect_out = Rectangle(d['rect-out'])
        else:
            rect_out = Rectangle(rect_in)
        rect_out.orient(True)

        # finally, set the in and out scale. A simple linear transform, but we have to do it in radians.
        dx_in = (self.rect_world.x1 - self.rect_world.x0)*pi/(rect_in.x1 - rect_in.x0)/180
        dy_in = (self.rect_world.y1 - self.rect_world.y0)*pi/(rect_in.y1 - rect_in.y0)/180
        x0_in = self.rect_world.x0*pi/180 - rect_in.x0*dx_in
        y0_in = self.rect_world.y0*pi/180 - rect_in.y0*dy_in
        self.scale_in = lambda x, y: (x*dx_in + x0_in, y*dy_in + y0_in)

        xref = self.rect_world.x0*(1 - align[0]) + self.rect_world.x1*align[0]
        yref = self.rect_world.y0*(1 - align[1]) + self.rect_world.y1*align[1]
        x_out0 = self.projection.project(self.rect_world.x0*pi/180, yref*pi/180)[0]
        y_out0 = self.projection.project(xref*pi/180, self.rect_world.y0*pi/180)[1]
        xref = self.rect_world.x0*(1 - align[2]) + self.rect_world.x1*align[2]
        yref = self.rect_world.y0*(1 - align[3]) + self.rect_world.y1*align[3]
        x_out1 = self.projection.project(self.rect_world.x1*pi/180, yref*pi/180)[0]
        y_out1 = self.projection.project(xref*pi/180, self.rect_world.y1*pi/180)[1]

        dx_out = (rect_out.x1 - rect_out.x0)/(x_out1 - x_out0)
        dy_out = (rect_out.y1 - rect_out.y0)/(y_out1 - y_out0)
        x0_out = rect_out.x0 - x_out0*dx_out
        y0_out = rect_out.y0 - y_out0*dy_out
        self.scale_out = lambda x, y: (x*dx_out + x0_out, y*dy_out + y0_out)

    def init_output(self, append):
        """
        Either create a new blank output file that is a copy of the input stripped of content,
        or load an existing one and index it.
        """
        if append:
            self.output_svg = svgfig.load(self.file_out)
            for k, s in self.input_svg:
                if isinstance(s, svgfig.SVG) and s.t == 'g' and 'inkscape:groupmode' in s.attr:
                    self.layers_out[s.attr['inkscape:label']] = s
        else:
            # Clone the header part of the input by iterating over all top-level members that are not groups.
            self.output_svg = svgfig.SVG('svg')
            self.output_svg.attr = copy.deepcopy(self.input_svg.attr)
            for k, s in self.input_svg.depth_first(1):
                if isinstance(s, svgfig.SVG) and s.t not in ['g', 'path']:
                    self.output_svg.append(s.clone())

    def run(self):
        self.initialize()
        for c in self.commands:
            c.run(self)
        self.output_svg.save(self.file_out)

    def project_inner(self, x, y):
        """ Project from world coordinates expressed in radians to page coordinates """
        x, y = self.projection.project(x, y)
        return self.scale_out(x, y)

    def project(self, x, y):
        x, y = self.scale_in(x, y)
        x, y = self.projection.project(x, y)
        return self.scale_out(x, y)

    def resolve_projection(self, p):
        """
        Locate the projection by name. If not found, assume the name is a projection class
        and try to create it from scratch. Finally, initialize it.
        """
        if isinstance(p, basestring):
            p = self.translate_string(p)
            pt = self.get_projection(p)
            if pt is None:
                return Projection({'class': p})
            else:
                return pt
        else:
            return self.get_projection(p)

    def get_output_layer(self, name):
        """ Either finds or creates a layer with the given name. """
        if name in self.layers_out:
            g = self.layers_out[name]
        else:
            g = svgfig.SVG('g', style="display:inline", inkscape__label=name, id=name, inkscape__groupmode='layer')
            self.output_svg.append(g)
            self.layers_out[name] = g
        return g

    def add_to_layer(self, layer, svg_object):
        """ Append an svg object to a named layer. """
        g = self.get_output_layer(layer)
        g.append(svg_object)
        return g


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Transform maps in SVG format in various ways.')
    parser.add_argument('config_file', help='The name of the json file which specifies the configuration')
    parser.add_argument('-r', '--resource', help='Additional resource file(s)',
                        action='append', metavar='resource_file')
    maps = parser.add_mutually_exclusive_group()
    maps.add_argument('-m', '--map', help='Map(s) to run instead of those listed in config file', metavar='map_name')
    maps.add_argument('-v', '--verbosity', help='Set verbosity: 0=errors only, 1=warnings, 2=info, 3=debug',
                      type=int, choices=range(0, 3), dest='verbosity')
    parser.add_argument('-l', '--log', help='Output to named log file', metavar=('level(0-3)', 'logFile'), nargs=2)
    parser.add_argument('-s', '--simulate', help='Don\'t actually do anything, just parse all the configurations',
                        action='store_true')
    args = parser.parse_args()

    log_levels = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
    logger.setLevel(logging.DEBUG)
    if args.log:
        level = log_levels[int(args.log[0])]
        lf = logging.FileHandler(args.log[1], mode='w')
        lf.setLevel(level)
        lf.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logger.addHandler(lf)
    lc = logging.StreamHandler()
    if args.verbosity:
        lc.setLevel(log_levels[args.verbosity])
    else:
        lc.setLevel(log_levels[2])
    logger.addHandler(lc)

    logger.info('Starting job')
    with SvgMapper() as mapper:
        mapper.load_config(args.config_file, add_resource=args.resource)
        if args.map:
            mapper.replace_targets(args.map)
        if not args.simulate:
            mapper.run()
    logger.info('Finished')
else:
    logger = logging.getLogger('SvgMapper')
