# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####
# ===============================================================
# Copyright 2017 Dimitris Chloupis
# ================================================================
#################################################################
#
# MORPHEAS
# =================================================================
# Morpheas is a GUI API for Blender addons that takes advantage of
# BGL module that gives access to Blender OpenGL content. In turn
# this allows the user to control and manipulate the Blender GUI
# in an extreme level. Morpheas try to make this whole process
# more easy.
#################################################################
#
# Installation
# ----------------------------------------------------------------
# Installation is very simple all you have to do is copy this file
# to the same folder as your addon. You also need to have png.py
# ( a module  that is  part of the PyPNG project, which
#  enables Morpheas to load PNG files) in the same folder.
##################################################################
#
# Documentation
# ----------------------------------------------------------------
# Documentation is included in this source file because its far
# more useful to learn how Morpheas works by examining its code.
# I tried to make my intentions in code as obvious as possible
# together with providing detailed comments
#################################################################
# ================================================================

"""
This is the basic Morpheas file. Here you will find all the necessary
classes for this library to work.
"""

import bpy
import blf
import bgl
import gpu
from gpu_extras.batch import batch_for_shader
from . import morpheas_tools
import pdb
import math


class Morph:
    """
    The Morph is extremely essential in Morpheas. It provides the base
    class that all other morph classes are inherit from. In this class is
    the most basic functionality of GUI elements that are called
    "Morphs". Specific functionality is defined on specific subclasses
    of this class. Morpheas is inspired by Morphic, a GUI that is
    also based on morphs, approaching GUI creation as a lego like process
    of assembling almost identical things together with ease and simplicity
    """

    # Global variable for the definition of the default folder where
    # the PNG files which are used as textures are located.
    texture_path = "media/graphics/"

    def __init__(
            self, texture=None, width=100, height=100, position=[0, 0],
            color=[1.0, 1.0, 1.0, 1.0], name='noname',
            on_left_click_action=None, on_left_click_released_action=None,
            on_right_click_action=None, on_right_click_released_action=None,
            on_mouse_in_action=None, on_mouse_out_action=None,
            texture_path=None, scale=1.0, round_corners=False,
            round_corners_strength=10, round_corners_select=[True, True, True, True],
            drag_drop=False, circle=False):
        """
        This is responsible for the creation of the morph, each keyword argument
        is associated with an instance variable so see the comment of the relevant
        instance variable for more information.
        """

        # If you need explanation for this, I'm worried about you.
        self.real_width = width
        self.real_height = height
        self.real_position = position

        self._width = self.real_width * scale
        self._height = self.real_height * scale
        self._position = [
            self.real_position[0],
            self.real_position[1]]

        # If no texture is defined, then this is the color of the morph.
        # Else, this affects the color and transparency of the texture.
        # Color is a list of floats following the RGBA: red, green, blue
        # and alpha (transparency). [ r , g , b, alpha ]
        self.color = color

        # Essentially these variables enable and disable the handling of specific events.
        # If events are disabled they are ignored by this morph but they do
        # pass to its children. If none handles them as well, the event
        # is passed back to Blender through world's consumed_event instance variable.
        # For more info about this, see World comments.
        self.handles_mouse_down = False
        self.handles_events = False
        self.handles_mouse_over = False
        self.handles_drag_drop = drag_drop

        self._is_hidden = False

        # A morph can be inside another morph.
        # That other morph is the parent while this morph becomes the child.
        self._parent = None
        self.children = []

        # A world is essentially a parent without a parent. World is a morph responsible for
        # anything that is not morph specific and general functionalities like figuring out
        # where the mouse is and what region draws at the time.
        self._world = None

        # These is are the positions of the 4 corners of the boundaries of the morph.
        self.bounds = [
            self.position[0], self.position[1], self.position[0] + self.width,
            self.position[1] + self.height]

        # A name is an optional feature for when you want to locate a specific morph inside a world
        # and do something to or with it.
        self._name = name

        # This counts the amount of times the morph has been drawn. Can be useful to figure out FPS
        # and make sure Morpheas does not slow down Blender.
        self.draw_count = 0

        # Though only one texture can display at time, a morph can have multiple textures.
        self.textures = {}

        # A morph can be scaled like any blender object.
        self.scale = scale

        # To be used only if no texture is given. The drawn rectangle will have round edges.
        self.round_corners = round_corners

        # Defines how much should the corners be rounded. Higher values give more rounded results.
        # Only used if round_corners is True and no texture is given.
        self.round_corners_strength = round_corners_strength

        # Defines which corners to round if round_corners is true. The order is
        # [lower_left, upper_left, upper_right, lower_right]. Default behaviour is
        # to round all of them.
        self.round_corners_select = round_corners_select

        self.circle = circle

        # This is the path to the textures.
        if texture_path is None:
            self.texture_path = Morph.texture_path
        else:
            self.texture_path = texture_path

        # Drag and drop flag.
        self.drag_drop = False
        self.drag_position = [0, 0]

        # Active texture is the texture displaying at the time.
        # Only one texture can display at a time for each morph,
        # if you want more then you have to have multiple child morphs.
        # Each child will have its own active texture.
        self.active_texture = texture

        # Not to be used by anyone but this class.
        self.image = None

        # These are actions which are basically simple python objects
        # that contain an appropriate method like on_left_click or on_right_click.
        # This allows us to keep as MVC model that has the handling of
        # events seperate from Morpheas and for the user to define his
        # own actions without having to subclass Morph.
        self.on_left_click_action = on_left_click_action
        self.on_left_click_released_action = on_left_click_released_action
        self.on_right_click_action = on_right_click_action
        self.on_right_click_released_action = on_right_click_released_action
        self.on_mouse_in_action = on_mouse_in_action
        self.on_mouse_out_action = on_mouse_out_action

        # Load the texture to be shown if a texture is given.
        if texture is not None:
            self.load_texture(self.active_texture, self.scale)

    @property
    def texture(self):
        """
        The easiest way to change the texture of the morph is to use the self.texture attribute.
        Here, Morpheas will return always the active texture when you read the variable.
        """
        return self.active_texture

    @texture.setter
    def texture(self, name):
        """
        If you try to set the variable and the texture is not part of the list of textures
        the morph has available, it loads the texture(adding it to the list of textures)
        and makes it active. If it is available it just makes it active.
        """
        if name in self.textures:
            self.activate_texture(name)
        else:
            self.load_texture(name)

    @property
    def width(self):
        """
        Return the width of the morph.
        """
        if self.real_width < 0:
            raise ValueError("width must not be a negative value")
        else:
            return self.real_width

    @property
    def width_scaled(self):
        """
        Return the scaled width of the morph.
        """
        if self._width < 0:
            raise ValueError("width must not be a negative value")
        else:
            return self._width

    @width.setter
    def width(self, value):
        """
        Change the width of the morph.
        """
        if value < 0:
            raise ValueError("new value for width must be a positive number")
        else:
            self.real_width = value
            self._width = value * self.get_absolute_scale()

    @property
    def height(self):
        """
        Return the height of the morph.
        """
        if self._height < 0:
            raise ValueError("height must not be a negative value ")
        else:
            return self.real_height

    @property
    def height_scaled(self):
        """
        Return the scaled height of the morph.
        """
        if self._height < 0:
            raise ValueError("height must not be a negative value ")
        else:
            return self._height

    @height.setter
    def height(self, value):
        """
        Change the height of the morph.
        """
        if value < 0:
            raise ValueError("new value for width must be a positive number")
        else:
            self.real_height = value
            self._height = value * self.get_absolute_scale()

    @property
    def position(self):
        """
        Return the position of the morph.
        """
        return self.real_position

    @property
    def position_scaled(self):
        """
        Return the scaled position of the morph.
        """
        return [self.real_position[0] * self.get_absolute_scale(),
                self.real_position[1] * self.get_absolute_scale()]

    @position.setter
    def position(self, value):
        """
        Change the position of the morph.
        """
        self.real_position = value
        self._position = [value[0] * self.get_absolute_scale(),
                          value[1] * self.get_absolute_scale()]

    @property
    def world_position(self):
        """
        Return world position of the morph.
        """
        if self.parent is not None:
            return [self.parent.world_position[0] + self.position[0],
                    self.parent.world_position[1] + self.position[1]]
        else:
            return [0, 0]

    @world_position.setter
    def world_position(self, value):
        """
        Can't change world position, stupid!
        """
        raise ValueError("world_position is read only !")

    @property
    def absolute_position(self):
        """
        Return absolute position of morph.
        """
        return [self.world_position[0] + self.world.draw_area[0],
                self.world_position[1] + self.world.draw_area[1]]

    @absolute_position.setter
    def absolute_position(self, value):
        """
        Can't change absolute position either...
        """
        raise ValueError("absolute_position is read only !")

    @property
    def mouse_over_morph(self):
        """
        Return true if mouse is over morph.
        """
        # If morph is a circle, conventional bounds don't work, need to
        # get the distance of the cursor position from the center of the
        # circle morph and compare it with its radius.
        if self.circle:
            ex = self.world.mouse_position_absolute[0]
            ey = self.world.mouse_position_absolute[1]

            position_x = self.get_absolute_position()[0]
            position_y = self.get_absolute_position()[1]

            circleR = float(self._width / 2)
            circleCenter = [position_x +
                            circleR, position_y + circleR]
            result = morpheas_tools.pointsDistance(
                circleCenter[0], circleCenter[1], ex, ey) <= circleR
            return result

        apx1 = self.get_absolute_position()[0]
        apy1 = self.get_absolute_position()[1]
        apx2 = self.get_absolute_position()[0] + self.width
        apy2 = self.get_absolute_position()[1] + self.height
        ex = self.world.mouse_position_absolute[0]
        ey = self.world.mouse_position_absolute[1]
        result = (ex > apx1 and ex < apx2 and ey > apy1 and ey < apy2)
        return result

    # this is an internal method not to be used directly by the user
    # it loads the texture, the actual displaying is handled by the
    # draw() method
    # name: is the same as texture and is the name of the PNG file
    # without the extension
    # scale: it allows to scale the texture
    # 1 being texture at full size
    def load_texture(self, name, scale=1.0):
        """
        This is an internal method not to be used directly by the user.
        It loads the texture, while the actual displaying is handled by the
        draw() method.
        name:
            Is the same as texture and is the name of the PNG file without the extension.
        scale:
            It allows to scale the texture, 1.0 being the full size.
        """

        # Create the full path of the texture to be loaded and load it.
        full_path = self.texture_path + name
        self.image = bpy.data.images.load(full_path)

        # A Morph can have multiple textures if it is needed, the information
        # about those textures are fetched directly from the PNG file.
        self.textures[name] = {
            'dimensions': [self.image.size[0], self.image.size[1]],
            'full_path': full_path, 'image': self.image,
            'is_gl_initialised': False, 'scale': scale, 'texture_id': 0}

        self.activate_texture(name)

        return self.textures[name]

    def activate_texture(self, name):
        """
        One texture can be active at a time in order to display on screen.
        """
        self.active_texture = name
        self.scale = self.textures[name]['scale']

    def draw(self, context):
        """
        The main draw function. Kind of a nightmare to figure out...
        """
        self._width = self.real_width * self.get_absolute_scale()
        self._height = self.real_height * self.get_absolute_scale()
        if self.parent == self.world:
            self._position = self.real_position
        else:
            self._position = [self.real_position[0] * self.get_absolute_scale(),
                              self.real_position[1] * self.get_absolute_scale()]
        position_x = self.get_absolute_position(
        )[0] - self.world.draw_area_position[0]
        position_y = self.get_absolute_position(
        )[1] - self.world.draw_area_position[1]
        width = self._width
        height = self._height

        bgl.glEnable(bgl.GL_BLEND)

        # If the morph is not hidden and a texture is given.
        if (not self.is_hidden) and (not len(self.textures) == 0):
            self.draw_count = self.draw_count + 1

            at = self.textures[self.active_texture]

            image = at['image']

            shader = gpu.shader.from_builtin('2D_IMAGE')

            if image.gl_load():
                raise Exception()

            # If there is a texture and circle is enabled, create a circle and
            # apply the texture to it.
            if self.circle:
                pos = []
                texCoord = []

                angle = 0.0

                # Circle radius and center.
                circleR = float(width / 2)
                circleCenter = [position_x +
                                circleR, position_y + circleR]

                while angle < 360.0:
                    radian = angle * (math.pi / 180.0)
                    xcos = float(math.cos(radian))
                    ysin = float(math.sin(radian))
                    x = xcos * circleR + circleCenter[0]
                    y = ysin * circleR + circleCenter[1]
                    tx = xcos * 0.5 + 0.5
                    ty = ysin * 0.5 + 0.5
                    texCoord.append((tx, ty))
                    pos.append((x, y))

                    angle += 1.0

            else:
                # Draw a simple rectangle with the dimensions, position and scale of the Morph.
                # Use the active texture as texture of the rectangle.
                pos = [
                    (position_x, position_y),
                    ((position_x + width), position_y),
                    ((position_x + width), (position_y + height)),
                    (position_x, (position_y + height))
                ]
                texCoord = [
                    (0, 0), (1, 0), (1, 1), (0, 1)
                ]

            batch = batch_for_shader(
                shader, 'TRI_FAN',
                {
                    "pos": tuple(pos),
                    "texCoord": tuple(texCoord),
                },
            )
            bgl.glActiveTexture(bgl.GL_TEXTURE0)
            bgl.glBindTexture(bgl.GL_TEXTURE_2D, image.bindcode)
            shader.bind()
            shader.uniform_int("image", 0)
            batch.draw(shader)

        # If morph is not hidden and no texture is given, create a simple rectangle,
        # with the option to have rounded corners.
        elif (not self.is_hidden) and (len(self.textures) == 0):
            if self.round_corners:
                outline = morpheas_tools.roundCorners(
                    position_x, position_y,
                    position_x +
                    width, position_y + height,
                    self.round_corners_strength,
                    self.round_corners_strength, self.round_corners_select)
                morpheas_tools.drawRegion(outline, self.color)
            elif self.circle:
                angle = 0.0

                points = []

                circleR = float(width / 2)
                circleCenter = [position_x +
                                circleR, position_y + circleR]

                while angle < 360.0:
                    radian = angle * (math.pi / 180.0)
                    xcos = float(math.cos(radian))
                    ysin = float(math.sin(radian))
                    x = xcos * circleR + circleCenter[0]
                    y = ysin * circleR + circleCenter[1]
                    new_point = [x, y]
                    points.append(new_point)

                    angle += 1.0
                morpheas_tools.drawRegion(points, self.color)
            else:
                outline = morpheas_tools.roundCorners(
                    position_x, position_y,
                    position_x +
                    width, position_y + height,
                    10, 10, [False, False, False, False])

                morpheas_tools.drawRegion(outline, self.color)

        bgl.glDisable(bgl.GL_BLEND)

        # If morph is not hidden, also draw all its children.
        if (not self.is_hidden) and len(self.children) > 0:
            for child_morph in self.children:
                child_morph.draw(context)

    @property
    def world(self):
        """
        Return Morph's World.
        Every Morph belongs to a World which is another Morph
        acting as a general manager of the behavior of Morphs.
        """
        if self._world is None and self._parent is not None:
            self._world = self.parent.world
        return self._world

    @world.setter
    def world(self, value):
        self._world = value

    @property
    def parent(self):
        """
        Return Morph's parent.
        A Morph can contain another Morph. If so, each morph it contains
        is called a "child" and for each child it is it's parent.
        """
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value

    @property
    def is_hidden(self):
        """
        Check is Morph is hidden.
        """
        return self._is_hidden

    @is_hidden.setter
    def is_hidden(self, value):
        for morph in self.children:
            if morph.is_hidden != value:
                morph.is_hidden = value
        self._is_hidden = value

    @property
    def name(self):
        """
        Return morph's name.
        """
        return self._name

    @name.setter
    def name(self, new_name):
        """
        Change morph's name.
        """
        self._name = new_name

    # Not in core.
    def delete(self):
        """
        Delete morph and all children morphs. Kind of macabre...
        """
        for child in self.children:
            child.delete()
        try:
            self.image.user_clear()
            self.image.gl_free()
            bpy.data.images.remove(self.image)
            self.textures.clear()
        except:
            pass

    # Not in core.
    def get_absolute_position(self):
        """
        Morpheas uses relative position in relation to the 3D Viewport.
        So to get the right coordinates we need to adjust them.
        Previous implementation where morphs had relative position to their
        parents did not work...
        """
        if self.parent is not None:
            return (self.parent.get_absolute_position()[0] + self._position[0],
                    self.parent.get_absolute_position()[1] + self._position[1])

        else:
            return self._position

    def get_absolute_scale(self):
        """
        Goes through all the parents and combines their scaling.
        """
        if self.parent is not None:
            return self.scale * self.parent.get_absolute_scale()
        else:
            return self.scale

    def add_morph(self, morph):
        """
        Add the Morph as a child to another Morph, the other Morph becomes its parent.
        """

        morph.parent = self
        morph.world = self.world
        self.children.append(morph)

        if self.bounds[0] > morph.bounds[0]:
            self.bounds[0] = morph.bounds[0]
        if self.bounds[1] > morph.bounds[1]:
            self.bounds[1] = morph.bounds[1]
        if self.bounds[2] < morph.bounds[2]:
            self.bounds[2] = morph.bounds[2]
        if self.bounds[3] < morph.bounds[3]:
            self.bounds[3] = morph.bounds[3]

    def get_child_morph_named(self, name):
        """
        Returns a child morph of a specific name.
        """
        for child in self.children:
            if child.name == name:
                return child
            else:
                child.get_child_morph_named(name)
        return None

    def get_child_morph_named_index(self, name):
        """
        Returns the index of a morph in the children list,
        useful for deleting the morph.
        """
        index = 0
        for child in self.children:
            if child.name == name:
                return index
            index += 1
        return None

    # Upper left and lower right corners of the bounding box,
    # defining the area occupied by the morph.

    def x(self):
        """
        x value of upper left corner of the bounding box.
        """
        return self.position[0]

    def y(self):
        """
        y value of upper left corner of the bounding box.
        """
        return self.position[1]

    def x2(self):
        """
        x value of lower right corner of the bounding box.
        """
        return self.x() + self.width

    def y2(self):
        """
        y value of lower right corner of the bounding box.
        """
        return self.y() + self.height

    def on_event(self, event, context):
        """
        This is also an internal method called by the World morph, that acts as the general
        mechanism for figuring out the type event it received and sending it to the appropriate
        specialised method. Generally this should not be overridden by your classes unless you
        want to override the general event behavior of the morph. For specific event override,
        call the relevant methods instead.
        """

        if len(self.children) > 0:
            for morph in self.children:
                morph.on_event(event, context)

        if self.handles_events and not self.is_hidden and not self.world.consumed_event:
            if event.type in {'LEFTMOUSE', 'RIGHTMOUSE'}:
                self.on_mouse_click(event)

            elif event.type in {'MOUSEMOVE'}:
                self.on_mouse_over(event)

    def on_mouse_click(self, event):
        """
        An event when any mouse button is pressed or released.
        """
        if self.mouse_over_morph:
            if self.handles_mouse_down:
                self.world.consumed_event = True
                if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                    self.on_left_click()
                if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                    self.on_left_click_released()
                if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
                    self.on_right_click()
                if event.type == 'RIGHTMOUSE' and event.value == 'RELEASE':
                    self.on_right_click_released()

    def on_mouse_over(self, event):
        """
        Αn event when the mouse cursor passes over the area occupied by the morph.
        """
        if self.drag_drop:
            cancel_drag = False

            offset = [
                self.world.mouse_position[0] - self.drag_position[0],
                self.world.mouse_position[1] - self.drag_position[1]]

            try:
                viewport_width = bpy.context.area.regions[4].width
                viewport_height = bpy.context.area.regions[4].height
            except:
                viewport_width = 100
                viewport_height = 100

            positionX = max(
                min(viewport_width - self._width, self.position[0] + offset[0]), 0)
            positionY = max(
                min(viewport_height - self._height, self.position[1] + offset[1]), 0)

            for bigMorph in self.world.children:
                if bigMorph.name != self.name and bigMorph.is_hidden is False \
                    and morpheas_tools.collisionDetect(
                        positionX, positionY, bigMorph.position_scaled[0],
                        bigMorph.position_scaled[1], self.width_scaled, self.height_scaled,
                        bigMorph.width_scaled, bigMorph.height_scaled):
                    cancel_drag = True

            if cancel_drag is False:
                self.position = [positionX, positionY]
                # self.position = [
                #     self.position[0] +
                #     offset[0], self.position[1] + offset[1]]
                self.drag_position = self.world.mouse_position
        if self.mouse_over_morph:
            return self.on_mouse_in()
        else:
            return self.on_mouse_out()

    # The following methods should be self explanatory and
    # depend on the action classes passed to the morph.
    # These are also the methods to override if you want to
    # treat specifc events differently inside your morph.

    def on_left_click(self):
        if self.on_left_click_action is not None:
            return self.on_left_click_action.on_left_click(self)
        else:
            if not self.drag_drop and self.handles_drag_drop:
                self.drag_drop = True
                self.drag_position = self.world.mouse_position
            return self.world.event

    def on_left_click_released(self):
        if self.on_left_click_released_action is not None:
            return self.on_left_click_released_action.on_left_click_released(self)
        else:
            if self.drag_drop and self.handles_drag_drop:
                self.drag_drop = False
            return self.world.event

    def on_right_click(self):
        if self.on_right_click_action is not None:
            return self.on_right_click_action.on_right_click(self)
        else:
            return self.world.event

    def on_right_click_released(self):
        if self.on_right_click_released_action is not None:
            return self.on_right_click_released_action.on_right_click_released(self)
        else:
            return self.world.event

    def on_mouse_in(self):
        """
        An event for when the mouse enters the area of the Morph.
        """
        if self.on_mouse_in_action is not None:
            return self.on_mouse_in_action.on_mouse_in(self)
        else:
            return self.world.event

    def on_mouse_out(self):
        """
        An event for when the mouse exits the area of the Morph.
        """
        if self.on_mouse_out_action is not None:
            return self.on_mouse_out_action.on_mouse_in(self)
        else:
            return self.world.event


class World(Morph):
    """
    World morph is a simple morph that triggers and handles the drawing methods and event methods
    for each child morph. In order for a morph to be a child of a World it has to be added to it or
    else it won't display. There can be more than one world.
    Generally this is not necessary if you want to create a multi layer interfaces because each
    morph can act as a container (parent) to other morphs (children).
    On the other hand there are cases when you want each layer to be really separate and with
    its own handling of events and drawing which make sense to have multiple worlds.
    The choice is up to you but remember you have to call draw and on_event methods for each
    world you have if you want that world to display and handle events for its children morphs.
    A world requires a modal operator, because only Blender's modal operators are the recommended
    way for handling Blender events and drawing on regions of internal Blender windows.
    As such the draw() method must be called inside the method associated with the modal's drawing
    and on_event is called on the modal method of your modal operator.
    You need to call only those two methods for Morpheas to work.
    Of course it's taking into account you have already created a world, then the morphs and added
    them to the world via add_morph method.
    """

    def __init__(self, singular=True, auto_hide=True, **kargs):

        super().__init__(**kargs)

        # This defines whether the event send to World's onEvent method
        # has been handled by any morph. If it has not , you can use this variable
        # to make sure your modal method returns {"PASS_THROUGH"} so that the event
        # is passed back to Blender and you don't block user interaction.
        self.consumed_event = False

        # The modal operator that uses this World.
        self.modal_operator = 0

        # The coordinates of the mouse cursor, its the same as blender mouse coordinates
        # of the WINDOW region of the internal window that has been assigned the modal
        # operator needed to draw and send events to Morpheas. Blender does not change that
        # window, so the mouse coordinates starting [0,0] does not change as well.
        self.mouse_position = [0, 0]

        # The absolute coordinates are different in that they don't start from the bottomn left
        # corner of the region assigned the handling of event by Blender, but rather
        # they are located at the bottom left corner of the Blender window.
        # This is necessary when Morpheas draws in regions not associated
        # by Blender with handling of events to figure out exactly where the
        # mouse is located inside the entire Blender window.
        self.mouse_position_absolute = [0, 0]

        # When mouse is inside a region that is drawing at the time
        # this is used for auto_hide feature.
        self.mouse_cursor_inside = False

        # Window here is the region that is associated with the handling of events
        # and it does not change, as this is defined by Blender. Morpheas itself gives any region
        # that calls the on_event method the ability to handle events through the World morph.
        # Generally, this should not concern you because it happens
        # automatically and does not require any additional information.
        self.window_position = [0, 0]
        self.window_width = 300
        self.window_height = 300

        # The blender event as it is.
        self.event = None

        # Draw area is the region at that particular time that draws the world.
        # Even though in blender only one region is responsible with event handling,
        # for Morpheas any other region can draw graphics and receive events as well.
        # This is useful when you replicate the same internal window, for example when
        # you have opened multiple 3d views.
        self.draw_area = [0, 0, 0, 0]
        self.draw_area_position = [0, 0]
        self.draw_area_width = 300
        self.draw_area_height = 300
        self.draw_area_context = None

        # This feature hides the World on regions that the mouse is on top of
        # so it depends on self.mouse_cursor_inside.
        self.auto_hide = True

        self._width = 2000
        self._height = 2000

    def get_absolute_position(self):
        """
        Position with coordinates that start [0,0] at the bottom of the entire Blender window
        (not to be confused with Blender's own internal windows).
        """
        return [self.position[0] + self.draw_area_position[0],
                self.position[1] + self.draw_area_position[1]]

    def disable_all_drag_drop(self, morph):
        """
        With a morph given(the world), recursively disable all drag_drops.
        """
        for child in morph.children:
            child.drag_drop = False
            self.disable_all_drag_drop(child)

        # World draw depends on Morph draw, what it does additionally is the auto_hide feature
    def draw(self, context):
        self.draw_area_context = context
        if self.event is not None:
            # Use OpenGL to get the size of the region we can draw without overlapping with other areas
            mybuffer = bgl.Buffer(bgl.GL_INT, 4)
            bgl.glGetIntegerv(bgl.GL_VIEWPORT, mybuffer)
            mx = self.event.mouse_region_x
            my = self.event.mouse_region_y
            mabx = self.mouse_position_absolute[0]
            maby = self.mouse_position_absolute[1]

            mybuffer[0] = bpy.context.area.regions[4].x
            mybuffer[1] = bpy.context.area.regions[4].y

            self.mouse_cursor_inside = (
                (mabx > mybuffer[0]) and (mabx < (mybuffer[0] + mybuffer[2])) and (
                    maby > mybuffer[1]) and (maby < (mybuffer[1] + mybuffer[3])))

            # When cursor is outside the area that draws, disable all drag_drops.
            if not self.mouse_cursor_inside:
                self.disable_all_drag_drop(self)

            # If auto_hide is enabled, draw my Morphs ONLY if the mouse is located inside the area
            # that draws at the time.
            if (self.mouse_cursor_inside and
                self.auto_hide and context.area.type == "VIEW_3D" and
                    context.region.type == "WINDOW") or not self.auto_hide:
                self.draw_area_context = context
                self.draw_area = mybuffer

                # from that extract information about the region and
                # assign it to relevant instance variables
                self.draw_area_position = [mybuffer[0], mybuffer[1]]
                self.draw_area_width = mybuffer[2]
                self.draw_area_height = mybuffer[3]

                self.mouse_position = [
                    self.mouse_position_absolute[0] - self.draw_area[0],
                    self.mouse_position_absolute[1] - self.draw_area[1]]
                for child in self.children:
                    child.draw(self.draw_area_context)
                    # context.area.tag_redraw()

    def add_morph(self, morph):
        """
        A world cannot have a world by itself and of course neither a parent.
        This is why we override the Morph add_morph method.
        """
        morph.parent = self
        morph.world = self
        self.children.append(morph)

        if self.bounds[0] > morph.bounds[0]:
            self.bounds[0] = morph.bounds[0]
        if self.bounds[1] > morph.bounds[1]:
            self.bounds[1] = morph.bounds[1]
        if self.bounds[2] < morph.bounds[2]:
            self.bounds[2] = morph.bounds[2]
        if self.bounds[3] < morph.bounds[3]:
            self.bounds[3] = morph.bounds[3]

    def on_event(self, event, context):
        """
        Again this depends on Morph on_event.
        Here we automatically set up information about which region has been
        assigned by Blender to handle events.
        """

        # If user has maximized screen and fucks about, he might create
        # some problems and the region will be None. This solves the issue.
        if context.region is None:
            return

        bmx = context.region.x
        bmy = context.region.y
        self.window_position = (bmx, bmy)

        self.window_width = context.region.width
        self.window_height = context.region.height

        self.mouse_position_absolute = [
            event.mouse_region_x + self.window_position[0], event.mouse_region_y + self.window_position[1]]
        self.event = event

        # consumed_event is reset so World does not block events that are not handled by it.
        # Instead, those events are passed back to Blender through the {'PASS_THROUGH'} return,
        # so you need to check out this variable and if it is False you need to make sure
        # the modal method of your modal operator(needed for Morpheas to work)
        # returns {'PASS_THROUGH'}, if you want your user to interact with a Morpheas GUI and
        # Blender at the same time, or else you will have an angry user hunting you down in forums.
        # That's why we always have good excuses, like university exams or work...
        self.consumed_event = False

        for morph in self.children:
            morph.on_event(event, context)


class TextMorph(Morph):
    """
    TextMorph is a class that defines a simple label, a piece of text of any size.
    """

    def __init__(self, font_id=0, text="empty string", x=15, y=0, size=16, dpi=72, **kargs):
        self.real_position = [x, y]
        super().__init__(texture=None, **kargs)
        self.size = size
        self.dpi = dpi
        self.text = text
        self.font_id = 0

    def draw(self, context):
        if not self.is_hidden:
            position_x = self.get_absolute_position(
            )[0] - self.world.draw_area_position[0]
            position_y = self.get_absolute_position(
            )[1] - self.world.draw_area_position[1]
            # blf.glColor4f(*self.color)
            blf.color(
                0, self.color[0], self.color[1],
                self.color[2], self.color[3])
            blf.size(self.font_id, self.size, self.dpi)
            blf.position(self.font_id, position_x, position_y, 0)
            blf.draw(self.font_id, self.text)


class ButtonMorph(Morph):
    """
    A ButtonMorph is a morph that responds to an action. This is a default
    behavior for morphs, however ButtonMorph makes it a bit easier and provides
    an easy way to change the morph appearance when the mouse is hovering over
    the button.
    """

    def __init__(self, hover_glow_mode=True, **kargs):
        super().__init__(**kargs)
        self.handles_mouse_over = True
        self.handles_events = True
        self.handles_mouse_down = True

        # hover_glow_mode will make the button semi transparent,
        # if the mouse is outside its boundaries.
        self.hover_glow_mode = hover_glow_mode

    def on_mouse_in(self):
        if self.hover_glow_mode:
            self.change_appearance(1)

    def on_mouse_out(self):
        if self.hover_glow_mode:
            self.change_appearance(0)

    def change_appearance(self, value):
        """
        If hovel_glow_mode is enabled, this will change the morph's
        appearance accordingly.
        """

        if value == 0:
            self.color = (self.color[0], self.color[1], self.color[2], 0.5)
        if value == 1:
            self.color = (self.color[0], self.color[1], self.color[2], 1.0)
