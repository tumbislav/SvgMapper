#SvgMapper

> SVG from Aitoff to Winkel, with style


## What is SvgMapper?
SvgMapper is a Python tool that will, in a nutshell, take a map in SVG format, apply any one of a dozen cartographic 
projections and create an output SVG. Additionally, you can tell it to add stuff to your map, change its style, 
draw graticules, add symbols and so on.

##Contributing to SvgMapper
There are many areas that need work, not all in code development. While Python developers certainly have their work
cut out for them, there are many things that need doing that require no coding skills at all. Style libraries need to 
be written, symbol sets are needed, documentation needs work, there is a lot of testing to be done, etc. Most 
importantly SvgMapper needs users: send me links to your work and I'll add them to the 
[gallery](https://github.com/tumbislav/SvgMapper/wiki/Samples-and-tests#gallery).
 
You can find a list of planned development areas [here]((https://github.com/tumbislav/SvgMapper/wiki/Roadmap).

###Commit policy
At the time of this writing, there are no branches in this repository, since there is only a single developer. If you
are interested in contributing, let me know.

##Using SvgMapper 
###Installing
SvgMapper is written in Python 2.7 and it needs that version or a later one to run. It may run with version 2.6,
although that has not been tested, but it will certainly not run with an earlier one. It also will not run
with any version from the 3.x branch. A port to 3.x is planned for a future date.

Besides the standard Python library, SvgMapper needs [PyYaml](http://pyyaml.org/) to work. Most reasonably recent 
versions will do, since we don't need any advanced functionality. In addition, if you wish to use the Robinson 
projection, [SciPy](http://www.scipy.org/) is highly recommended. See 
[projections]((https://github.com/tumbislav/SvgMapper/wiki/Projections) for details.

SvgMapper uses a modified version of [SvgFig](http://code.google.com/p/svgfig/), developed by Jim Pivarski for basic 
SVG file handling and, most importantly, as a path transformation engine. Since Jim's version had to be modified for 
SvgMapper, it has been renamed and packaged with SvgMapper, so you can use SvgFig in the same environment 
without collision.

###Running SvgMapper

See the [wiki](https://github.com/tumbislav/SvgMapper/wiki/Running) for help.

