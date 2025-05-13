import itertools
import tkinter as tk
import numpy as np
from PIL import Image

from Selection import SelectionObject


class RectangleObject(SelectionObject):  #TODO cambia nome (rectangle tipo)
    """ Widget to display a rectangular area on given canvas defined by two points
        representing its diagonal.
    """

    def __init__(self, canvas, container, width, height, img, select_opts, coords=None):
        super(RectangleObject, self).__init__(canvas, container, width, height, img, select_opts, coords)

        # Options for areas outside rectanglar selection.
        select_opts1 = self.select_opts.copy()  # Avoid modifying passed argument.
        select_opts1.update(state=tk.HIDDEN)  # Hide initially.
        # Separate options for area inside rectanglar selection.
        select_opts2 = dict(dash=(2, 2), fill='', outline='white', state=tk.HIDDEN)

        # Initial extrema of inner and outer rectangles.
        imin_x, imin_y, imax_x, imax_y = 0, 0, 1, 1
        omin_x, omin_y, omax_x, omax_y = 0, 0, self.img_width, self.img_height

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

    def _update_rects(self, imin_x, imin_y, imax_x, imax_y, omin_x, omin_y, omax_x, omax_y):
        # Update coords of all rectangles based on these extrema.
        self.canvas.coords(self.rects[0], omin_x, omin_y, omax_x, imin_y),
        self.canvas.coords(self.rects[1], omin_x, imin_y, imin_x, imax_y),
        self.canvas.coords(self.rects[2], imax_x, imin_y, omax_x, imax_y),
        self.canvas.coords(self.rects[3], omin_x, imax_y, omax_x, omax_y),
        self.canvas.coords(self.rects[4], imin_x, imin_y, imax_x, imax_y),

    def matrix(self, p1, p2, p3, p4):
        w = p3[0] - p1[0] + 1
        h = p3[1] - p1[1] + 1
        x_coords = [x for x in range(p1[0], p3[0] + 1)]
        y_coords = [y for y in range(p1[1], p3[1] + 1)]
        output = np.asarray(list(itertools.product(x_coords, y_coords)))
        return output.reshape((w, h, 2))

    def get_mat(self, img, coord, deltax, deltay, mss=None):
        # img = self.img.crop((coord[0].x, coord[0].y, coord[1].x, coord[1].y))
        cropped = np.array(img[coord[0].y: coord[2].y + 1, coord[0].x: coord[2].x + 1, :], dtype=np.uint32)
        # mat = np.array(cropped.convert('RGBA'))
        if cropped.shape[-1] == 3:
            cropped = np.dstack((cropped, np.ones((cropped.shape[0], cropped.shape[1]))))
        return cropped


    def tile_image(self, tile: Image, coords=None, xrepeat=3, yrepeat=3):
        og_w = tile.size[0]*xrepeat
        og_h = tile.size[1]*yrepeat
        tile_w, tile_h = tile.size

        tiled = Image.new('RGBA', (xrepeat * tile_w, yrepeat * tile_h))

        for i in range(0, xrepeat * tile_w, tile_w):
            for j in range(0, yrepeat * tile_h, tile_h):
                tiled.paste(tile, (i, j))

        return tiled
