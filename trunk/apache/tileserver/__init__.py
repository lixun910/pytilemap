import os

os.environ['PYTHON_EGG_CACHE'] = '/tmp'

# Configuration
# =============
# Set some things that backends will need.

conf = {}

ALWAYS_BUILD = ('true', 'yes', '1')
ALWAYS_BUILD = conf.get('_always_build', '').lower() in ALWAYS_BUILD

BUILD_EMPTIES = ('true', 'yes', '1')
BUILD_EMPTIES = conf.get('_build_empties', 'true').lower() in BUILD_EMPTIES

os.umask(0002)

SIZE = 256 # size of (square) tile; NB: changing this will break gmerc calls!
MAX_ZOOM = 31 # this depends on Google API; 0 is furthest out as of recent ver.

DB = "test"
DB_UNAME = "test"
DB_UPWD  = "test"

ROOT = "/var/www/redmine/public/dist/tmp/dist/pytilemap"
EMPTYTILE = '/'.join([ROOT,'empty.png'])
map_types = ["DELETE","classic","color","LISA","percentile"]

#from PIL import Image
#img = Image.new('RGBA', (256,256), (255,255,255,0))
#img.save(EMPTYTILE,'PNG')

def get_tile(path):
    fspath = ROOT + path

    if path.endswith('.png') and 'empties' not in path and not os.path.exists(fspath): 
        # let people hit empties directly if they want; why not?
        # Parse and validate input.
        # =========================
        # URL paths are of the form:
        #
        #   /<mapname>/<maptype>/<zoom>/<x>,<y>.png
        #
        # E.g.:
        #
        #   /nyctrip/classic/3/0,1.png

        raw = path[:-4] # strip extension
        try:
            #assert raw.count('/') == 4, "%d /'s" % raw.count('/')

            foo, map_name, map_type, zoom, xy = raw.split('/')

            if map_type == "DELETE":
                from shutil import rmtree
                shutil.rmtree('/'.join([ROOT,map_name])) 
                return fspath

            #assert map_type in map_types, ("bad map type: "+ map_type)
            #assert xy.count(',') == 1, "%d /'s" % xy.count(',')

            x, y = xy.split(',')

            #assert zoom.isdigit() and x.isdigit() and y.isdigit(), "not digits"

            zoom = int(zoom)
            x = int(x)
            y = int(y)

            #assert 0 <= zoom <= 30, "bad zoom: %d" % zoom
        except AssertionError, err:
            return str(err)


        # Build and save the file.
        # ========================
        # The tile that is built here will be served by the static handler.

        from tileserver import base as backend
        tile = backend.PostGISTile(map_name, map_type, zoom, x, y, fspath)
        if tile.is_outrange() or tile.is_empty():
            dirname = os.path.dirname(fspath)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            os.symlink(EMPTYTILE,fspath)
        else:
            tile.rebuild()
            tile.save()

    return fspath