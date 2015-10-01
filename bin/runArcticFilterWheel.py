#!/usr/bin/env python2
from __future__ import division, absolute_import
"""Run the Arctic Filter Wheel actor
"""
import os

from twisted.internet import reactor
from twistedActor import startFileLogging

from arcticFilterWheel import ArcticFWActor


UserPort = 37000
homeDir = os.getenv("HOME")
logDir = os.path.join(homeDir, "logs/arcticFilterWheel")

try:
    startFileLogging(logDir)
except KeyError:
   # don't start logging
   pass

if __name__ == "__main__":
    print("arcticFilterWheel running on port %i"%UserPort)
    arcticFilterWheel = ArcticFWActor(name="arcticFilterWheel", userPort=UserPort)
    reactor.run()