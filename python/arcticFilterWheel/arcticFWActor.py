from __future__ import division, absolute_import

import syslog


from RO.Comm.TwistedTimer import Timer

from twistedActor import Actor, expandUserCmd, log, UserCmd

from .commandSet import arcticFWCommandSet
from .version import __version__

from filter import FilterWheel

from .fakeFilterWheel import FilterWheel as FakeFilterWheel

UserPort = 37000

class ArcticFWStatus(object):
    def __init__(self):
        self.id = 0
        self.currentEncoder = "NaN"
        self.motor = 0
        # self.hall = "?"
        self.position = 0
        # self.power = "?"
        self.isHomed = 0
        self.isHoming = 0
        self.desiredStep = "NaN"
        self.currentStep = "NaN"
        self._cmdFilterID = "NaN"

    @property
    def kwMap(self):
        return dict((
            ("wheelID", self.id),
            ("filterID", self.position),
            ("cmdFilterID", self.cmdFilterID),
            ("isMoving", self.motor),
            ("isHomed", self.isHomed),
            ("isHoming", self.isHoming),
            ("encoderPos", self.currentEncoder),
            ("desiredStep", self.desiredStep),
            ("currentStep", self.currentStep),
        ))

    @property
    def cmdFilterID(self):
        if self._cmdFilterID == "NaN" and not 1 in [self.motor, self.isHoming] and self.isHomed:
            # asked for commanded filter but currently set to NaN, everything looks fine
            # set it to commanded ID
            self._cmdFilterID = self.position
        return self._cmdFilterID # may return none

    @cmdFilterID.setter
    def cmdFilterID(self, value):
        self._cmdFilterID = value

    @property
    def moveStr(self):
        statusList = []
        for kw in ["isMoving", "cmdFilterID"]:
            statusList.append("%s=%s"%(kw, str(self.kwMap[kw])))
        return "; ".join(statusList)


    @property
    def statusStr(self):
        # todo: only output a changed status value?
        return "; ".join(["%s=%s"%(kw, str(val)) for kw, val in self.kwMap.iteritems()])

class ArcticFWActor(Actor):
    Facility = syslog.LOG_LOCAL1
    DefaultTimeLim = 5 # default time limit, in seconds
    PollTime = 0.05 # seconds
    MoveRange = range(1,7)
    # State options
    def __init__(self,
        name,
        userPort = UserPort,
        commandSet = arcticFWCommandSet,
        fakeFilterWheel = False,
    ):
        """!Construct an ArcticFWActor

        @param[in] name  actor name
        @param[in] userPort  int, a port on which this thing runs
        @param[in] commandSet  a twistedActor.parse.CommandSet used for command def, and parsing
        @param[in] fakeFilterWheel  bool.  If true use a fake filter wheel device, for safe testing.
        """
        self.status = ArcticFWStatus()
        self.moveCmd = UserCmd()
        self.moveCmd.setState(self.moveCmd.Done)
        self.pollTimer = Timer()
        if fakeFilterWheel:
            self.FilterWheelClass = FakeFilterWheel
        else:
            self.FilterWheelClass = FilterWheel
        self.filterWheel = self.FilterWheelClass()
        self.filterWheel.connect()
        Actor.__init__(self,
            userPort = userPort,
            maxUsers = 1,
            name = name,
            version = __version__,
            commandSet = commandSet,
            )
        # init the filterWheel
        # this sets self.filterWheel
        self.init(getStatus=False)

    def init(self, userCmd=None, getStatus=True, timeLim=DefaultTimeLim):
        """! Initialize all devices, and get status if wanted
        @param[in]  userCmd  a UserCmd or None
        @param[in]  getStatus if true, query all devices for status
        @param[in]  timeLim
        """
        userCmd = expandUserCmd(userCmd)
        log.info("%s.init(userCmd=%s, timeLim=%s, getStatus=%s)" % (self, userCmd, timeLim, getStatus))
        # print("%s.init(userCmd=%s, timeLim=%s, getStatus=%s)" % (self, userCmd, timeLim, getStatus))
        # initialize the fw, command status after
        # self.filterWheel = self.FilterWheelClass()
        # self.filterWheel.connect()
        # self.cmd_home(expandUserCmd(None)) # blocks and sets isHomed flag
        if getStatus:
            self.cmd_status(userCmd) # sets done
        else:
            userCmd.setState(userCmd.Done)
        return userCmd

    def cmd_init(self, userCmd):
        """! Implement the init command
        @param[in]  userCmd  a twistedActor command with a parsedCommand attribute
        """
        log.info("%s.cmd_init(userCmd=%s)"%(self, str(userCmd)))
        # print("%s.cmd_init(userCmd=%s)"%(self, str(userCmd)))
        self.init(userCmd, getStatus=True)
        # userCmd.setState(userCmd.Done)
        return True

    def cmd_ping(self, userCmd):
        """! Implement the ping command
        @param[in]  userCmd  a twistedActor command with a parsedCommand attribute
        """
        log.info("%s.cmd_ping(userCmd=%s)"%(self, str(userCmd)))
        # print("%s.cmd_ping(userCmd=%s)"%(self, str(userCmd)))
        userCmd.setState(userCmd.Done, textMsg="alive")
        return True

    def cmd_stop(self, userCmd):
        log.info("%s.cmd_stop(userCmd=%s)"%(self, str(userCmd)))
        # print("%s.cmd_stop(userCmd=%s)"%(self, str(userCmd)))
        if not self.moveCmd.isDone:
            self.moveCmd.setState(self.moveCmd.Failed, "stop commanded")
        self.filterWheel.stop()
        userCmd.setState(userCmd.Done)
        return True

    def cmd_move(self, userCmd):
        desPos = int(userCmd.parsedCommand.parsedPositionalArgs[0])
        log.info("%s.cmd_move(userCmd=%s) desPos: %i"%(self, userCmd, desPos))
        # print("%s.cmd_move(userCmd=%s) desPos: %i"%(self, userCmd, desPos))
        if desPos not in self.MoveRange:
            # raise ParseError("desPos must be one of %s for move command"%(str(self.MoveRange),))
            userCmd.setState(userCmd.Failed, "desPos must be one of %s for move command"%(str(self.MoveRange),))
        elif not self.status.isHomed:
            userCmd.setState(userCmd.Failed, "cannot command move, home filter wheel first.")
        elif not self.moveCmd.isDone:
            userCmd.setState(userCmd.Failed, "filter wheel is moving")
        else:
            self.moveCmd = userCmd
            if not self.moveCmd.isActive:
                self.moveCmd.setState(self.moveCmd.Running)
            self.status.cmdFilterID = desPos
            self.filterWheel.moveToPosition(desPos - 1) # filterwheel is 0 indexed
            self.getStatus()
            self.writeToUsers("i", self.status.moveStr, cmd=userCmd)
            self.pollStatus()
        return True

    def cmd_home(self, userCmd):
        log.info("%s.cmd_home(userCmd=%s)"%(self, str(userCmd)))
        # print("%s.cmd_home(userCmd=%s)"%(self, str(userCmd)))
        self.status.isHoming = 1
        # send out status (basically announce I'm homing)
        self.cmd_status(userCmd, setDone=False)
        self.filterWheel.home() # blocks
        self.status.isHomed = 1
        self.status.isHoming = 0
        self.cmd_status(userCmd, setDone=False)
        userCmd.setState(userCmd.Done)
        return True

    def cmd_status(self, userCmd, setDone=True):
        """! Implement the status command
        @param[in]  userCmd  a twistedActor command with a parsedCommand attribute
        """
        log.info("%s.cmd_status(userCmd=%s)"%(self, str(userCmd)))
        # print("%s.cmd_status(userCmd=%s)"%(self, str(userCmd)))
        # statusStr = self.getCameraStatus()
        # self.writeToUsers("i", statusStr, cmd=userCmd)
        self.getStatus()
        self.writeToUsers("i", self.status.statusStr, cmd=userCmd)
        if setDone:
            userCmd.setState(userCmd.Done)
        return True

    def pollStatus(self):
        """Begin continuously filter wheel for status, to determine when a pending move command is done.
        Only poll while filter wheel is moving
        """
        self.getStatus()
        if self.status.motor == 0:
            if not self.moveCmd.isDone:
                log.info("current move done")
                print("current move done")
                self.cmd_status(self.moveCmd) # status will set command done
        else:
            # motor is still moving, continue polling
            self.pollTimer.start(self.PollTime, self.pollStatus)

    def getStatus(self):
        """! A generic status command
        @param[in] userCmd a twistedActor UserCmd or none
        """
        for key, val in self.filterWheel.status().iteritems():
            if key == "position":
                val += 1 # filter wheel is zero indexed
            setattr(self.status, key, val)





