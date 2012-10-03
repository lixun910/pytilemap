#!/Library/Frameworks/Python.framework/Versions/2.7/bin/python
import os
import sys

if not os.getenv("DEBUG"):
    import cgitb
    cgitb.enable()


import tileserver

if os.getenv("DEBUG"):
    os.remove("/var/cache/"+os.getenv("REQUEST_URI"))
"""
import datetime
print datetime.datetime.now() 
fn = tileserver.get_tile("/"+"/".join("/pytilemap/crime/classic/10/3,5.png".split("/")[-4:]))
fn = tileserver.get_tile("/"+"/".join("/pytilemap/crime/classic/10/193,410.png".split("/")[-4:]))
fn = tileserver.get_tile("/"+"/".join("/pytilemap/crime/classic/10/194,410.png".split("/")[-4:]))
fn = tileserver.get_tile("/"+"/".join("/pytilemap/crime/classic/10/193,411.png".split("/")[-4:]))
fn = tileserver.get_tile("/"+"/".join("/pytilemap/crime/classic/10/194,411.png".split("/")[-4:]))
print datetime.datetime.now() 
"""
fn = tileserver.get_tile("/"+"/".join(os.getenv("REQUEST_URI").split("/")[-4:]))

if not os.path.exists(fn):
    print "Status: 404 Not Found"
    print "Content-type: text/plain"
    print ""
    print fn
    sys.exit(1)

if os.getenv("DEBUG"):
    print "Content-type: text/plain"
    print ""
    print fn
    sys.exit(0)

print "Location:http://%s%s\n" % (os.getenv("HTTP_HOST"),os.getenv("REQUEST_URI"))