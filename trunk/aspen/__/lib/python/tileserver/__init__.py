import logging
import os
import stat

import aspen
if not aspen.CONFIGURED: # for tests
    aspen.configure()
from aspen import ConfigurationError
from aspen.handlers.static import wsgi as static_handler
from aspen.utils import translate


# Logging config
# ==============

if aspen.mode.DEVDEB:
    level = logging.INFO
else:
    level = logging.WARNING
logging.basicConfig(level=level) # Ack! This should be in Aspen. :^(
log = logging.getLogger('pytilemap')


# Configuration
# =============
# Set some things that backends will need.
BUILD_EMPTIES = False
SIZE = 256 # size of (square) tile; NB: changing this will break gmerc calls!
MAX_ZOOM = 31 # this depends on Google API; 0 is furthest out as of recent ver.


# Database
# ========
import psycopg2
try:
    CONN = psycopg2.connect(
        database="test",
        user="postgres",
        password="abc123")
    log.info("connect to database.")
except psycopg2.DatabaseError, e:
    log.error("connect to database error %s" %e)
    CONN = None

# Try to find an image library.
# =============================

# Main WSGI callable 
# ==================

ROOT = aspen.paths.root

def wsgi(environ, start_response):
    path = environ['PATH_INFO']
    fspath = translate(ROOT, path)

    if path.endswith('.png') and 'empties' not in path: 
        # let people hit empties directly if they want; why not?

        # Parse and validate input.
        # =========================
        # URL paths are of the form:
        #
        #   /<mapname>/<maptype>/<zoom>/<x>,<y>.png
        #
        # E.g.:
        #
        #   /crime/classic/3/0,1.png

        raw = path[:-4] # strip extension
        try:
            foo, map_name, map_type, zoom, xy = raw.split('/')
            x, y = xy.split(',')
            zoom = int(zoom)
            x = int(x)
            y = int(y)
        except AssertionError, err:
            log.warn(err.args[0])
            start_response('400 Bad Request', [('CONTENT-TYPE','text/plain')])
            return ['Bad request.']

        # Build and save the file.
        # ========================
        # The tile that is built here will be served by the static handler.
        from base import PostGISTile

        tile = PostGISTile(map_name, map_type, zoom, x, y, fspath)
        if tile.is_outrange():
            log.info('serving empty tile %s' % path)
        elif tile.is_stale():
            log.info('servering cached tile %s' %path)
        elif tile.is_empty():
            log.info('serving empty tile %s' % path)
        else:
            log.info('rebuilding %s' % path)
            tile.rebuild()
            tile.save()


    environ['PATH_TRANSLATED'] = fspath
    return static_handler(environ, start_response)


