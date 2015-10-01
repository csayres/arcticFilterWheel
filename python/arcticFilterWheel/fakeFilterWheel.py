from __future__ import division, absolute_import

import time

from RO.Comm.TwistedTimer import Timer

MoveTime = 3 # seconds for all moves

StatusDict = {
    "id": None,
    "encoder": None,
    "motor": 0,
    "hall": "0000",
    "position": None,
    "power": None
}


class FilterWheel(object):
    def __init__(self):
        self.moveTimer = Timer()

    def stopMove(self):
        self.moveTimer.cancel()
        StatusDict["motor"]=0


    def setup(self):
        """
        initiate filter wheel communication
        """
        pass

    def home(self):
        """
        home filter wheel and set the filter wheel id
        """
        # emulate the block
        time.sleep(3)
        StatusDict["id"] = 1
        return StatusDict["id"]

    def stop(self):
        """
        stop filter wheel motion
        """
        return self.stopMove()

    def moveToPosition(self, pos):
        """
        move to a specific filter wheel position
        arguments:
            int pos - filter position between 1 and 6
        status:
            0 - fail
            1 - succeed
            -1 - unknown
        """
        StatusDict["position"] = int(pos)
        StatusDict["motor"] = 1
        self.moveTimer.start(MoveTime, self.stopMove)
        return self.status()

    def status(self):
        """
        return current status of filter wheel
        """
        return StatusDict

