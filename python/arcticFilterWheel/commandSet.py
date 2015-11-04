"""Arctic ICC command definitions
"""
from __future__ import division, absolute_import

from twistedActor.parse import Command, CommandSet, Int

__all__ = ["arcticFWCommandSet"]


arcticFWCommandSet = CommandSet(
    actorName = "Arctic Filter Wheel",
    commandList = [
        Command(
            commandName = "move",
            positionalArguments = [
                Int(helpStr="Filter wheel position")
            ],
            helpStr = "Move filter wheel to an integer position.",
        ),
        Command(
            commandName = "home",
            helpStr = "Home the filter wheel."
        ),
        Command(
            commandName = "stop",
            helpStr = "Stop any filter wheel movement."
        ),
        Command(
            commandName = "initialize",
            helpStr = "Initialize the filter wheel."
        ),
        Command(
            commandName = "status",
            helpStr = "Query filter wheel for status."
        ),
        Command(
            commandName = "ping",
            helpStr = "Show alive."
        ),
    ]
)
