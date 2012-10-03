"""
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename='/tmp/myapp.log',
                    filemode='w')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.INFO)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)
"""


class ShapeObjectInterface():
    def __init__(self):
        pass
    
    def __len__(self):
        pass
    
    def __del__(self):
        pass
    
    def getName(self):
        pass
   
    def getExtent(self):
        pass
    
    def getShapeType(self):
        pass
    
    def getShapeObjects(self):
        pass
    
    def getCentroids(self):
        pass
    
    def getLocator(self):
        """?"""
        pass
    
    def getAllData(self):
        pass
    
    def getDataByRow(self, ridx):
        pass
    
    def getDataByColumn(self, cidx):
        pass
    
    def getColumnIndex(self, colname):
        pass
    
    def getFieldSpec(self):
        pass
   
import psycopg2,sys
    
class PostgreShapeObject(ShapeObjectInterface):
    
    def __init__(self, database, tablename, uname, upwd):
        self.database  = database
        self.tablename = tablename
        self.uname     = uname
        self.upwd      = upwd
        self.conn      = None
        self.shapeType = None 
        self.extent    = None
        self.n         = 0
        self.shapeObjects  = []
        self.screenObjects = []
        
        self.conn = None #self._connect(self.uname, self.upwd)

    def _connect(self, uname, upwd):
        try:
            conn = psycopg2.connect(
                database=self.database,
                user=self.uname,
                password=self.upwd)
            #logging.info("connect to database by %s" %self)
        except psycopg2.DatabaseError, e:
            print 'Error %s' % e    
            #logging.error("Error: connect to database %s, by %s" % (e,self))
            return None
        return conn
    
    def __del__(self):
        if self.conn:
            #logging.info("disconnect to database by %s" % self)
            self.conn.close()
            
    def getName(self):
        return self.tablename
    
    def getExtent(self):
        if self.extent:
            return self.extent
        try:
            if not self.conn:
                self.conn = self._connect(self.uname, self.upwd)

            cur = self.conn.cursor()
            cur.execute("SELECT st_extent(the_geom) FROM %s" % self.tablename)
            result = cur.fetchone()[0]
            
            extent = []
            pos1 = result.find(' ')
            pos2 = result.find(',')
            pos3 = result.rfind(' ')
            pos4 = result.find(')')
            extent.append(float(result[4:pos1]))
            extent.append(float(result[pos1+1:pos2]))
            extent.append(float(result[pos2+1:pos3]))
            extent.append(float(result[pos3+1:pos4]))
            
            self.extent = extent
            return extent
        except psycopg2.DatabaseError, e:
            #logging.error("Get Extent error: %s by %s" %(e, self))
            print 'Error %s' % e    
            self.conn.rollback()
            return None
       
    def getShapeType(self):
        if self.shapeType:
            return self.shapeType
        try:
            if not self.conn:
                self.conn = self._connect(self.uname, self.upwd)

            cur = self.conn.cursor()
            cur.execute("SELECT geometrytype(the_geom) FROM %s" % self.tablename)
            result = cur.fetchone()[0]
            self.shapeType = result
            return result
        except psycopg2.DatabaseError, e:
            #logging.error("Get shape type error: %s by %s" %(e, self))
            print 'Error %s' % e    
            self.conn.rollback()
            return None
    
    def getShapeObjects(self):
        if self.n > 0:
            return self.shapeObjects
        
        try:
            if not self.conn:
                self.conn = self._connect(self.uname, self.upwd)
                
            shapeType = self.getShapeType()
            
            cur = self.conn.cursor()
            cur.execute("SELECT astext(the_geom) FROM %s" % self.tablename)
            rows = cur.fetchall()
           
            self.n   = 0
            startPos = len(shapeType)
            for row in rows:
                length  = 17 if row[startPos] == '-' else 16
                lat     = row[startPos:startPos+17]
                nextPos = startPos+length + 1
                lon     = row[startPos:]
                lat     = float(lat)
                lon     = float(lon)
                self.shapeObjects.append([lat,lon])
                self.n += 1
            
            return self.shapeObjects
        except psycopg2.DatabaseError, e:
            print 'Error %s' % e    
            self.conn.rollback()
            return None
        
    def getShapeObjectsByRegion(self, qregion):
        try:
            if not self.conn:
                self.conn = self._connect(self.uname, self.upwd)
                
            qShapeObjects = []
            shapeType     = self.getShapeType()
            
            qregion_str = ""
            for pt in qregion:
                pt_str       = "%s %s,"%(pt[0], pt[1])
                qregion_str += pt_str
            qregion_str = "POLYGON((" + qregion_str[:-1] + "))"
            cur = self.conn.cursor()
            """
            extent_str = "POLYGON((%s %s,%s %s,%s %s,%s %s,%s %s))" %\
                       (self.extent[0], self.extent[1],
                        self.extent[2], self.extent[1],
                        self.extent[2], self.extent[3],
                        self.extent[0], self.extent[3],
                        self.extent[0], self.extent[1])
            sql = "SELECT st_intersects('%s'::geometry, '%s'::geometry)"
            sql = sql % (qregion_str, extent_str)
            cur.execute(sql)
            result = cur.fetchone()[0]
            if result == "f":
                return qShapeObjects
            """
            sql = "SELECT astext(the_geom) FROM %s WHERE st_contains(geomfromtext('%s',4326),the_geom)"
            sql = (sql % (self.tablename,qregion_str))
            cur.execute(sql)
            rows = cur.fetchall()
           
            startPos = len(shapeType)+1
            for row in rows:
                row     = row[0][startPos:-1]
                lat,lon = row.split(' ')
                lat     = float(lat)
                lon     = float(lon)
                qShapeObjects.append((lat,lon))
           
            #logging.info("Get %s shape objects by region by %s" %(len(qShapeObjects), self))
            qShapeObjects = list(set(qShapeObjects))
            return qShapeObjects
        except psycopg2.DatabaseError, e:
            #logging.error("Get shape object by region: %s by %s" %(e, self))
            print 'Error %s' % e    
            self.conn.rollback()
            return None
        
    def getShapeIdsByRegion(self, qregion):
        try:
            if not self.conn:
                self.conn = self._connect(self.uname, self.upwd)
                
            qShapeIds = []
            shapeType = self.getShapeType()
            
            #POLYGON((-111.97775968862 33.45551380033,-111.98050627065 33.327667948884,))
            qregion_str = ""
            for pt in qregion:
                pt_str       = "%s %s,"%(pt[0], pt[1])
                qregion_str += pt_str
            qregion_str = "POLYGON((" + qregion_str[:-1] + "))"

            
            cur  = self.conn.cursor()
            sql  = "SELECT gid FROM %s WHERE st_contains('%s'::geometry,the_geom)"
            cur.execute(sql % (self.tablename,qregion_str))
            rows = cur.fetchall()
           
            for row in rows:
                gid = int(row)
                qShapeIds.append(gid-1)
            
            return qShapeIds
        except psycopg2.DatabaseError, e:
            print 'Error %s' % e    
            self.conn.rollback()
            return None
    
    def getScreenObjects(self, 
                         screenWidth,
                         screenHeight,
                         screenOffsetX=0,
                         screenOffsetY=0,
                         screenPanOffsetX=0,
                         screenPanOffsetY=0,
                         viewExtent=None):
        if viewExtent == None:
            viewExtent = self.extent
           
        screenObjects = []
        viewLeft   = viewExtent[0]
        viewBottom = viewExtent[1]
        viewRight  = viewExtent[2]
        viewTop    = viewExtent[3]
        viewWidth  = viewRight - viewLeft
        viewHeight = viewTop - viewBottom

        if len(self.shapeObjects) > 0:
            shapeIds = self.getShapeIdsByRegion(viewExtent)
            for sid in shapeIds:
                so = self.shapeObjects[sid]
                
   
        