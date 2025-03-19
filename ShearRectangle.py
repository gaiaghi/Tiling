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


def point_selector(func1, func2):
    return lambda a: func1(a[a[:, 0] == func2(a[:, 0])], 0)


class ShearRectangle:
    """ Widget to display a sheared rectangular area on given canvas defined by two points
        representing its diagonal + user edit.
    """

    def __init__(self, canvas, container, width, height, coords=None):
        # Create attributes needed to display selection.
        self.draft = None
        self.moving_start = None
        self.canvas = canvas
        self.select_opts1 = SELECT_OPTS
        # self.width = int(self.canvas.cget('width'))
        # self.height = int(self.canvas.cget('height'))
        #TODO rename (img width, img height)
        self.width = width
        self.height = height
        self.container = container
        self.selected = None
        self.direction = 0
        self.coordinates = None
        # inizio e fine dell'area selezionabile
        # all'inizio coincide con l'area dell'immagine a grandezza naturale
        if coords is None:
            self.start = (0, 0)
            self.end = (self.width, self.height)
            # self.coordinates = Coordinates((0, 0), (self.width, 0),
            #                                (self.width, self.height), (0, self.height))
        else:
            self.start = (coords[0], coords[1])
            self.end = (coords[2], coords[3])
        self.coordinates = (self.start, (self.end[0], self.start[1]), (self.start[0], self.end[1]), self.end)

        # Options for areas outside rectanglar selection.
        select_opts1 = self.select_opts1.copy()  # Avoid modifying passed argument.
        select_opts1.update(state=tk.HIDDEN)  # Hide initially.
        # Separate options for area inside rectanglar selection.
        # select_opts2 = dict(dash=(2, 2), width=2, fill='white', state=tk.HIDDEN)

        # Initial extrema of inner and outer rectangles.
        imin_x, imin_y, imax_x, imax_y = 0, 0, 1, 1
        # omin_x, omin_y, omax_x, omax_y = 0, 0, self.width, self.height

        # self.rect = self.canvas.create_rectangle(imin_x, imin_y, imax_x, imax_y, **select_opts1)
        # a = (imin_x, imin_y)
        # b = (imax_x, imin_y)
        # c = (imax_x, imax_y)
        # d = (imin_x, imax_y)
        # self.rect = (self.canvas.create_line(imin_x, imin_y, imax_x, imin_y, **select_opts2, tags=("line",)),  #a-b
        #              self.canvas.create_line(imax_x, imin_y, imax_x, imax_y, **select_opts2, tags=("line",)),  #b-c
        #              self.canvas.create_line(imax_x, imax_y, imin_x, imax_y, **select_opts2, tags=("line",)),  #c-d
        #              self.canvas.create_line(imin_x, imax_y, imin_x, imin_y, **select_opts2, tags=("line",)),  #d-a
        #              )
        # self.outside = (
        #     self.canvas.create_polygon(0, 0, 0, self.height, self.width, self.height, c[0], c[1], d[0], d[1], a[0],
        #                                a[1], **select_opts1),
        #     self.canvas.create_polygon(0, 0, self.width, 0, self.width, self.height, c[0], c[1], b[0], b[1], a[0],
        #                                a[1], **select_opts1))

        self.rect_setup()

        if coords is not None:
            self.update(self.start, self.end)

        self.canvas.bind("<Double-Button-1>", self._clear)
        # self.canvas.bind("<Button-1>", self.click_callback)
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
            element = self.rect[self.selected - 1]
            opp = self.rect[(self.selected+1) % 4]
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
            side = (opposite[2] - opposite[0])*(current[1] - opposite[1]) - (opposite[3] - opposite[1])*(current[0] - opposite[0])

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
                # if side <= 0:
                #     dx = 0
            if self.direction == 1:
                dx = 0
                # if side <= 0:
                #     dy = 0

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

            # self.draft = tk.Canvas(self.canvas)  # if w is deleted, the draft is deleted
            # self.draft.delete("all")  # if you use the fake canvas for other uses
            # concerned = self.canvas.find_withtag("line")  # what you want
            # for obj in concerned:
            #     config = {opt: self.canvas.itemcget(obj, opt) for opt in self.canvas.itemconfig(obj)}
            #     config["tags"] = str(obj)  # I can retrieve the ID in "w" later with this trick
            #     self.draft.create_line(*self.canvas.coords(obj), **config)

            # a = (self.draft.coords(1)[0], self.draft.coords(1)[1], 0)
            # b = (self.draft.coords(1)[2], self.draft.coords(1)[3], 1)
            # c = (self.draft.coords(3)[0], self.draft.coords(3)[1], 2)
            # d = (self.draft.coords(3)[2], self.draft.coords(3)[3], 3)
            # points = [a, b, c, d]
            # points = sorted(points, key=lambda x: (x[0], x[1]))

            # flip = 1
            #caso verticale
            # if self.selected == 2 and b[0] < a[0]:
            #     flip = -1
            # if self.selected == 4 and a[0] > b[0]:
            #     flip = -1
            # if self.selected == 1 and a[1] > d[1]:
            #     flip = -1
            # if self.selected == 3 and d[1] < a[1]:
            #     flip = -1
            #
            # p1 = min(points, key=lambda p: p[0])
            # candidati = [item for item in points if item[0] == p1[0]]
            # if len(candidati) > 1:
            #     p1 = min(candidati, key=lambda p: p[1])
            # index = p1[2]
            # p1 = (p1[0], p1[1])
            # p2 = points[(index + 1*flip) % 4]
            # p3 = points[(index + 2*flip) % 4]
            # p4 = points[(index + 3*flip) % 4]

            # print("index a " + str(index))
            # print(points)

            # p1 = self.point_selector(np.min, np.min)(points)
            # p2 = self.point_selector(np.min, np.max)(points)
            # p3 = self.point_selector(np.max, np.max)(points)
            # p4 = self.point_selector(np.max, np.min)(points)

            # self.canvas.coords(self.outside[0], omin_x, omin_y, omin_x, omax_y, omax_x, omax_y, p3[0], p3[1], p4[0],
            #                    p4[1], p1[0], p1[1])
            # self.canvas.coords(self.outside[1], omin_x, omin_y, omax_x, omin_y, omax_x, omax_y, p3[0], p3[1], p2[0],
            #                    p2[1], p1[0], p1[1])
            self._show()

    # def _point_selector(self, func1, func2):
    #     return lambda a: func1(a[a[:, 0] == func2(a[:, 0])], 0)

    def quit(self, event):
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

        self._update_coordinates()

        # a = (imin_x, imin_y)
        # b = (imax_x, imin_y)
        # c = (imax_x, imax_y)
        # d = (imin_x, imax_y)
        # self.canvas.coords(self.outside[0], omin_x, omin_y, omin_x, omax_y, omax_x, omax_y, c[0], c[1], d[0], d[1],
        #                    a[0], a[1]),
        # self.canvas.coords(self.outside[1], omin_x, omin_y, omax_x, omin_y, omax_x, omax_y, c[0], c[1], b[0], b[1],
        #                    a[0], a[1])

        self._show()

    def _coord_mapping(self, selection, box):
        og_h = self.height
        og_w = self.width
        h_ratio = og_h / (box[3] - box[1])
        w_ratio = og_w / (box[2] - box[0])
        coord = ((selection[0] - box[0]) * w_ratio, (selection[1] - box[1]) * h_ratio,
                 (selection[2] - box[0]) * w_ratio, (selection[3] - box[1]) * h_ratio)

        return tuple(map(lambda n: math.ceil(n), coord))

    #TODO unifica
    def _coord_mapping2(self, x, y, box):
        og_h = self.height
        og_w = self.width
        h_ratio = og_h / (box[3] - box[1])
        w_ratio = og_w / (box[2] - box[0])
        coord = ((x - box[0]) * w_ratio, (y - box[1]) * h_ratio)

        return tuple(map(lambda n: math.ceil(n), coord))


    def _get_coords(self, start, end, pan=(0,0)):
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
        # for o in self.outside:
        #     self.canvas.itemconfigure(o, state=tk.HIDDEN)

    def _show(self):
        for r in self.rect:  # Make sure all are now visible.
            self.canvas.itemconfigure(r, state=tk.NORMAL)
        # for o in self.outside:
        #     self.canvas.itemconfigure(o, state=tk.NORMAL)

    def _clear(self, event=None):
        self._hide()
        self.start = (0, 0)
        self.end = (self.width, self.height)
        self.draft = None

    # def crop(self, h_border=0, v_border=0) -> Image.Image:
    #     # left, top, right, bottom = self._get_coords(self.start, self.end)
    #     left, top = self.start
    #     right, bottom = self.end
    #     cropped = self.canvas.img.crop((left - h_border, top - v_border, right + h_border, bottom + v_border))
    #     return cropped

    def rect_setup(self):
        select_opts2 = dict(dash=(2, 2), width=2, fill='white', state=tk.HIDDEN)
        imin_x, imin_y, imax_x, imax_y = 0, 0, 1, 1
        self.rect = (self.canvas.create_line(imin_x, imin_y, imax_x, imin_y, **select_opts2, tags=("line",)),  #a-b
                     self.canvas.create_line(imax_x, imin_y, imax_x, imax_y, **select_opts2, tags=("line",)),  #b-c
                     self.canvas.create_line(imax_x, imax_y, imin_x, imax_y, **select_opts2, tags=("line",)),  #c-d
                     self.canvas.create_line(imin_x, imax_y, imin_x, imin_y, **select_opts2, tags=("line",)),  #d-a
                     )

    def _update_coordinates(self):
        box_image = self.canvas.coords(self.container)  # get image area
        box_img_int = tuple(map(int, box_image))

        self.coordinates = (self._coord_mapping2(self.canvas.coords(self.rect[0])[0], self.canvas.coords(self.rect[0])[1],box_img_int),
                            self._coord_mapping2(self.canvas.coords(self.rect[1])[0], self.canvas.coords(self.rect[1])[1],box_img_int),
                            self._coord_mapping2(self.canvas.coords(self.rect[2])[0], self.canvas.coords(self.rect[2])[1],box_img_int),
                            self._coord_mapping2(self.canvas.coords(self.rect[3])[0], self.canvas.coords(self.rect[3])[1], box_img_int))
        # self.coordinates = ((self.canvas.coords(self.rect[0])[0], self.canvas.coords(self.rect[0])[1]),
        #                     (self.canvas.coords(self.rect[1])[0], self.canvas.coords(self.rect[1])[1]),
        #                     (self.canvas.coords(self.rect[2])[0], self.canvas.coords(self.rect[2])[1]),
        #                     (self.canvas.coords(self.rect[3])[0], self.canvas.coords(self.rect[3])[1]))
        self.start = self.coordinates[0]
        self.end = self.coordinates[2]
