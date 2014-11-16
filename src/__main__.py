# encoding: utf-8

# __main__.py, copyright 2014 by Marko Čibej <marko@cibej.org>
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

from main import *


args = parse_args()
set_logging(args.log, args.verbosity)
main(args.config_file, args.resource, args.map, args.simulate)
