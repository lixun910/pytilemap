import datetime
import os
import stat

import tileserver
import tileserver.opacity
import gmerc
from tileserver import BUILD_EMPTIES, SIZE
from PIL import Image, ImageDraw, ImageChops
import pysal


class EmptyTile(object):
    
    def __init__(self, name, fspath):
        """Takes the name and filesystem path of the defining PNG.
        """
        self.empties_dir = os.path.join("/var/cache/pytilemap", name, 'empties')
        self.build_empties()
        self.hook_set(fspath)
        
    def hook_set(self, fspath):
        self.colors = Image.open(fspath).load()


    def build_empties(self):
        """Build empty tiles for this color scheme.
        """
        empties_dir = self.empties_dir

        if not BUILD_EMPTIES:
            pass
            #log.info("not building empty tiles for %s" % name)
        else:    
            if not os.path.isdir(empties_dir):
                os.makedirs(empties_dir)
            if not os.access(empties_dir, os.R_OK|os.W_OK|os.X_OK):
                raise ConfigurationError( "Permissions too restrictive on "
                                        + "empties directory "
                                        + "(%s)." % empties_dir
                                         )
            for zoom, opacity in tileserver.opacity.zoom_to_opacity.items():
                fspath = os.path.join(empties_dir, str(zoom)+'.png')
                if not os.path.exists(fspath):
                    self.hook_build_empty(opacity, fspath)
            
            #log.info("building empty tiles in %s" % empties_dir)


    def get_empty_fspath(self, zoom):
        fspath = os.path.join(self.empties_dir, str(zoom)+'.png')
        if not os.path.isfile(fspath):
            self.build_empties() # so we can rebuild empties on the fly
        return fspath
    
    def hook_build_empty(self, opacity, fspath):
        color = self.colors[0, 255]
        if len(color) == 4: # color map has per-pixel alpha
            (conf, pixel) = opacity, color[3] 
            opacity = int(( (conf/255.0)    # from configuration
                          * (pixel/255.0)   # from per-pixel alpha
                           ) * 255)
        color = color[:3] + (opacity,)
        tile = Image.new('RGBA', (SIZE, SIZE), color)
        tile.save(fspath, 'PNG')


class Tile(object):
    """Base class for tile representations.
    """

    img = None

    def __init__(self, mapname, map_type,  zoom, x, y, fspath):
        """x and y are tile coords per Google Maps.
        """

        # Translate tile to pixel coords.
        # -------------------------------

        x1 = x * SIZE
        x2 = x1 + 255
        y1 = y * SIZE
        y2 = y1 + 255
    
    
        # Expand bounds by one-half dot width.
        # ------------------------------------
        """
        x1 = x1 - dot.half_size
        x2 = x2 + dot.half_size
        y1 = y1 - dot.half_size
        y2 = y2 + dot.half_size
        """
        expanded_size = (x2-x1, y2-y1)
    
    
        # Translate new pixel bounds to lat/lng.
        # --------------------------------------
    
        n, w = gmerc.px2ll(x1, y1, zoom)
        s, e = gmerc.px2ll(x2, y2, zoom)
        self.w,self.s,self.e,self.n = w,s,e,n

        # Save
        # ====

        self.x = x
        self.y = y

        self.x1 = x1
        self.y1 = y1

        self.x2 = x2
        self.y2 = y2

        self.expanded_size = expanded_size
        self.llbound = (n,s,e,w)
        self.zoom = zoom
        self.fspath = fspath
        self.opacity = tileserver.opacity.zoom_to_opacity[zoom]
        self.map_type= map_type
        self.mapname = mapname
  

    def is_empty(self):
        """With attributes set on self, return a boolean.

        Calc lat/lng bounds of this tile (include half-dot-width of padding)
        SELECT count(uid) FROM points

        """
        """
        db = gheat.get_cursor()
        query = {"mapname":self.mapname,
                           "lat":{"$lte":self.llbound[0],"$gte":self.llbound[1]},
                           "lng":{"$lte":self.llbound[2],"$gte":self.llbound[3]}}
        numpoints = db.find(query).count()
        return numpoints == 0
        """
        return False


    def rebuild(self):
        """Rebuild the image at self.img. Real work delegated to subclasses.
        """

        # Calculate points.
        # =================
        # Build a closure that gives us the x,y pixel coords of the points
        # to be included on this tile, relative to the top-left of the tile.

        db = gheat.get_cursor()
        query = {"mapname":self.mapname,
                           "lat":{"$lte":self.llbound[0],"$gte":self.llbound[1]},
                           "lng":{"$lte":self.llbound[2],"$gte":self.llbound[3]}}
        _points = db.find(query)
        def points():
            """Yield x,y pixel coords within this tile, top-left of dot.
            """
            for point in _points:
                x, y = gmerc.ll2px(point['lat'], point['lng'], self.zoom)
                x = x - self.x1 # account for tile offset relative to 
                y = y - self.y1 #  overall map
                yield x-self.pad,y-self.pad


        # Main logic
        # ==========
        # Hand off to the subclass to actually build the image, then come back 
        # here to maybe create a directory before handing back to the backend
        # to actually write to disk.

        self.img = self.hook_rebuild(points())

        dirpath = os.path.dirname(self.fspath)
        if dirpath and not os.path.isdir(dirpath):
            os.makedirs(dirpath)


    def hook_rebuild(self, points, opacity):
        """Rebuild and save the file using the current library.

        The algorithm runs something like this:

            o start a tile canvas/image that is a dots-worth oversized
            o loop through points and multiply dots on the tile
            o trim back down to straight tile size
            o invert/colorize the image
            o make it transparent

        Return the img object; it will be sent back to hook_save after a
        directory is made if needed.

        Trim after looping because we multiply is the only step that needs the
        extra information.

        The coloring and inverting can happen in the same pixel manipulation 
        because you can invert colors.png. That is a 1px by 256px PNG that maps
        grayscale values to color values. You can customize that file to change
        the coloration.

        """
        raise NotImplementedError


    def save(self):
        """Write the image at self.img to disk.
        """
        raise NotImplementedError


class ShapeTile(Tile):

    def rebuild(self):
        self.mapname
        # read objects, shp type from mapname
        f = pysal.open('/Users/xunli/data/%s.shp'%self.mapname)
        shp_type    = f.type
        shp_objects = f.read()
        
        # query objects in tile extent
        locator = None
        bound   = pysal.cg.Rectangle(self.w,self.s,self.e,self.n)
        
        if shp_type == pysal.cg.Point:
            locator = pysal.cg.PointLocator(shp_objects)
        elif shp_type == pysal.cg.Polygon:
            locator = pysal.cg.PolygonLocator(shp_objects)
        
        query_objects = locator.overlapping(bound)
       
        self.img = self.hook_rebuild(query_objects, shp_type)
        
        dirpath = os.path.dirname(self.fspath)
        if dirpath and not os.path.isdir(dirpath):
            os.makedirs(dirpath, 0755)
    
    def hook_rebuild(self, shp_objects, shp_type):
        self.img  = Image.new('RGBA', (SIZE,SIZE), (255,255,255,0))
        draw = ImageDraw.Draw(self.img)

        if shp_type == pysal.cg.Point:
            for x,y in shp_objects:
                x, y = gmerc.ll2px(y,x, self.zoom)
                x = x - self.x1 # account for tile offset relative to 
                y = y - self.y1 #  overall map
                draw.ellipse( (x-2,y-2,x+2,y+2), fill="red",outline="black") 

        elif shp_type == pysal.cg.Polygon:
            for obj in shp_objects:
                for poly in obj.parts:
                    _poly = []
                    for pt in poly:
                        x, y = gmerc.ll2px(pt[1],pt[0], self.zoom)
                        x = x - self.x1 # account for tile offset relative to 
                        y = y - self.y1 #  overall map
                        _poly.append((x,y))
                    draw.polygon(_poly, outline="black", fill="blue")
                    
        return self.img
    
    def save(self):
        self.img.save(self.fspath, 'PNG')