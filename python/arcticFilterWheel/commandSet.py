"""Arctic ICC command definitions
"""
from __future__ import division, absolute_import

from twistedActor.parse import Command, CommandSet, Int

__all__ = ["arcticFWCommandSet"]


arcticFWCommandSet = CommandSet(
    commandList = [
        Command(
            commandName = "move",
            positionalArguments = [
                Int(helpStr="position to move to")
            ],
            helpStr = "move help"
        ),
        Command(
            commandName = "home",
            helpStr = "home help"
        ),
        Command(
            commandName = "stop",
            helpStr = "stop help"
        ),
        Command(
            commandName = "init",
            helpStr = "init help"
        ),
        Command(
            commandName = "status",
            helpStr = "status help"
        ),
        Command(
            commandName = "ping",
            helpStr = "show alive"
        ),
    ]
)
