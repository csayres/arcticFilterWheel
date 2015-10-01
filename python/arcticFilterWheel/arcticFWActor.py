from __future__ import division, absolute_import

import syslog


from RO.Comm.TwistedTimer import Timer

from twistedActor import Actor, expandUserCmd, log, UserCmd
from twistedActor.parse import ParseError

from .commandSet import arcticFWCommandSet
from .version import __version__

from filter import FilterWheel

from .fakeFilterWheel import FilterWheel as FakeFilterWheel

class ArcticFWStatus(object):
    def __init__(self):
        self.id = "?"
        self.encoder = "?"
        self.motor = "?"
        self.hall = "?"
        self.position = "?"
        self.power = "?"

    @property
    def kwMap(self):
        return [
            ("wheelWheelID", self.id),
            ("filterID", self.position),
            ("filterMoving", self.motor),
            ("filterEncoder", self.encoder)
        ]

    @property
    def moveStr(self):
        return "%s=%s"%(self.kwMap[2])

    @property
    def statusStr(self):
        return "; ".join(["%s=%s"%(kw, str(val)) for kw, val in self.kwMap])

class ArcticFWActor(Actor):
    Facility = syslog.LOG_LOCAL1
    DefaultTimeLim = 5 # default time limit, in seconds
    PollTime = 0.05 # seconds
    MoveRange = range(1,7)
    def __init__(self,
        name,
        userPort,
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
        self.filterWheel = None
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
        # initialize the fw, command status after
        self.filterWheel = self.FilterWheelClass()
        self.filterWheel.setup()
        self.filterWheel.home() # blocks
        if getStatus:
            self.cmd_status(userCmd) # sets done
        else:
            userCmd.setState(userCmd.Done)
        return userCmd

    def cmd_init(self, userCmd):
        """! Implement the init command
        @param[in]  userCmd  a twistedActor command with a parsedCommand attribute
        """
        self.init(userCmd, getStatus=True)
        # userCmd.setState(userCmd.Done)
        return True

    def cmd_ping(self, userCmd):
        """! Implement the ping command
        @param[in]  userCmd  a twistedActor command with a parsedCommand attribute
        """
        userCmd.setState(userCmd.Done, textMsg="alive")
        return True

    def cmd_stop(self, userCmd):
        if not self.moveCmd.isDone:
            self.moveCmd.setState(self.moveCmd.Failed, "stop commanded")
        self.filterWheel.stop()
        userCmd.setState(userCmd.Done)
        return True

    def cmd_move(self, userCmd):
        desPos = int(userCmd.parsedCommand.parsedPositionalArgs[0])
        if desPos not in self.MoveRange:
            raise ParseError("desPos must be one of %s for move command"%(str(self.MoveRange),))
        if not self.moveCmd.isDone:
            userCmd.setState(userCmd.Failed, "filter wheel is moving")
        else:
            self.moveCmd = userCmd
            if not self.moveCmd.isActive:
                self.moveCmd.setState(self.moveCmd.Running)
            self.filterWheel.moveToPosition(desPos)
            self.getStatus()
            self.writeToUsers("i", self.status.moveStr, cmd=userCmd)
            self.pollStatus()
        return True

    def cmd_home(self, userCmd):
        self.filterWheel.home() # blocks
        userCmd.setState(userCmd.Done)
        return True

    def cmd_status(self, userCmd, setDone=True):
        """! Implement the status command
        @param[in]  userCmd  a twistedActor command with a parsedCommand attribute
        """
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
                self.cmd_status(self.moveCmd) # status will set command done
        else:
            # motor is still moving, continue polling
            self.pollTimer.start(self.PollTime, self.pollStatus)

    def getStatus(self):
        """! A generic status command
        @param[in] userCmd a twistedActor UserCmd or none
        """
        for key, val in self.filterWheel.status().iteritems():
            setattr(self.status, key, val)





