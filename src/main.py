# encoding: utf-8

# main.py, copyright 2014 by Marko Čibej <marko@cibej.org>
#
# This file is part of SvgMapper. Full sources and documentation
# are available here: https://github.com/tumbislav/SvgMapper
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#
# Full licence is in the file LICENSE and at http://www.gnu.org/copyleft/gpl.html

__author__ = 'Marko Čibej'


import argparse
from svgmapper import *
from helper import logger


def main(config, resources=None, maps=None, simulate=False):
    logger.info('Starting job')
    with SvgMapper() as mapper:
        mapper.load_config(config, resources)
        if maps:
            mapper.replace_targets(maps)
        if not simulate:
            mapper.run()
    logger.info('Finished')


def parse_args():
    parser = argparse.ArgumentParser(description='Transform maps in SVG format in various ways.')
    parser.add_argument('config_file', help='The name of the configuration file')
    parser.add_argument('-r', '--resource', help='Additional resource file(s)',
                        action='append', metavar='resource_file')
    parser.add_argument('-m', '--map', help='Map(s) to run instead of those listed in config file', metavar='map_name')
    parser.add_argument('-v', '--verbosity', help='Set verbosity: 0=errors only, 1=warnings, 2=info, 3=debug',
                        type=int, choices=range(0, 3), dest='verbosity')
    parser.add_argument('-l', '--log', help='Output to named log file', metavar=('level(0-3)', 'logFile'), nargs=2)
    parser.add_argument('-s', '--simulate', help='Don\'t actually do anything, just parse all the configurations',
                        action='store_true')
    return parser.parse_args()


def set_logging(the_log, verbosity):
    log_levels = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
    logger.setLevel(logging.DEBUG)
    if the_log:
        level = log_levels[int(the_log[0])]
        lf = logging.FileHandler(the_log[1], mode='w')
        lf.setLevel(level)
        lf.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logger.addHandler(lf)
    lc = logging.StreamHandler()
    if verbosity:
        lc.setLevel(log_levels[verbosity])
    else:
        lc.setLevel(log_levels[2])
    logger.addHandler(lc)
