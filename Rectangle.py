import tkinter as tk
from Selection import SelectionObject


class RectangleObject(SelectionObject): #TODO cambia nome (rectangle tipo)
    """ Widget to display a rectangular area on given canvas defined by two points
        representing its diagonal.
    """

    def __init__(self, canvas, container, width, height, select_opts, coords=None):
        # Create attributes needed to display selection.
        self.canvas = canvas
        self.select_opts1 = select_opts
        # self.width = int(self.canvas.cget('width'))
        # self.height = int(self.canvas.cget('height'))
        self.width = width
        self.height = height
        self.container = container
        # inizio e fine dell'area selezionabile
        # all'inizio coincide con l'area dell'immagine a grandezza naturale
        if coords is None:
            self.start = (0, 0)
            self.end = (self.width, self.height)
        else:
            self.start = (coords[0], coords[1])
            self.end = (coords[2], coords[3])

        # Options for areas outside rectanglar selection.
        select_opts1 = self.select_opts1.copy()  # Avoid modifying passed argument.
        select_opts1.update(state=tk.HIDDEN)  # Hide initially.
        # Separate options for area inside rectanglar selection.
        select_opts2 = dict(dash=(2, 2), fill='', outline='white', state=tk.HIDDEN)

        # Initial extrema of inner and outer rectangles.
        imin_x, imin_y, imax_x, imax_y = 0, 0, 1, 1
        omin_x, omin_y, omax_x, omax_y = 0, 0, self.width, self.height

        self.rects = (
            # Area *outside* selection (inner) rectangle.
            self.canvas.create_rectangle(omin_x, omin_y, omax_x, imin_y, **select_opts1),
            self.canvas.create_rectangle(omin_x, imin_y, imin_x, imax_y, **select_opts1),
            self.canvas.create_rectangle(imax_x, imin_y, omax_x, imax_y, **select_opts1),
            self.canvas.create_rectangle(omin_x, imax_y, omax_x, omax_y, **select_opts1),
            # Inner rectangle.
            self.canvas.create_rectangle(imin_x, imin_y, imax_x, imax_y, **select_opts2)
        )

        if coords is not None:
            self.update(self.start, self.end)

        self.canvas.bind("<Double-Button-1>", self._clear)

    def update(self, start, end):
        pan = (self.canvas.canvasx(0), self.canvas.canvasy(0))
        # Current extrema of inner and outer rectangles.
        imin_x, imin_y, imax_x, imax_y = self._get_coords(start, end, pan)
        if not all((imin_x, imin_y, imax_x, imax_y)):
            return None
        # TODO controllo coordinate con pan che non funzionano (_get_coords)

        # print("coords: " + str(self._get_coords(start, end)))
        box_image = self.canvas.coords(self.container)  # get image area
        box_img_int = tuple(map(int, box_image))


        # # Get scroll region box
        # box_scroll = [min(box_img_int[0], box_canvas[0]), min(box_img_int[1], box_canvas[1]),
        #               max(box_img_int[2], box_canvas[2]), max(box_img_int[3], box_canvas[3])]

        # print("box image coord " + str(box_img_int))
        # print("box canvas " + str(pan))
        omin_x, omin_y, omax_x, omax_y = box_img_int
        # print("outer rect coord " + str((omin_x, omin_y, omax_x, omax_y)))
        # print("inner rect coord " + str((imin_x, imin_y, imax_x, imax_y)))
        up_coord = self._coord_mapping((imin_x, imin_y, imax_x, imax_y), box_img_int)
        print("COORD ---- " + str(up_coord))
        # omin_x, omin_y, omax_x, omax_y = 0, 0, self.width, self.height
        # self.start = (imin_x, imin_y)
        # self.end = (imax_x, imax_y)
        self.start = (up_coord[0], up_coord[1])
        self.end = (up_coord[2], up_coord[3])
        # Update coords of all rectangles based on these extrema.
        self.canvas.coords(self.rects[0], omin_x, omin_y, omax_x, imin_y),
        self.canvas.coords(self.rects[1], omin_x, imin_y, imin_x, imax_y),
        self.canvas.coords(self.rects[2], imax_x, imin_y, omax_x, imax_y),
        self.canvas.coords(self.rects[3], omin_x, imax_y, omax_x, omax_y),
        self.canvas.coords(self.rects[4], imin_x, imin_y, imax_x, imax_y),

        for rect in self.rects:  # Make sure all are now visible.
            self.canvas.itemconfigure(rect, state=tk.NORMAL)