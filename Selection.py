import math
import tkinter as tk
from abc import abstractmethod
from PIL import Image
from utils import TwoDPoint, Coordinates


class SelectionObject:
    def __init__(self, canvas: tk.Canvas, container, width, height, img, select_opts, coords=None):
        self.canvas = canvas
        self.container = container
        self.img = img
        self.img_width = width
        self.img_height = height
        self.select_opts = select_opts
        self.rects = None
        self.module_rects = ()

        if coords is None:
            self.start = TwoDPoint(0, 0)
            self.end = TwoDPoint(self.img_width, self.img_height)
        else:
            self.start = TwoDPoint(coords[0], coords[1])
            self.end = TwoDPoint(coords[2], coords[3])

        self.coordinates = Coordinates((self.start.x, self.start.y), (self.end.x, self.start.y),
                                       (self.start.x, self.end.y), (self.end.x, self.end.y))

        self.canvas.bind("<Double-Button-1>", self._clear)

    def _get_coords(self, start, end, pan=(0, 0)):
        """ Determine coords of a polygon defined by the start and
            end points one of the diagonals of a rectangular area.
        """
        if start is None:
            return (None, None, None, None)

        clamp = lambda n, minn, maxn: max(min(maxn, n), minn)

        box_image = self.canvas.coords(self.container)  # get image area
        box_img_int = tuple(map(int, box_image))
        min_w = box_img_int[0]
        min_h = box_img_int[1]
        max_w = box_img_int[2]
        max_h = box_img_int[3]
        s0 = clamp(start[0] + pan[0], min_w, max_w - 1)
        e0 = clamp(end[0] + pan[0], min_w, max_w - 1)
        s1 = clamp(start[1] + pan[1], min_h, max_h - 1)
        e1 = clamp(end[1] + pan[1], min_h, max_h - 1)

        return ((min((s0, e0)), min((s1, e1)),
                 max((s0, e0)), max((s1, e1))))

    def _hide(self):
        for rect in self.rects:
            self.canvas.itemconfigure(rect, state=tk.HIDDEN)
        for mod in self.module_rects:
            self.canvas.itemconfigure(mod, state=tk.HIDDEN)

    def _clear(self, event=None):
        self._hide()
        self.start = TwoDPoint(0, 0)
        self.end = TwoDPoint(self.img_width, self.img_height)

    def hide_module_rects(self):
        for mod in self.module_rects:
            self.canvas.itemconfigure(mod, state=tk.HIDDEN)

    def _show(self):
        for r in self.rects:  # Make sure all are now visible.
            self.canvas.itemconfigure(r, state=tk.NORMAL)

    def _coord_mapping(self, x, y, box): #screen to img
        og_h = self.img_height
        og_w = self.img_width
        h_ratio = og_h / (box[3] - box[1])
        w_ratio = og_w / (box[2] - box[0])
        coord = ((x - box[0]) * w_ratio, (y - box[1]) * h_ratio)

        return tuple(map(lambda n: math.ceil(n), coord))

    def _img_to_screen(self, xx, yy, box):
        og_h = self.img_height
        og_w = self.img_width
        h_ratio = og_h / (box[3] - box[1])
        w_ratio = og_w / (box[2] - box[0])
        coord = ((xx / w_ratio) + box[0], (yy / h_ratio) + box[1])

        return tuple(map(lambda n: math.ceil(n), coord))

    def update(self, start, end):
        pan = (self.canvas.canvasx(0), self.canvas.canvasy(0))
        # Current extrema of inner and outer rectangles.
        imin_x, imin_y, imax_x, imax_y = self._get_coords(start, end, pan)
        if not all((imin_x, imin_y, imax_x, imax_y)):
            return None

        box_image = self.canvas.coords(self.container)  # get image area
        box_img_int = tuple(map(int, box_image))

        # # Get scroll region box
        omin_x, omin_y, omax_x, omax_y = box_img_int
        up_coord = (*self._coord_mapping(imin_x, imin_y, box_img_int),
                    *self._coord_mapping(imax_x, imax_y, box_img_int))
        # print("COORD ---- " + str(up_coord))
        self.coordinates = ((up_coord[0], up_coord[1]), (up_coord[2], up_coord[1]),
                            (up_coord[2], up_coord[3]), (up_coord[0], up_coord[3]))

        self.start = TwoDPoint(up_coord[0], up_coord[1])
        self.end = TwoDPoint(up_coord[2], up_coord[3])

        self._update_rects(imin_x, imin_y, imax_x, imax_y, omin_x, omin_y, omax_x, omax_y)

        for rect in self.rects:  # Make sure all are now visible.
            self.canvas.itemconfigure(rect, state=tk.NORMAL)

        self._show()

    def rect_module(self, a, b, c, d):
        self.hide_module_rects()
        select_opts = dict( width=2, fill='red', state=tk.NORMAL)
        print(a, b, c, d)
        box_image = self.canvas.coords(self.container)  # get image area
        box_img_int = tuple(map(int, box_image))
        a = self._img_to_screen(a[0], a[1], box_img_int)
        b = self._img_to_screen(b[0], b[1], box_img_int)
        c = self._img_to_screen(c[0], c[1], box_img_int)
        d = self._img_to_screen(d[0], d[1], box_img_int)
        print(a,b,c,d)

        self.module_rects = (self.canvas.create_line(a[0],a[1],b[0],b[1], **select_opts, tags=("line",)),  #a-b
                             self.canvas.create_line(b[0], b[1], c[0], c[1], **select_opts, tags=("line",)),  #b-c
                             self.canvas.create_line(c[0], c[1], d[0], d[1], **select_opts, tags=("line",)),  #c-d
                             self.canvas.create_line(d[0], d[1], a[0], a[1], **select_opts, tags=("line",)),  #d-a
                            )

    @abstractmethod
    def _update_rects(self, imin_x, imin_y, imax_x, imax_y, omin_x, omin_y, omax_x, omax_y):
        pass

    @abstractmethod
    def matrix(self, p1, p2, p3, p4):
        pass

    @abstractmethod
    def get_mat(self, img, coord: tuple[TwoDPoint, ...], deltax, deltay, mss= None):
        pass

    @abstractmethod
    def tile_image(self, tile: Image.Image, coords=None, xrepeat=3, yrepeat=3):
        pass