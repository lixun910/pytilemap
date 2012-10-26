#!/usr/bin/python
import os
import sys
from tileserver import get_tile

#import shutil
#shutil.rmtree("/var/www/redmine/public/dist/tmp/dist/pytilemap/data_and_rates_for_beats")

fn = get_tile("/"+"/".join(os.getenv("REQUEST_URI").split("/")[-4:]))
#fn = get_tile("/asu_mesa_tempe_merge2005_2009/classic/4/3,1.png")

if not os.path.exists(fn):
    print "Status: 404 Not Found"
    print "Content-type: text/plain"
    print ""
    print fn
    sys.exit(1)

print "Location:http://%s%s\n" % (os.getenv("HTTP_HOST"),os.getenv("REQUEST_URI"))
