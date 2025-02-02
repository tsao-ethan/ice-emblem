"""
This module is central in Ice Emblem's engine since it provides the Room class and some functions that uniformly act
upon Room objects.
"""

from typing import Callable, List, Tuple

import pygame
import pygame.locals as p
import logging

from enum import Flag, Enum, auto
import colors as c

import events
import display
import utils

from basictypes import NESW


class Gravity(Flag):
    """
    Standard constants and tools for placing an object within a potentially larger container.

    | Gravity is used in Room.layout_gravity and Room.layout.
    | The former specify how a child would like to be positioned and sized by the parent.
    | The latter specify how a parent should position and size it's children that have no preference.

    This class has taken inspiration from android.view.Gravity.
    """
    NO_GRAVITY = 0  #: Constant indicating that no gravity has been set
    TOP = auto()  #: Push object to the top of its container, not changing its size.
    BOTTOM = auto()  #: Push object to the bottom of its container, not changing its size.
    LEFT = auto()  #: Push object to the left of its container, not changing its size.
    RIGHT = auto()  #: Push object to the right of its container, not changing its size.
    TOPLEFT = TOP | LEFT
    TOPRIGHT = TOP | RIGHT
    BOTTOMLEFT = BOTTOM | LEFT
    BOTTOMRIGHT = BOTTOM | RIGHT
    CENTER_HORIZONTAL = auto()  #: Place object in the horizontal center of its container, not changing its size.
    CENTER_VERTICAL   = auto()  #: Place object in the vertical center of its container, not changing its size.
    CENTER = CENTER_HORIZONTAL | CENTER_VERTICAL  #: Place the object in the center of its container in both the vertical and horizontal axis, not changing its size.
    FILL_HORIZONTAL = auto()  #: Grow the horizontal size of the object if needed so it completely fills its container.
    FILL_VERTICAL = auto()  #: Grow the vertical size of the object if needed so it completely fills its container.
    FILL = FILL_HORIZONTAL | FILL_VERTICAL  #: Grow the horizontal and vertical size of the object if needed so it completely fills its container.
    VERTICAL = TOP | BOTTOM | CENTER_VERTICAL
    HORIZONTAL = LEFT | RIGHT | CENTER_HORIZONTAL


class LayoutParams(Enum):
    """
    LayoutParams are used by Room to tell their parents how they want to be laid out.

    This class has taken inspiration from android.view.ViewGroup.LayoutParams.
    """
    FILL_PARENT = auto()
    WRAP_CONTENT = auto()


class MeasureSpec(Enum):
    """
    A MeasureSpec is an enumeration used by :class:`MeasureParams`.
    It informs the child about the parent's layout decisions.

    This class has taken inspiration from android.view.View.MeasureSpec.
    """
    EXACTLY = auto()  #: The parent has determined an exact size for the child. The child is going to be given those
    # bounds regardless of how big it wants to be.
    AT_MOST = auto()  #: The child can be as large as it wants up to the specified size.
    UNSPECIFIED = auto()  #: The parent has not imposed any constraint on the child. It can be whatever size it wants.


class MeasureParams(object):
    """
    A MeasureParams encapsulates the layout requirements passed from parent to child.

    Each MeasureParams represents a requirement for either the width or the height.
    A MeasureParams is comprised of a size and a mode. A mode is a :class:`MeasureSpec` object.

    This class has taken inspiration from android.view.View.MeasureSpec.
    """

    def __init__(self, mode: MeasureSpec, value: int):
        """
        Constructor of MeasureParams.
        :param mode: a MeasureSpec
        :param value: an int
        """
        self.mode = mode
        self.value = value

    def __str__(self):
        return "%s, %s" % (self.mode, self.value)

    def exactly(self) -> 'MeasureParams':
        """
        Make another MeasureParams with mode set to MeasureSpec.EXACTLY.
        :return: a newly instanced MeasureParams with mode set to MeasureSpec.EXACTLY.
        """
        return MeasureParams(MeasureSpec.EXACTLY, self.value)

    def at_most(self) -> 'MeasureParams':
        """
        Make another MeasureParams with mode set to MeasureSpec.AT_MOST.
        :return: a newly instanced MeasureParams with mode set to MeasureSpec.AT_MOST.
        """
        return MeasureParams(MeasureSpec.AT_MOST, self.value)


class Room(object):
    """
    Room class is at the heart of Ice Emblem's engine.

    It provides a tree like data structure that can be run in a uniform way by the
    run_room function and allow to route events to registered callbacks or methods
    named like handle_videoresize.
    """

    def __init__(self, **kwargs):
        """
        Initializes a Room object. You can pass no argument and the defaults will be used.

        Parameters
        ----------

        fps: int, optional
            Sets the required framerate (defaults to 60)
        wait: bool, optional
            should we wait for events or keep drawing at max fps? (defaults to true)
        allowed_events: List[int], optional
            a list of pygame event types that can be processed by the room (defaults to keep the previous events)
        die_when_done: bool, optional
            when self.done is set to True the life-cycle of the room terminates with a call to self.end.
            This parameter determines whether this child should keep living or should die by removing itself from the
            tree (defaults to True)
        clear_screen: bool, optional
            color to fill the main window with. If None no clear is performed. (defaults to black (0, 0, 0))
        visible: bool, optional
            whether this room is visible or not (if it is blit on the parent) (defaults to True)
        layout_width: LayoutParams, optional
            (defaults to LayoutParams.WRAP_CONTENT)
        layout_height: LayoutParams, optional
            (defaults to LayoutParams.WRAP_CONTENT)
        layout_gravity: Gravity, optional
            (defaults to Gravity.NO_GRAVITY)
        layout_position: Tuple[int, int], optional
            (defaults to (0, 0))
        children: List[Room], optional
            the list of children (defaults to [])
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int], optional
            (defaults to 0)
        border: Union[int, Tuple[int, int], Tuple[int, int, int, int], optional
            (defaults to 0)
        margin: Union[int, Tuple[int, int], Tuple[int, int, int, int], optional
            (defaults to 0)
        bg_color: pygame.Color, optional
            (defaults to c.MENU_BG)
        bg_image: pygame.Surface, optional
            (defaults to None)
        bg_size: str, optional
            (defaults to 'contain')
        next: Room, optional
            When this room is done the next one will take its place. (defaults to None)
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.fps = kwargs.get('fps', display.fps)
        self.wait_prefer = self.wait = kwargs.get('wait', True)
        self.wait_valid = True
        self.allowed_events = kwargs.get('allowed_events', [])
        self.die_when_done = kwargs.get('die_when_done', True)
        self.clear_screen = kwargs.get('clear_screen', (0, 0, 0))

        self.parent = None
        self.done = False
        self.root = False
        self.valid = False
        self.visible = kwargs.get('visible', True)
        self.rect = pygame.Rect((0, 0), (0, 0))
        self.surface = pygame.Surface(self.rect.size)
        self.callbacks = {}
        self.next = kwargs.get('next', None)

        self.layout_width = kwargs.get('layout_width', LayoutParams.WRAP_CONTENT)
        self.layout_height = kwargs.get('layout_height', LayoutParams.WRAP_CONTENT)
        self.layout_gravity = kwargs.get('layout_gravity', Gravity.NO_GRAVITY)
        self.layout_position = kwargs.get('layout_position', (0, 0))
        self.layout_valid = False

        self.children = []
        self.add_children(*kwargs.get('children', []))

        self.padding = NESW(kwargs.get('padding', 0))
        self.border = NESW(kwargs.get('border', 0))
        self.margin = NESW(kwargs.get('margin', 0))

        self.bg_color = kwargs.get('bg_color', c.MENU_BG)
        self.bg_image = kwargs.get('bg_image', None)
        self.bg_size = kwargs.get('bg_size', 'contain')  # Possible values: 'contain', 'cover', (int, int)
        self._bg_image_size = None

    def __str__(self):
        return self.logger.name

    @property
    def layout_wh(self) -> Tuple[int, int]:
        """
        Layout's width and height.
        """
        return self.layout_width, self.layout_height

    @property
    def measured_size(self) -> Tuple[int, int]:
        """
        Measured width and height.
        """
        return self.measured_width, self.measured_height

    def mark_done(self, *_) -> None:
        """
        Mark this Room as done.
        """
        self.done = True

    def children_done(self) -> bool:
        """
        Returns True if all children are done. If there are no children returns True (like an universal quantifier).
        """
        for child in self.children:
            if not child.done:
                return False
        return True

    def prepare_child(self, child: 'Room') -> None:
        """
        Called before adding a child to the tree.
        :param child: the Room to prepare before being added to the tree to ensure it is consistent
        """
        child.parent = self
        child.logger = self.logger.getChild(child.__class__.__name__)
        child.begin()
        for grandchild in child.children:
            child.prepare_child(grandchild)
        return child

    def add_children(self, *children) -> None:
        """
        Adds many children to the tree.
        :param children: Room children to add to the tree.
        """
        for child in children:
            self.prepare_child(child)
        self.children.extend(children)
        self.layout_request()
        self.invalidate()

    def add_child(self, child: 'Room') -> None:
        """
        Adds a child to the tree.
        :param child: Room child to add to the tree.
        """
        self.add_children(child)

    def remove_child(self, child: 'Room') -> None:
        """
        Removes a child from the tree.
        :param child: which child to remove
        :raises ValueError when the child is not part of the tree
        """
        self.children.remove(child)
        child.parent = None
        child.logger = logging.getLogger(child.__class__.__name__)
        self.layout_request()
        self.invalidate()
        self.wait_invalidate()

    def invalidate(self) -> None:
        """
        Bottom-top traverse of the tree. Every parent is invalidated up until the root.

        The draw method will be called at next frame if the Room is invalid.
        """
        self.valid = False
        node = self.parent
        while node and node.valid:
            node.valid = False
            node = node.parent
        self.logger.debug("Invalidated")

    def layout_request(self) -> None:
        """
        Bottom-top traverse of the tree. Every parent is invalidated up until the root.

        The room_layout function will be called on the root Room before next frame.
        """
        node = self
        while node and node.layout_valid:
            node.layout_valid = False
            node = node.parent
        self.logger.debug("Layout requested")

    def wait_invalidate(self) -> None:
        """
        Bottom-top traverse of the tree. Every parent is invalidated up until the root.

        The wait_update method of the root Room will be called before next frame.
        """
        if self.wait_valid:
            self.logger.debug("Wait invalidated")
        self.wait_valid = False
        node = self.parent
        while node and node.wait_valid:
            node.wait_valid = False
            node = node.parent

    def wait_set(self, wait: bool) -> None:
        """
        Sets wait_prefer and invalidates wait. When wait is invalidated self.wait_update gets called.
        :param wait: Wether this Room wants the wait behaviour provided by pygame.event.wait or the behaviour of
        pygame.event.get
        """
        if wait != self.wait_prefer:
            self.wait_prefer = wait
            self.wait_invalidate()

    def wait_update(self) -> None:
        """
        Updates self.wait by recurring over all children.
        """
        if self.wait_valid:
            return self.wait
        self.wait = self.wait_prefer
        for child in self.children:
            self.wait = self.wait and child.wait_update()
        self.wait_valid = True
        self.logger.debug("Wait updated: %s", self.wait)
        return self.wait

    def measure(self, spec_width: MeasureParams, spec_height: MeasureParams) -> None:
        """
        Top-down traversal of the tree. The parent asks its children to measure their size.
        The measured size should not exceed max_width and max_height otherwise the parent may clip the child.
        """
        for child in self.children:
            child.measure(spec_width.at_most(), spec_height.at_most())
        self.resolve_measure(spec_width, spec_height, self.rect.w, self.rect.h)

    def resolve_measure(self, spec_width: MeasureParams, spec_height: MeasureParams, content_width: int,
                        content_height: int) -> None:
        """
        Handy method that implements the basic logic of MeasureSpec.

        Sets self.measured_width and self.measured_height.
        :param spec_width:
        :param spec_height:
        :param content_width:
        :param content_height:
        """
        if spec_width.mode == MeasureSpec.EXACTLY:
            self.measured_width = spec_width.value
        else:
            if self.layout_width == LayoutParams.FILL_PARENT:
                self.measured_width = spec_width.value
            elif self.layout_width == LayoutParams.WRAP_CONTENT:
                self.measured_width = min(spec_width.value, content_width)
            else:
                self.measured_width = min(spec_width.value, self.layout_width)

        if spec_height.mode == MeasureSpec.EXACTLY:
            self.measured_height = spec_height.value
        else:
            if self.layout_height == LayoutParams.FILL_PARENT:
                self.measured_height = spec_height.value
            elif self.layout_height == LayoutParams.WRAP_CONTENT:
                self.measured_height = min(spec_height.value, content_height)
            else:
                self.measured_height = min(spec_height.value, self.layout_height)
        self.logger.debug("W: (%s) -> %s; H: (%s) -> %s", spec_width, self.measured_width, spec_height,
                          self.measured_height)

    def layout(self, rect: pygame.Rect) -> None:
        """
        Top-down traversal of the tree. The parent positions its children. This method will be called after measure.

        This method should be redefined by subclasses to enforce their layout.
        :param rect: contains the position and size this child should use.
        """
        for child in self.children:
            child.layout(pygame.Rect(child.layout_position, child.measured_size))
        self.resolve_layout(rect)

    def resolve_layout(self, rect: pygame.Rect) -> None:
        """
        An handy method to finalize layout.
        :param rect: contains the position and size this child should use.
        """
        self.rect.topleft = rect.topleft
        self.resize(rect.size)
        self.layout_valid = True
        self.logger.debug("layout gravity: %s; rect: %s", self.layout_gravity, self.rect)

    def resize(self, size: Tuple[int, int]) -> None:
        """
        If size is different from self.rect.size then resizes this.surface, calls self.fill and self.invalidate.
        :param size:
        :return:
        """
        if self.rect.size != size:
            self.rect.size = size
            self.surface = pygame.Surface(self.rect.size)
            self.fill()
            self.invalidate()

    def handle_videoresize(self, _event: pygame.event.EventType) -> None:
        """
        Request new layout on resize event.
        :param _event: useless
        """
        self.layout_request()

    def toggle_visibility(self) -> None:
        """
        Toggles visibility of this Room.

        If a Room is invisible all of it'ssubtree will not be rendered.
        """
        self.visible = not self.visible
        self.invalidate()

    def begin_children(self) -> None:
        """
        Recursively begin all children's life-cycle.
        """
        for child in self.children:
            child.begin()

    def begin(self) -> None:
        """
        Begins this Room's life-cycle. Called by run_room or when added as a child to another running Room.
        """
        self.begin_children()
        self.invalidate()
        self.wait_invalidate()
        self.logger.debug("begin")

    def loop(self, _events: List[pygame.event.EventType], dt: int) -> None:
        """
        Called every frame.
        :param _events: a list of pygame.event.Event
        :param dt: number of elapsed milliseconds since last frame
        """
        for child in self.children:
            child.loop(_events, dt)
            if child.done and child.die_when_done:
                child.end()

    def draw(self) -> None:
        """
        Draw on self.surface. Called every frame if self.valid is false.

        Use self.invalidate() to mark invalid and allow this method to be called at next frame.
        """
        self.draw_children()
        self.valid = True

    def draw_children(self) -> None:
        """
        Draw children recursively by calling their draw method if they are visible and invalid.
        """
        for child in self.children:
            if child.visible:
                if not child.valid:
                    child.draw()
                self.surface.blit(child.surface, child.rect)

    def fill(self, area=None) -> None:
        """
        Fill self.surface with self.bg_color and/or with self.bg_image.

        This method is called before draw. and is generally avoided because filling a surface and drawing from scratch
        is pretty expensive.
        :param area: if not None restricts the fill to an area.
        """
        if self.bg_color:
            if area:
                surf = pygame.Surface(area.size)
                surf.fill(self.bg_color)
                self.surface.blit(surf, area)
            else:
                self.surface.fill(self.bg_color)
        if self.bg_image:
            resized = self.bg_image_resized()
            pos = resized.get_rect(center=self.rect.center).move(-self.rect.x, -self.rect.y)
            self.surface.blit(resized, pos, area)

    def fill_recursive(self) -> None:
        """
        Fill every surface recursively.
        """
        self.fill()
        self.valid = False
        for child in self.children:
            child.fill_recursive()

    def bg_image_resized(self) -> None:
        """
        Resize self.bg_image so that it can fit self.surface respecting the type of resize specified by self.bg_size.
        """
        if self.bg_size == 'contain':
            new_size = utils.resize_keep_ratio(self.bg_image.get_size(), self.rect.size)
        elif self.bg_size == 'cover':
            new_size = utils.resize_cover(self.bg_image.get_size(), self.rect.size)
        else:
            new_size = (int(self.bg_size[0] / 100 * self.rect.w), int(self.bg_size[1] / 100 * self.rect.h))
        if new_size == self._bg_image_size:
            return self._bg_image_resized
        self._bg_image_resized = pygame.transform.smoothscale(self.bg_image, new_size)
        self._bg_image_size = self.rect.size
        return self._bg_image_resized

    def end_children(self) -> None:
        """
        If parent dies all children die with him.
        """
        for child in self.children:
            child.end()

    def end(self) -> None:
        """
        Ends life-cycle of this Room. Unregisters all callbacks and removes himself from parent if self.die_when_done is
        true.
        """
        for event_type in self.callbacks:
            if event_type >= p.USEREVENT and self.callbacks[event_type]:
                events.stop_timer(event_type)
        self.logger.debug("end")
        self.end_children()
        if self.parent:
            if self.next:
                self.parent.add_child(self.next)
            if self.die_when_done:
                self.parent.remove_child(self)

    def process_events(self, _events):
        """
        Dispatches an event to registered callbacks or to methods named
        like handle_mousebuttondown.
        """
        processed = False
        for child in self.children:
            processed = processed or child.process_events(_events)
        if processed:
            return
        for event in _events:
            if event.type in self.callbacks:
                for callback in self.callbacks[event.type]:
                    processed = processed or callback(event)
            method = getattr(self, 'handle_' + pygame.event.event_name(event.type).lower(), None)
            if method is not None:
                processed = processed or method(event)
        return processed

    def register(self, event_type: int, callback: Callable) -> None:
        """
        Bind a callback function to an event type.
        """
        if event_type in self.callbacks:
            if callback not in self.callbacks[event_type]:
                self.callbacks[event_type].append(callback)
        else:
            self.callbacks[event_type] = [callback]
        self.logger.debug('registered %s -> %s', pygame.event.event_name(event_type), callback)

    def unregister(self, event_type: int, callback: Callable = None):
        """
        Unregister the latest or the specified callback function from event_type.
        """
        if callback:
            if callback in self.callbacks[event_type]:
                self.callbacks[event_type].remove(callback)
        elif len(self.callbacks[event_type]) > 0:
            self.callbacks[event_type].pop()
        self.logger.debug('unregistered %s -> %s', pygame.event.event_name(event_type), callback)

    def set_timeout(self, time: int, callback: Callable) -> int:
        """
        This method is kind of inspired from JS's SetTimeout. It calls callback only once approximately after time
        milliseconds. When this room ends the timer is cancelled too.
        :param time: time in milliseconds
        :param callback: callback function
        :return: an int between pygame.USEREVENT and pygame.NUMEVENTS which can be used to stop the timer by calling
        Room.unregister
        """
        event_type = events.new_timer(time)

        def callme(_event: int) -> bool:
            events.stop_timer(event_type)
            self.unregister(event_type, callme)
            return callback(_event)

        self.register(event_type, callme)
        return event_type

    def set_interval(self, time: int, callback: Callable) -> int:
        """
        This method is kind of inspired from JS's setInterval.

        It calls callback every time milliseconds until this room ends or Room.unregister is called.
        :param time: time in milliseconds
        :param callback: callback function
        :return: an int between pygame.USEREVENT and pygame.NUMEVENTS which can be used to stop the timer by calling
        Room.unregister
        """
        event_type = events.new_timer(time)
        self.register(event_type, callback)
        return event_type

    def bind_keys(self, keys, callback):
        """
        Binds a keyboard key to a callback function.
        """

        def f(event):
            for key in keys:
                if event.key == key:
                    callback(self)

        self.register(p.KEYDOWN, f)

    def bind_click(self, mouse_buttons, callback, area=None, inside=True):
        """
        Binds a mouse button to a callback functions.

        The call to the callback can be filtered by area (pygame.Rect) and specify if
        the event position must be inside or outside that area.
        """

        def f(event):
            for mouse_button in mouse_buttons:
                if event.button == mouse_button:
                    if area is None:
                        callback(self)
                    else:
                        collide = area.collidepoint(event.pos)
                        if inside and collide:
                            callback(self)
                        elif not inside and not collide:
                            callback(self)

        self.register(p.MOUSEBUTTONDOWN, f)

    def global_coord(self, coord):
        """
        Translates local coordinates to global coordinates.

        The inverse method is self.local_coord
        :param coord: local coordinates (relative to the parent's top-left corner)
        :return: global coordinates (relative to the window's top-left corner)
        """
        node = self
        while node:
            coord = coord[0] + node.rect.x, coord[1] + node.rect.y
            node = node.parent
        return coord

    def global_pos(self) -> Tuple[int, int]:
        """
        Returns the position relative to the top-left corner of the window.
        :return: global position
        """
        return self.global_coord((0, 0))

    def global_rect(self):
        """
        Returns global rect, that is a rect having self.flobal_pos() as topleft and self.rect.size as size.
        :return: global rect
        """
        return pygame.Rect(self.global_pos(), self.rect.size)

    def local_coord(self, coord: Tuple[int, int]) -> Tuple[int, int]:
        """
        Translates global coordinates to local coordinates.

        The inverse method is self.global_coord
        :param coord: global coordinates (relative to the window's top-left corner)
        :return: local coordinates (relative to the parent's top-left corner)
        """
        node = self
        while node:
            coord = coord[0] - node.rect.x, coord[1] - node.rect.y
            node = node.parent
        return coord


class RunRoomAsRoot(Room):
    def __init__(self, room, **kwargs):
        super().__init__(**kwargs)
        self.room = room

    def begin(self):
        super().begin()
        run_room(self.room)
        self.done = True


class RoomStop(Exception):
    """
    Exception used to interrupt abruptly the execution of currently running Rooms.
    """
    pass


def layout_room(room: Room) -> None:
    """
    Layout the root Room.
    :param room: the root Room
    """
    if Gravity.FILL_HORIZONTAL in room.layout_gravity:
        spec_width = MeasureParams(MeasureSpec.EXACTLY, display.get_width())
    else:
        spec_width = MeasureParams(MeasureSpec.AT_MOST, display.get_width())
    if Gravity.FILL_VERTICAL in room.layout_gravity:
        spec_height = MeasureParams(MeasureSpec.EXACTLY, display.get_height())
    else:
        spec_height = MeasureParams(MeasureSpec.AT_MOST, display.get_height())
    room.measure(spec_width, spec_height)

    rect = pygame.Rect((0, 0), room.measured_size)

    if room.layout_gravity == Gravity.NO_GRAVITY:
        rect.center = display.get_rect().center

    if Gravity.LEFT in room.layout_gravity:
        rect.left = 0
    elif Gravity.RIGHT in room.layout_gravity:
        rect.right = display.get_width()
    elif Gravity.CENTER_HORIZONTAL in room.layout_gravity:
        rect.centerx = display.get_width() // 2

    if Gravity.TOP in room.layout_gravity:
        rect.top = 0
    elif Gravity.BOTTOM in room.layout_gravity:
        rect.bottom = display.get_height()
    elif Gravity.CENTER_VERTICAL in room.layout_gravity:
        rect.centery = display.get_height() // 2

    room.layout(rect)


def draw_room(room: Room, first_draw=False):
    """
    Draws the root Room.
    :param room: the room to draw.
    :param first_draw: True if it's the first frame.
    """
    if room.clear_screen:
        display.window.fill(room.clear_screen)
    if not room.layout_valid:
        layout_room(room)
    if first_draw:
        room.fill_recursive()
    if not room.valid:
        room.draw()
    display.window.blit(room.surface, room.rect)
    display.draw_fps()
    display.flip()


def generic_event_handler(_events: List[pygame.event.EventType]) -> None:
    """
    Handle common events.
    :param _events:
    :return:
    """
    for event in _events:
        if event.type == pygame.QUIT:
            utils.return_to_os()
        if event.type == pygame.VIDEORESIZE:
            display.handle_videoresize(event)


def run_room(room: Room) -> None:
    """
    Runs a Room.
    :param room: root Room
    """
    allowed_events = list(events.get_allowed())
    if room.allowed_events:
        events.set_allowed(room.allowed_events)
    room.root = True
    room.done = False
    room.valid = False
    room.layout_valid = False
    room.begin()
    draw_room(room, first_draw=True)
    dt = display.tick(room.fps)

    while not room.done:
        if not room.wait_valid:
            room.wait_update()
        if room.wait and not pygame.event.peek(list(events.get_allowed())):
            _events = [pygame.event.wait()]
        else:
            _events = pygame.event.get()
        generic_event_handler(_events)
        room.process_events(_events)
        room.loop(_events, dt)
        draw_room(room)
        dt = display.tick(room.fps)

    room.end()
    if room.allowed_events:
        events.set_allowed(allowed_events)
    room.root = False


def run(first_room):
    """
    Runs the first root room and keeps going until they keep providing a next room.
    :param first_room: the first Room to execute.
    """
    room = first_room
    try:
        while room:
            run_room(room)
            room = room.next
    except RoomStop:
        room.root = False


def stop() -> None:
    """
    Stops all running room.
    """
    raise RoomStop()
