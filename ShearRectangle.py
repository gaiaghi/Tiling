import tkinter as tk
import math
import numpy as np
from numpy.linalg import norm
from Selection import SelectionObject
from Selection import TwoDPoint, Coordinates

# SELECT_OPTS = dict(dash=(2, 2),  fill='white')
SELECT_OPTS = dict(dash=(2, 2), stipple='gray25', fill='white',
                   outline='')
MIN_DIST = 9


def point_selector(func1, func2):
    return lambda a: func1(a[a[:, 0] == func2(a[:, 0])], 0)


class ShearRectangle(SelectionObject):
    """ Widget to display a sheared rectangular area on given canvas defined by two points
        representing its diagonal + user edit.
    """

    def __init__(self, canvas, container, width, height, select_opts=None, coords=None):
        if select_opts is None:
            select_opts = SELECT_OPTS

        super(ShearRectangle, self).__init__(canvas, container, width, height, select_opts, coords)

        self.draft = None
        self.moving_start = None
        self.selected = None
        self.direction = 0

        self.coordinates = Coordinates((self.start.x, self.start.y), (self.end.x, self.start.y),
                                       (self.start.x, self.end.y), (self.end.x, self.end.y))

        # Options for areas outside rectanglar selection.
        select_opts1 = self.select_opts.copy()  # Avoid modifying passed argument.
        select_opts1.update(state=tk.HIDDEN)  # Hide initially.
        # Separate options for area inside rectanglar selection.
        # select_opts2 = dict(dash=(2, 2), width=2, fill='white', state=tk.HIDDEN)
        # TODO outside rects

        self.rect_setup()

        if coords is not None:
            self.update(self.start, self.end)

        self.canvas.bind("<Shift-Button-1>", self.click_callback_x)
        self.canvas.bind("<Shift-B1-Motion>", self.move_line)
        self.canvas.bind("<Shift-ButtonRelease-1>", self.quit)
        self.canvas.bind("<Control-Button-1>", self.click_callback_y)
        self.canvas.bind("<Control-B1-Motion>", self.move_line)
        self.canvas.bind("<Control-ButtonRelease-1>", self.quit)

    def click_callback_x(self, event):  #TODO change name
        self.direction = 0
        self._on_click(event)

    def click_callback_y(self, event):  # TODO change name
        self.direction = 1
        self._on_click(event)

    def _on_click(self, event):
        """
        Finds the closest side of the parallelogram to the user click coordinates.
        :param event: click
        :return:
        """
        self.moving_start = (event.x, event.y)
        self.draft = tk.Canvas(self.canvas)  # if w is deleted, the draft is deleted
        self.draft.delete("all")  # if you use the fake canvas for other uses
        concerned = self.canvas.find_withtag("line")  # what you want
        for obj in concerned:
            config = {opt: self.canvas.itemcget(obj, opt) for opt in self.canvas.itemconfig(obj)}
            config["tags"] = str(obj)  # I can retrieve the ID in "w" later with this trick
            self.draft.create_line(*self.canvas.coords(obj), **config)

        # adjust coordinates according to user panning
        pan = (self.canvas.canvasx(0), self.canvas.canvasy(0))
        element = self.draft.find_closest(self.draft.canvasx(event.x + pan[0]), self.draft.canvasy(event.y + pan[1]))
        if not element:
            self.draft = None
            return
        coords = self.draft.coords(element)  # Current extrema of inner and outer rectangles.
        # line ends
        p1 = np.asarray((coords[0], coords[1]))
        p2 = np.asarray((coords[2], coords[3]))
        dist = norm(np.cross(p2 - p1, p1 - np.asarray((event.x + pan[0], event.y + pan[1])))) / norm(p2 - p1)

        if dist < MIN_DIST:
            self.selected = element[0]

    def move_line(self, event):
        if self.selected:
            box_image = self.canvas.coords(self.container)  # get image area
            box_img_int = tuple(map(int, box_image))
            omin_x, omin_y, omax_x, omax_y = box_img_int

            # retrieve selected element
            element = self.rects[self.selected - 1]
            opp = self.rects[(self.selected + 1) % 4]
            # calculate distance moved from last position
            dx, dy = event.x - self.moving_start[0], event.y - self.moving_start[1]
            current = self.canvas.coords(element)
            opposite = self.canvas.coords(opp)

            miny = min(current[1], current[3])
            minx = min(current[0], current[2])
            maxy = max(current[1], current[3])
            maxx = max(current[0], current[2])

            # do not exceed og image coordinates:
            if dx < 0 and minx + dx < omin_x:
                dx = minx - omin_x
            if dy < 0 and miny + dy < omin_y:
                dy = miny - omin_y
            if dx > 0 and maxx + dx > omax_x:
                dx = omax_x - maxx
            if dy > 0 and maxy + dy > omax_y:
                dy = omax_y - maxy

            # do not flip
            side = (opposite[2] - opposite[0]) * (current[1] - opposite[1]) - (opposite[3] - opposite[1]) * (
                    current[0] - opposite[0])

            if side < 0:
                if self.selected == 1 and dy > 0:
                    dy = 0
                if self.selected == 3 and dy < 0:
                    dy = 0
                if self.selected == 2 and dx < 0:
                    dx = 0
                if self.selected == 4 and dx > 0:
                    dx = 0

            if self.direction == 0:
                dy = 0
            if self.direction == 1:
                dx = 0

            # move the selected item
            self.canvas.move(element, dx, dy)
            # update last position
            self.moving_start = (event.x, event.y)
            # line indexes to update
            delta_1 = (((self.selected - 1) - 1) % 4) - (self.selected - 1)
            delta_2 = (((self.selected - 1) + 1) % 4) - (self.selected - 1)
            index1 = element + delta_1
            index2 = element + delta_2
            ax, ay, bx, by = self.canvas.coords(element)
            x1, y1, _, _ = self.canvas.coords(index1)
            _, _, x2, y2 = self.canvas.coords(index2)
            self.canvas.coords(index1, x1, y1, ax, ay)
            self.canvas.coords(index2, bx, by, x2, y2)
            # self.coordinates = ((ax, ay), (bx, by), (x2, y2), (x1, y1))
            self._update_coordinates()

            self._show()

    def quit(self, event):
        self.selected = None

    def _update_rects(self, imin_x, imin_y, imax_x, imax_y, omin_x, omin_y, omax_x, omax_y):
        # Update coords of all rectangles based on these extrema.
        self.canvas.coords(self.rects[0], imin_x, imin_y, imax_x, imin_y),
        self.canvas.coords(self.rects[1], imax_x, imin_y, imax_x, imax_y),
        self.canvas.coords(self.rects[2], imax_x, imax_y, imin_x, imax_y),
        self.canvas.coords(self.rects[3], imin_x, imax_y, imin_x, imin_y)

        self._update_coordinates()

    def rect_setup(self):
        select_opts2 = dict(dash=(2, 2), width=2, fill='white', state=tk.HIDDEN)
        imin_x, imin_y, imax_x, imax_y = 0, 0, 1, 1
        self.rects = (self.canvas.create_line(imin_x, imin_y, imax_x, imin_y, **select_opts2, tags=("line",)),  #a-b
                      self.canvas.create_line(imax_x, imin_y, imax_x, imax_y, **select_opts2, tags=("line",)),  #b-c
                      self.canvas.create_line(imax_x, imax_y, imin_x, imax_y, **select_opts2, tags=("line",)),  #c-d
                      self.canvas.create_line(imin_x, imax_y, imin_x, imin_y, **select_opts2, tags=("line",)),  #d-a
                      )

    def _update_coordinates(self):
        box_image = self.canvas.coords(self.container)  # get image area
        box_img_int = tuple(map(int, box_image))

        self.coordinates = (
            self._coord_mapping(self.canvas.coords(self.rects[0])[0], self.canvas.coords(self.rects[0])[1],
                                box_img_int),
            self._coord_mapping(self.canvas.coords(self.rects[1])[0], self.canvas.coords(self.rects[1])[1],
                                box_img_int),
            self._coord_mapping(self.canvas.coords(self.rects[2])[0], self.canvas.coords(self.rects[2])[1],
                                box_img_int),
            self._coord_mapping(self.canvas.coords(self.rects[3])[0], self.canvas.coords(self.rects[3])[1],
                                box_img_int))

        self.start = TwoDPoint(self.coordinates[0][0], self.coordinates[0][1])
        self.end = TwoDPoint(self.coordinates[2][0], self.coordinates[2][1])
