import tkinter as tk
import math
import numpy as np
from numpy.linalg import norm

# SELECT_OPTS = dict(dash=(2, 2),  fill='white')
SELECT_OPTS = dict(dash=(2, 2), stipple='gray25', fill='white',
                   outline='')
MIN_DIST = 9


class Coordinates:
    def __init__(self, a, b, c, d):
        self.A = a
        self.B = b
        self.C = c
        self.D = d

    def set_A(self, a):
        self.A = a

    def set_B(self, b):
        self.B = b

    def set_C(self, c):
        self.C = c

    def set_D(self, d):
        self.D = d


class ShearRectangle:
    """ Widget to display a sheared rectangular area on given canvas defined by two points
        representing its diagonal + user edit.
    """

    def __init__(self, canvas, container, width, height, coords=None):
        # Create attributes needed to display selection.
        self.moving_start = None
        self.canvas = canvas
        self.select_opts1 = SELECT_OPTS
        # self.width = int(self.canvas.cget('width'))
        # self.height = int(self.canvas.cget('height'))
        self.width = width
        self.height = height
        self.container = container
        self.selected = None
        # inizio e fine dell'area selezionabile
        # all'inizio coincide con l'area dell'immagine a grandezza naturale
        if coords is None:
            self.start = (0, 0)
            self.end = (self.width, self.height)
            self.coordinates = Coordinates((0, 0), (self.width, 0),
                                           (self.width, self.height), (0, self.height))
        else:
            self.start = (coords[0], coords[1])
            self.end = (coords[2], coords[3])

        # Options for areas outside rectanglar selection.
        select_opts1 = self.select_opts1.copy()  # Avoid modifying passed argument.
        select_opts1.update(state=tk.HIDDEN)  # Hide initially.
        # Separate options for area inside rectanglar selection.
        select_opts2 = dict(dash=(2, 2), fill='white', state=tk.HIDDEN)

        # Initial extrema of inner and outer rectangles.
        imin_x, imin_y, imax_x, imax_y = 0, 0, 1, 1
        omin_x, omin_y, omax_x, omax_y = 0, 0, self.width, self.height

        # self.rect = self.canvas.create_rectangle(imin_x, imin_y, imax_x, imax_y, **select_opts1)
        self.rect = (self.canvas.create_line(imin_x, imin_y, imax_x, imin_y, **select_opts2, tags=("line",)),  #a-b
                     self.canvas.create_line(imax_x, imin_y, imax_x, imax_y, **select_opts2, tags=("line",)),  #b-c
                     self.canvas.create_line(imax_x, imax_y, imin_x, imax_y, **select_opts2, tags=("line",)),  #c-d
                     self.canvas.create_line(imin_x, imax_y, imin_x, imin_y, **select_opts2, tags=("line",)),  #d-a
                     )
        self.outside = (
            self.canvas.create_polygon(imin_x, imin_y, imax_x, imin_y, imax_x, imax_y, imin_x, imax_y, **select_opts1),
            self.canvas.create_polygon(imin_x, imin_y, imax_x, imin_y, imax_x, imax_y, imin_x, imax_y, **select_opts1, )
        )
        # ( # Area *outside* selection (inner) rectangle.
        # self.canvas.create_rectangle(omin_x, omin_y, omax_x, imin_y, **select_opts1),
        # self.canvas.create_rectangle(omin_x, imin_y, imin_x, imax_y, **select_opts1),
        # self.canvas.create_rectangle(imax_x, imin_y, omax_x, imax_y, **select_opts1),
        # self.canvas.create_rectangle(omin_x, imax_y, omax_x, omax_y, **select_opts1),
        # Inner rectangle.
        # self.canvas.create_rectangle(imin_x, imin_y, imax_x, imax_y, **select_opts2)
        # )

        if coords is not None:
            self.update(self.start, self.end)

        self.canvas.bind("<Double-Button-1>", self.clear)
        # self.canvas.bind("<Button-1>", self.click_callback)
        self.canvas.bind("<Shift-Button-1>", self.click_callback)
        self.canvas.bind("<Shift-B1-Motion>", self.move_line)
        self.canvas.bind("<Shift-ButtonRelease-1>", self.quit)

    def click_callback(self, event):  #TODO change name
        """
        Finds the closest side of the parallelogram to the user click coordinates.
        :param event: click
        :return: TODO
        """
        print("click")
        self.moving_start = (event.x, event.y)
        draft = tk.Canvas(self.canvas)  # if w is deleted, the draft is deleted
        draft.delete("all")  # if you use the fake canvas for other uses
        concerned = self.canvas.find_withtag("line")  # what you want
        for obj in concerned:
            config = {opt: self.canvas.itemcget(obj, opt) for opt in self.canvas.itemconfig(obj)}
            config["tags"] = str(obj)  # I can retrieve the ID in "w" later with this trick
            draft.create_line(*self.canvas.coords(obj), **config)

        element = draft.find_closest(draft.canvasx(event.x), draft.canvasy(event.y))
        coords = draft.coords(element)
        p1 = np.asarray((coords[0], coords[1]))
        p2 = np.asarray((coords[2], coords[3]))
        dist = norm(np.cross(p2 - p1, p1 - np.asarray((event.x, event.y)))) / norm(p2 - p1)
        print(element)
        print("dist: " + str(dist))
        if dist < MIN_DIST:
            self.selected = element[0]

    def move_line(self, event):
        pan = (self.canvas.canvasx(0), self.canvas.canvasy(0))
        if self.selected:
            # retrieve selected element
            element = self.rect[self.selected - 1]
            # calculate distance moved from last position
            dx, dy = event.x - self.moving_start[0], event.y - self.moving_start[1]
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
            #TODO change to true outside
            self.canvas.coords(self.outside[0], x1, y1, ax, ay, bx, by, x2, y2)
            self.canvas.coords(self.outside[1], x1, y1, ax, ay, bx, by, x2, y2)

        self._show()

    def quit(self, event):
        print("quit")
        self.selected = None

    def update(self, start, end):
        pan = (self.canvas.canvasx(0), self.canvas.canvasy(0))
        # Current extrema of inner and outer rectangles.
        imin_x, imin_y, imax_x, imax_y = self._get_coords(start, end, pan)
        if not all((imin_x, imin_y, imax_x, imax_y)):
            return None
        # TODO controllo coordinate con pan che non funzionano (_get_coords)

        box_image = self.canvas.coords(self.container)  # get image area
        box_img_int = tuple(map(int, box_image))

        omin_x, omin_y, omax_x, omax_y = box_img_int

        up_coord = self._coord_mapping((imin_x, imin_y, imax_x, imax_y), box_img_int)
        print("COORD ---- " + str(up_coord))
        self.start = (up_coord[0], up_coord[1])
        self.end = (up_coord[2], up_coord[3])
        # Update coords of all rectangles based on these extrema.
        self.canvas.coords(self.rect[0], imin_x, imin_y, imax_x, imin_y),
        self.canvas.coords(self.rect[1], imax_x, imin_y, imax_x, imax_y),
        self.canvas.coords(self.rect[2], imax_x, imax_y, imin_x, imax_y),
        self.canvas.coords(self.rect[3], imin_x, imax_y, imin_x, imin_y)
        self.canvas.coords(self.outside[0], imin_x, imin_y, imax_x, imin_y, imax_x, imax_y, imin_x, imax_y)

        # self.canvas.coords(self.rect, imin_x, imin_y, imax_x, imax_y),
        self._show()

    def _coord_mapping(self, selection, box):
        og_h = self.height
        og_w = self.width
        h_ratio = og_h / (box[3] - box[1])
        w_ratio = og_w / (box[2] - box[0])
        coord = ((selection[0] - box[0]) * w_ratio, (selection[1] - box[1]) * h_ratio,
                 (selection[2] - box[0]) * w_ratio, (selection[3] - box[1]) * h_ratio)

        return tuple(map(lambda n: math.ceil(n), coord))

    def _get_coords(self, start, end, pan=0):
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
        for r in self.rect:
            self.canvas.itemconfigure(r, state=tk.HIDDEN)
        for o in self.outside:
            self.canvas.itemconfigure(o, state=tk.HIDDEN)

    def _show(self):
        for r in self.rect:  # Make sure all are now visible.
            self.canvas.itemconfigure(r, state=tk.NORMAL)
        for o in self.outside:
            self.canvas.itemconfigure(o, state=tk.NORMAL)

    def clear(self, event=None):
        self._hide()
        self.start = (0, 0)
        self.end = (self.width, self.height)

    # def crop(self, h_border=0, v_border=0) -> Image.Image:
    #     # left, top, right, bottom = self._get_coords(self.start, self.end)
    #     left, top = self.start
    #     right, bottom = self.end
    #     cropped = self.canvas.img.crop((left - h_border, top - v_border, right + h_border, bottom + v_border))
    #     return cropped
