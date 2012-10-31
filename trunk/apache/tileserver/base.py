import os

from tileserver.ShapeObjectInterface import PostgreShapeObject
import gmerc
from tileserver import BUILD_EMPTIES, SIZE, DB, DB_UNAME, DB_UPWD
from PIL import Image, ImageDraw

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
        self.mapType= map_type
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


class PostGISTile(Tile):

    def __init__(self, mapname, map_type,  zoom, x, y, fspath):
        Tile.__init__(self,mapname, map_type, zoom, x, y, fspath)

        self.postgis  = PostgreShapeObject(DB,mapname,DB_UNAME,DB_UPWD)
        self.shapeObjects = []
        self.shapeType    = ""
        self.colorScheme  = {}

    def is_outrange(self):
        shapeExtent  = self.postgis.getExtent()

        if shapeExtent[0] > self.e or\
           shapeExtent[2] < self.w or\
           shapeExtent[1] > self.n or\
           shapeExtent[3] < self.s:

            return True

        return False

    def is_empty(self):
        """With attributes set on self, return a boolean.

        Calc lat/lng bounds of this tile (include half-dot-width of padding)
        SELECT count(uid) FROM points

        """
        self.shapeType    = self.postgis.getShapeType()

        tileBound    = (self.w,self.s,self.e,self.n)
        tileRegion   = ((self.w,self.s), (self.e,self.s),
                        (self.e,self.n), (self.w,self.n),(self.w,self.s))

        if self.mapType.startswith("color"):
            colorColumn = "color"
            parameters  = self.mapType.split(",")
            if len(parameters) > 1:
                colorColumn = parameters[1]
            self.shapeObjects,self.colorScheme = \
                self.postgis.getShapeObjectsByRegionWithColor(tileRegion,colorColumn)
        else: 
            self.shapeObjects = self.postgis.getShapeObjectsByRegion(tileRegion)

        #disconnect database connection here
        #todo: this should be ignored in "static" 
        #db handler
        del self.postgis

        return len(self.shapeObjects) == 0

    def rebuild(self):
        self.img = self.hook_rebuild()

        dirpath = os.path.dirname(self.fspath)
        if dirpath and not os.path.isdir(dirpath):
            os.makedirs(dirpath, 0755)

    def hook_rebuild(self):
        self.img  = Image.new('RGBA', (SIZE,SIZE), (255,255,255,0))
        draw = ImageDraw.Draw(self.img)

        if len(self.colorScheme) > 0:
            colors = self.colorScheme.keys()
            for color in colors:
                objIDs = self.colorScheme[color]
                if self.shapeType == "POINT":
                    for i in objIDs:
                        x,y = self.shapeObjects[i]
                        x, y = gmerc.ll2px(y,x, self.zoom)
                        x = x - self.x1 # account for tile offset relative to 
                        y = y - self.y1 #  overall map
                        draw.ellipse( (x-2,y-2,x+2,y+2), fill=color,outline="black") 
                    elif self.shapeType == "MULTIPOLYGON":
                        for i in objIDs:
                            poly = self.shapeObjects[i]
                            _poly = []
                            for pt in poly:
                                x, y = gmerc.ll2px(pt[1],pt[0], self.zoom)
                                x = x - self.x1 # account for tile offset relative to 
                                y = y - self.y1 #  overall map
                                _poly.append((x,y))
                            draw.polygon(_poly, outline="black", fill=color)
            return self.img

        # without color scheme	
        if self.shapeType == "POINT":
            for x,y in self.shapeObjects:
                x, y = gmerc.ll2px(y,x, self.zoom)
                x = x - self.x1 # account for tile offset relative to 
                y = y - self.y1 #  overall map
                draw.ellipse( (x-2,y-2,x+2,y+2), fill="red",outline="black") 

        elif self.shapeType == "MULTIPOLYGON":
            for poly in self.shapeObjects:
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

