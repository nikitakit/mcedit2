"""
    command_visuals
"""
from __future__ import absolute_import, division, print_function, unicode_literals
import logging

from OpenGL import GL

from mcedit2.rendering.scenegraph.depth_test import DepthFuncNode
from mcedit2.rendering.scenegraph.misc import LineWidthNode
from mcedit2.rendering.scenegraph.scenenode import Node
from mcedit2.rendering.scenegraph.vertex_array import VertexNode
from mcedit2.rendering.selection import SelectionBoxNode
from mcedit2.rendering.vertexarraybuffer import VertexArrayBuffer
from mcedit2.util.commandblock import UnknownCommand
from mceditlib.geometry import Vector
from mceditlib.selection import BoundingBox

log = logging.getLogger(__name__)


def LineStripNode(points, rgba):
    vertexArray = VertexArrayBuffer(len(points), GL.GL_LINE_STRIP, False, False)
    vertexArray.vertex[:] = points
    vertexArray.rgba[:] = rgba
    node = VertexNode([vertexArray])
    return node


def LineArcNode(p1, p2, color):
    arcSegments = 20

    rgba = [c * 255 for c in color]
    points = [p1]
    x, y, z = p1
    dx = p2[0] - p1[0]
    dz = p2[2] - p1[2]
    dx /= arcSegments
    dz /= arcSegments
    heightDiff = p2[1] - p1[1]
    # maxRise = 8

    # initial y-velocity
    dy = 0.3 if heightDiff >= 0 else -0.3
    dy += 2 * heightDiff / arcSegments

    # the height of p2 without gravity

    overshot = y + dy * arcSegments - p2[1]

    # needed gravity so the last point is p2
    ddy = -overshot / (arcSegments * (arcSegments-1) / 2)

    for i in range(arcSegments):
        y += dy
        dy += ddy
        x += dx
        z += dz
        points.append((x, y, z))

    arcNode = Node()

    lineNode = LineStripNode(points, rgba)

    lineWidthNode = LineWidthNode(3.0)
    lineWidthNode.addChild(lineNode)

    arcNode.addChild(lineWidthNode)

    depthNode = DepthFuncNode(GL.GL_GREATER)
    depthNode.addChild(lineNode)

    arcNode.addChild(depthNode)

    return arcNode


def CommandVisuals(pos, commandObj):
    visualCls = _visualClasses.get(commandObj.name)
    if visualCls is None:
        log.warn("No command found for %s", commandObj.name)
        return Node()
    else:
        return visualCls(pos, commandObj)

class SetBlockVisuals(Node):
    commandName = "setblock"

    def __init__(self, pos, commandObj):
        super(SetBlockVisuals, self).__init__()

        x, y, z = commandObj.resolvePosition(pos)

        color = (0.2, 0.9, 0.7, 0.6)

        boxNode = SelectionBoxNode()
        boxNode.filled = False
        boxNode.wireColor = color
        boxNode.selectionBox = BoundingBox((x, y, z), (1, 1, 1))

        lineNode = LineArcNode(Vector(*pos) + (0.5, 0.5, 0.5), (x+.5, y+.5, z+.5), color)

        self.addChild(boxNode)
        self.addChild(lineNode)

class CloneVisuals(Node):
    commandName = "clone"

    def __init__(self, pos, commandObj):
        super(CloneVisuals, self).__init__()

        sourceBox = commandObj.resolveSourceBounds(pos)

        dest = commandObj.resolveDestination(pos)
        destBox = BoundingBox(dest, sourceBox.size)

        sourceColor = (0.2, 0.4, 0.9, 0.6)
        destColor = (0.0, 0.0, 0.9, 0.6)

        sourceBoxNode = SelectionBoxNode()
        sourceBoxNode.filled = False
        sourceBoxNode.wireColor = sourceColor
        sourceBoxNode.selectionBox = sourceBox

        destBoxNode = SelectionBoxNode()
        destBoxNode.filled = False
        destBoxNode.wireColor = destColor
        destBoxNode.selectionBox = destBox

        lineToSourceNode = LineArcNode(Vector(*pos) + (0.5, 0.5, 0.5), sourceBox.center, sourceColor)
        lineToDestNode = LineArcNode(sourceBox.center, destBox.center, destColor)

        self.addChild(sourceBoxNode)
        self.addChild(destBoxNode)

        self.addChild(lineToSourceNode)
        self.addChild(lineToDestNode)


class ExecuteVisuals(Node):
    commandName = "execute"

    def __init__(self, pos, commandObj):
        """

        Parameters
        ----------
        commandObj : ExecuteCommand

        Returns
        -------

        """
        super(ExecuteVisuals, self).__init__()

        selector = commandObj.targetSelector
        if selector.playerName is not None:
            return

        selectorPos = [selector.getArg(a) for a in 'xyz']

        if None in (selectorPos):
            log.warn("No selector coordinates for command %s", commandObj)
            targetPos = commandObj.resolvePosition((0, 0, 0))
        else:
            targetPos = commandObj.resolvePosition(selectorPos)

        # Draw box at selector pos and draw line from command block to selector pos
        # xxxx selector pos is a sphere of radius `selector.getArg('r')`

        boxNode = SelectionBoxNode()
        boxNode.filled = False
        boxNode.wireColor = (0.9, 0.2, 0.2, 0.6)
        boxNode.selectionBox = BoundingBox(selectorPos, (1, 1, 1))

        lineNode = LineArcNode(Vector(*pos) + (0.5, 0.5, 0.5),
                               Vector(*selectorPos) + (.5, .5, .5),
                               (0.9, 0.2, 0.2, 0.6))
        self.addChild(boxNode)
        self.addChild(lineNode)

        if selectorPos != targetPos:
            # Command block's own coordinates are different from the selected pos,
            # either relative or absolute.
            # Draw a box at the target coordinates and a line from
            # the selected pos to the target

            boxNode = SelectionBoxNode()
            boxNode.filled = False
            boxNode.wireColor = (0.9, 0.2, 0.2, 0.6)
            boxNode.selectionBox = BoundingBox(targetPos, (1, 1, 1))

            lineNode = LineArcNode(Vector(*selectorPos) + (0.5, 0.5, 0.5),
                                   Vector(*targetPos) + (.5, .5, .5),
                                   (0.9, 0.2, 0.2, 0.6))

            self.addChild(boxNode)
            self.addChild(lineNode)

        if not isinstance(commandObj.subcommand, UnknownCommand):
            subvisuals = CommandVisuals(targetPos, commandObj.subcommand)
            self.addChild(subvisuals)

_visualClasses = {cls.commandName: cls
                  for cls in [ExecuteVisuals,SetBlockVisuals,CloneVisuals]}