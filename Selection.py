import math
import tkinter as tk
from abc import abstractmethod


class TwoDPoint(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __getitem__(self, idx):
        if idx == 0:
            return self.x
        else:
            return self.y

    def __setitem__(self, idx, val):
        if idx == 0:
            self.x = val
        if idx == 1:
            self.y = val

    def __str__(self):
        return "(" + str(self.x) + "," + str(self.y) + ")"


class Coordinates:
    def __init__(self, a: tuple[int, int], b: tuple[int, int], c: tuple[int, int], d: tuple[int, int]):
        self.A = TwoDPoint(*a)
        self.B = TwoDPoint(*b)
        self.C = TwoDPoint(*c)
        self.D = TwoDPoint(*d)

    def set_a(self, a):
        self.A = a

    def set_b(self, b):
        self.B = b

    def set_c(self, c):
        self.C = c

    def set_d(self, d):
        self.D = d

    def __str__(self):
        return "[" + str(self.A) + "," + str(self.B) + "," + str(self.C) + "," + str(self.D) + "]"


class SelectionObject:
    def __init__(self, canvas, container, width, height, select_opts, coords=None):
        self.canvas = canvas
        self.container = container
        self.img_width = width
        self.img_height = height
        self.select_opts = select_opts
        self.rects = None

        if coords is None:
            self.start = TwoDPoint(0, 0)
            self.end = TwoDPoint(self.img_width, self.img_height)
        else:
            self.start = TwoDPoint(coords[0], coords[1])
            self.end = TwoDPoint(coords[2], coords[3])

        self.canvas.bind("<Double-Button-1>", self._clear)

    def _get_coords(self, start, end, pan=(0, 0)):
        """ Determine coords of a polygon defined by the start and
            end points one of the diagonals of a rectangular area.
        """
        # print(start)
        if start is None:
            return (None, None, None, None)

        clamp = lambda n, minn, maxn: max(min(maxn, n), minn)

        box_image = self.canvas.coords(self.container)  # get image area
        box_img_int = tuple(map(int, box_image))
        min_w = box_img_int[0]
        min_h = box_img_int[1]
        max_w = box_img_int[2]
        max_h = box_img_int[3]
        # print("min_h: " + str(min_h) + ", max_h: " + str(max_h))
        # print("min_w: " + str(min_w) + ", max_w: " + str(max_w))
        s0 = clamp(start[0] + pan[0], min_w, max_w - 1)
        e0 = clamp(end[0] + pan[0], min_w, max_w - 1)
        s1 = clamp(start[1] + pan[1], min_h, max_h - 1)
        e1 = clamp(end[1] + pan[1], min_h, max_h - 1)

        return ((min((s0, e0)), min((s1, e1)),
                 max((s0, e0)), max((s1, e1))))

    def _hide(self):
        for rect in self.rects:
            self.canvas.itemconfigure(rect, state=tk.HIDDEN)

    def _clear(self, event=None):
        self._hide()
        self.start = TwoDPoint(0, 0)
        self.end = TwoDPoint(self.img_width, self.img_height)
        # self.draft = None #TODO override in shear

    def _show(self):
        for r in self.rects:  # Make sure all are now visible.
            self.canvas.itemconfigure(r, state=tk.NORMAL)

    def _coord_mapping(self, x, y, box):
        og_h = self.img_height
        og_w = self.img_width
        h_ratio = og_h / (box[3] - box[1])
        w_ratio = og_w / (box[2] - box[0])
        coord = ((x - box[0]) * w_ratio, (y - box[1]) * h_ratio)

        return tuple(map(lambda n: math.ceil(n), coord))

    def update(self, start, end):
        pan = (self.canvas.canvasx(0), self.canvas.canvasy(0))
        # Current extrema of inner and outer rectangles.
        imin_x, imin_y, imax_x, imax_y = self._get_coords(start, end, pan)
        if not all((imin_x, imin_y, imax_x, imax_y)):
            return None
        # TODO controllo coordinate con pan che non funzionano (_get_coords)

        box_image = self.canvas.coords(self.container)  # get image area
        box_img_int = tuple(map(int, box_image))

        # # Get scroll region box
        omin_x, omin_y, omax_x, omax_y = box_img_int
        up_coord = (*self._coord_mapping(imin_x, imin_y, box_img_int),
                    *self._coord_mapping(imax_x, imax_y, box_img_int))
        print("COORD ---- " + str(up_coord))

        self.start = TwoDPoint(up_coord[0], up_coord[1])
        self.end = TwoDPoint(up_coord[2], up_coord[3])

        self._update_rects(imin_x, imin_y, imax_x, imax_y, omin_x, omin_y, omax_x, omax_y)

        for rect in self.rects:  # Make sure all are now visible.
            self.canvas.itemconfigure(rect, state=tk.NORMAL)

        self._show()

    @abstractmethod
    def _update_rects(self, imin_x, imin_y, imax_x, imax_y, omin_x, omin_y, omax_x, omax_y):
        pass
