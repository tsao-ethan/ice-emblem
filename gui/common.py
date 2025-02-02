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


import room


class Image(room.Room):
    def __init__(self, image, **kwargs):
        super().__init__(bg_image=image, **kwargs)
        self.bg_color = kwargs.get('bg_color', None)

    def measure(self, spec_width, spec_height):
        self.resolve_measure(spec_width, spec_height, *self.bg_image.get_size())

    def handle_keydown(self, _event):
        self.done = True

    def handle_mousebuttondown(self, _event):
        self.done = True

