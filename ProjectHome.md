PyTileMap renders tile maps to Google Maps/Bing Maps/OpenStreetMap from your shape files and spatial database (supports Postgres+PostGIS).

Download the source code, and setup your own tile map server to display your spatial data.

News:

9/25/2012  First commit, a work around version for rendering shape files with simple color scheme into tiles.

![https://lh3.googleusercontent.com/-03CRIY7iSkw/UGKA6Wp_5qI/AAAAAAAABpw/4uw2aHBmNqs/s512/Picture%25252099.png](https://lh3.googleusercontent.com/-03CRIY7iSkw/UGKA6Wp_5qI/AAAAAAAABpw/4uw2aHBmNqs/s512/Picture%25252099.png)

_This work is supported by Geoda Center at Arizona State University._



---

  * Pytilemap URI definition:

`/dataset_name/map_type[,map_type_parameters]/zoom/x,y.pn`

  * `dataset_name`: can be the file name of shape files (without .shp postfix), or the database table name in PostGIS.

> (NOTE: by default, the geometry column "the\_geom" is used in PyTileMap.)

  * `map_type`: PyTileMap now supports several different map types:
    * `classic`:  map without color scheme or style, POINTs are rendered in RED and POLYGONS are rendered in BLUE
    * `color`:    (NOTE: this is only supported in PostGIS setup) map with color scheme, which can be specified by the color column in database table. By default, the column name "color" is used in PyTileMap. One can specify the name of color column by adding a parameter.          For example, `/dataset_name/color,mycolorcolumn/zoom/x,y.png`
    * `classify`: PyTileMap supports several popular classify maps, such as: quantile/percentile/, and uses the popular ColorBrewer as the color schemes.         For example: `/dataset_name/classify,variable,quantile,5/zoom/x,y.png`


---

  * Import data into PostGIS database:
    * Reprojecting shapefiles to Lat-Lon format
      * `ogr2ogr -skipfailures -t_srs EPSG:4326 -f "ESRI Shapefile" reproject_shape_file original_shape_file`
    * Import shapefile into PostGIS database
      * `shp2pgsql -s 4326 shape_file > import.sql`
      * `psql -h host -q -f import.sql -d databasename -U username`