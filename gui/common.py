# -*- coding: utf-8 -*-
#
#  menu.py, Ice Emblem's menu class.
#
#  Copyright 2015 Elia Argentieri <elia.argentieri@openmailbox.org>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.


import pygame

import room
from enum import Flag, auto


class Gravity(Flag):
    NO_GRAVITY = 0  # Constant indicating that no gravity has been set
    TOP = auto()  # Push object to the top of its container, not changing its size.
    BOTTOM = auto()  # Push object to the bottom of its container, not changing its size.
    LEFT = auto()  # Push object to the left of its container, not changing its size.
    RIGHT = auto()  # Push object to the right of its container, not changing its size.
    TOPLEFT = TOP | LEFT
    TOPRIGHT = TOP | RIGHT
    BOTTOMLEFT = BOTTOM | LEFT
    BOTTOMRIGHT = BOTTOM | RIGHT
    CENTER_HORIZONTAL = auto()  # Place object in the horizontal center of its container, not changing its size.
    CENTER_VERTICAL   = auto()  # Place object in the vertical center of its container, not changing its size.
    CENTER = CENTER_HORIZONTAL | CENTER_VERTICAL  # Place the object in the center of its container in both the vertical and horizontal axis, not changing its size.
    FILL_HORIZONTAL = auto()  # Grow the horizontal size of the object if needed so it completely fills its container.
    FILL_VERTICAL = auto()  # Grow the vertical size of the object if needed so it completely fills its container.
    FILL = FILL_HORIZONTAL | FILL_VERTICAL  # Grow the horizontal and vertical size of the object if needed so it completely fills its container.
    VERTICAL = TOP | BOTTOM | CENTER_HORIZONTAL | FILL_HORIZONTAL
    HORIZONTAL = LEFT | RIGHT | CENTER_VERTICAL | FILL_VERTICAL


class GUI(room.Room):
    def __init__(self, **kwargs):
        self._content_size = (0, 0)
        self._padding = (0, 0, 0, 0)
        super().__init__(**kwargs)
        self._content_size = self.rect.size
        self.padding = kwargs.get('padding', (0, 0, 0, 0))
        self.layout_gravity = kwargs.get('layout_gravity', Gravity.NO_GRAVITY)

    @property
    def content_size(self):
        return self._content_size

    @content_size.setter
    def content_size(self, size):
        self._content_size = size
        self.update_size()
        if isinstance(self.parent, GUI):
            self.parent.compute_content_size()

    def compute_content_size(self):
        self.rect.apply()

    @property
    def padding(self):
        return self._padding

    @padding.setter
    def padding(self, padding):
        if isinstance(padding, int):
            self._padding = (padding,) * 4
        elif len(padding) == 2:
            self._padding = padding * 2
        elif len(padding) == 4:
            self._padding = padding
        else:
            raise ValueError("padding shold be either an int or a couple or a quadruple")
        self.update_size()

    def update_size(self):
        self.rect.size = (self.padding[1] + self.padding[3] + self.content_size[0],
                        self.padding[0] + self.padding[2] + self.content_size[1])
        self.rect.apply()
        self.surface = pygame.Surface(self.rect.size).convert_alpha()
        self.invalidate()


class Image(GUI):
    def __init__(self, image, **kwargs):
        self.image = image
        super().__init__(**kwargs)
        self.compute_content_size()
        self.bg_color = kwargs.get('bg_color', (0, 0, 0, 0))

    def compute_content_size(self):
        self.content_size = self.image.get_size()

    def draw(self):
        self.surface.fill(self.bg_color)
        self.surface.blit(self.image, (0, 0))
        super().draw()

