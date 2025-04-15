import os
import os.path
from os import listdir
from os.path import isfile, join
import argparse
import sys
import math
import time
import tkinter as tk
import numpy as np
from tkinter import filedialog
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.path import Path
from PIL import Image, ImageDraw, ImageTransform
from datetime import datetime

from skimage.draw import line

import Selection
from CanvasImage import CanvasImage
from Selection import Coordinates, TwoDPoint
from Rectangle import RectangleObject

OUT_DIR = './out/'
WIDTH, HEIGHT = 900, 900
BACKGROUND = '#292929'


class Tiling:
    #TODO riorganizza classi in file diversi
    # fai prove su mappe diverse, temporizza per il report
    # prova a parallelizzare calcolo differenze
    # ricerca su tutte le mappe

    # def __init__(self, master, image: Image.Image, selection: SelectionObject, border=5, search_area=0.15):
    def __init__(self, master, img: Image.Image, start: TwoDPoint, end: TwoDPoint, selection: Selection,
                 shear: Coordinates = None, border=10,
                 search_area=0.15,
                 maps=None, start_tiling=True):
        self.selection = selection
        self.tiled = None
        self.master = master
        self.search_ratio = search_area
        # overlap border size
        self.border = border  #TODO prova con 5, 10 e 15, 25
        self.image = img  # original image
        # start and end of selected area
        self.start = start
        self.end = end
        self.shear = Coordinates(shear[0], shear[1], shear[2], shear[3])  # coordinates of sheared rect
        self.maps = maps  # all image maps
        # width and height of the user-selected area
        self.width = self.end.x - self.start.x
        self.height = self.end.y - self.start.y
        # vertical search area (size)
        self.bv = int(self.height * self.search_ratio)
        # horizontal search area (size)
        self.bo = int(self.width * self.search_ratio)

        if self.bv < 1:
            self.bv = 1
        if self.bo < 1:
            self.bo = 1

        # check if image overflow
        #TODO check con x e y max per shear
        if (self.end.x + self.bo) > self.image.width:
            start_h = (self.image.width - 2 * self.bo - self.border, self.start.y)
            end_h = (self.image.width - 2 * self.bo, self.end.y)
        else:
            start_h = (self.end.x - self.bo, self.start.y)
            end_h = (self.end.x - self.bo + self.border, self.end.y)

        if (self.end.y + self.bv) > self.image.height:
            start_v = (self.start.x, self.image.height - 2 * self.bv - self.border)
            end_v = (self.end.x, self.image.height - 2 * self.bv)
        else:
            start_v = (self.start.x, self.end.y - self.bv)
            end_v = (self.end.x, self.end.y - self.bv + self.border)

        # Borders setup
        if self.shear is None:
            self._rect_setup(start_h, end_h, start_v, end_v)
        else:
            self._shear_setup(start_h, end_h, start_v, end_v)  #TODO shear setup
        # self._rect_setup(start_h, end_h, start_v, end_v)

        # start module search
        if start_tiling:
            self.start_search()

    def _rect_setup(self, start_h, end_h, start_v, end_v):

        self.left_border = Coordinates((self.start[0], self.start[1]),
                                       (self.start[0] + self.border, self.start[1]),
                                       (self.start[0] + self.border, self.end[1]),
                                       (self.start[0], self.end[1]))

        self.right_border = Coordinates((start_h[0], start_h[1]),
                                        (end_h[0], start_h[1]),
                                        (end_h[0], end_h[1]),
                                        (start_h[0], end_h[1]))

        self.top_border = Coordinates((self.start[0], self.start[1]),
                                      (self.end[0], self.start[1]),
                                      (self.end[0], self.start[1] + self.border),
                                      (self.start[0], self.start[1] + self.border))

        self.bottom_border = Coordinates((start_v[0], start_v[1]),
                                         (end_v[0], start_v[1]),
                                         (end_v[0], end_v[1]),
                                         (start_v[0], end_v[1]))

        # crop_img = self.crop(self.image, self.start, self.end, self.bo, self.bv)
        # # user-selected image (with border) to matrix
        # matrix = crop_img.convert('RGB')
        # self.cropped = np.array(matrix)

    def _shear_setup(self, start_h, end_h, start_v, end_v):

        self.left_pixels = self.get_line(self.shear.A, self.shear.D)
        self.right_pixels = self.get_line(self.shear.B, self.shear.C)
        self.top_pixels = self.get_line(self.shear.A, self.shear.B)
        self.bottom_pixels = self.get_line(self.shear.D, self.shear.C)

        self.delta_idx_RL = [(p[0] - self.right_pixels[0][0], p[1] - self.right_pixels[0][1]) for p in self.right_pixels]
        self.delta_idx_TB = [(p[0] - self.top_pixels[0][0], p[1] - self.top_pixels[0][1]) for p in self.top_pixels]

        self.left_border = Coordinates((self.shear.A.x, self.shear.A.y), self.top_pixels[self.border - 1],
                                       self.bottom_pixels[self.border - 1], (self.shear.D.x, self.shear.D.y))


        self.right_border = Coordinates(self.top_pixels[-self.bo],
                                        self.tuple_sum(self.top_pixels[-self.bo], self.delta_idx_TB[self.border-1]),
                                        self.tuple_sum(self.bottom_pixels[-self.bo], self.delta_idx_TB[self.border-1]),
                                        self.bottom_pixels[-self.bo])

        self.top_border = Coordinates((self.shear.A.x, self.shear.A.y),
                                      (self.shear.B.x, self.shear.B.y),
                                      self.left_pixels[self.border - 1],
                                      self.right_pixels[self.border - 1])

        self.bottom_border = Coordinates(self.left_pixels[-self.bv],
                                         self.right_pixels[-self.bv],
                                         self.tuple_sum(self.right_pixels[-self.bv], self.delta_idx_RL[self.border-1]),
                                         self.tuple_sum(self.left_pixels[-self.bv], self.delta_idx_RL[self.border-1]))


        print("self left" + str(self.left_border))
        print("self right" + str(self.right_border))
        print("self top" + str(self.top_border))
        print("self bottom" + str(self.bottom_border))

    def _get_masked_img(self, a, b, c, d):
        image = self.image
        background = Image.new("RGBA", image.size, (0, 0, 0, 0))
        mask = Image.new("RGBA", image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.polygon(((a[0], a[1]), (b[0], b[1]),
                      (c[0], c[1]), (d[0], d[1])), fill='green',
                     outline=None)
        minx = min(a[0], b[0], c[0], d[0])
        maxx = max(a[0], b[0], c[0], d[0])
        miny = min(a[1], b[1], c[1], d[1])
        maxy = max(a[1], b[1], c[1], d[1])
        new_img = Image.composite(image, background, mask)
        new_img = new_img.crop((minx, miny, maxx, maxy))

        # selection = np.array(new_img)
        # extract = []
        # for l in selection:
        #     if not all(p[3] == 0 for p in l):
        #         extract.append(l)
        #
        # extract = np.array(extract)
        # idx = np.argwhere(np.all(extract[..., :] == 0, axis=0))
        # a2 = np.delete(extract, idx, axis=1)
        #
        # cropped = Image.fromarray(np.array(a2)[:,:,:3], mode='RGB')
        # cropped.show()
        return new_img

    def start_search(self):
        # TODO togli tutte le stampe
        og_img = self.image.convert('RGB')
        og_img = np.array(og_img)
        h_diff_values = []
        v_diff_values = []
        txt_path = os.path.join(OUT_DIR, "search_info.txt")
        f = open(txt_path, "w")
        #TODO distingui caso rettangolo e parallelogramma
        print("bo e bv ", self.bo, self.bv)

        # ricerca orizzontale
        step = 0
        min_diff_right = (1, 0)  # tuple containing (min difference, step)
        # bordo sinistro partendo dalla coordinata 0 della selezione dell'utenete (fissato)
        left_border = self.selection.get_mat((self.left_border.A, self.left_border.B,
                                              self.left_border.C, self.left_border.D),
                                             self.delta_idx_TB[:self.border], self.delta_idx_RL)
        # print("left.size ", left_border.size)

        f.write("#left" + str(self.left_border.start) + " " + str(self.left_border.end) + "\n")

        start_time = time.time()

        tmp_right = Coordinates((self.right_border.A.x, self.right_border.A.y),
                                (self.right_border.B.x, self.right_border.B.y),
                                (self.right_border.C.x, self.right_border.C.y),
                                (self.right_border.D.x, self.right_border.D.y))
        # print("tmp_right dx ", tmp_right.A.x-tmp_right.B.x)
        # print("left dx ", self.left_border.A.x-self.left_border.B.x)

        # lf = Image.fromarray(left_border, mode='RGB')
        # self.save_img(lf, 'LEFT----.png')
        #+++++++++++ fissato a sx, sposto il bordo di dx
        while step < 2 * self.bo:  # ricerca  nell'area tra -bo e +bo
            right = self.selection.get_mat((tmp_right.A, tmp_right.B,
                                            tmp_right.C, tmp_right.D),
                                           self.delta_idx_TB[:self.border], self.delta_idx_RL)
            diff = self.normalize(right) - self.normalize(left_border)
            m_norm = sum(sum(sum(abs(diff)))) / right.size  # Manhattan norm
            if m_norm < min_diff_right[0]:
                min_diff_right = (m_norm, step)
                min_right_border = Coordinates(tmp_right.A.tuple, tmp_right.B.tuple, tmp_right.C.tuple, tmp_right.D.tuple)

            h_diff_values.append(m_norm)
            # print("step, diff, ", step, m_norm)
            step += 1
            tmp_right = Coordinates(self.tuple_sum(self.right_border.A, self.delta_idx_TB[step]),
                                    self.tuple_sum(self.right_border.A, self.delta_idx_TB[step + self.border - 1]),
                                    self.tuple_sum(self.right_border.D, self.delta_idx_TB[step + self.border - 1]),
                                    self.tuple_sum(self.right_border.D, self.delta_idx_TB[step]))
            f.write(str(step) + " " + str(tmp_right) + " " + str(m_norm) + "\n")

            # rrrrr = self._get_masked_img(tmp_right.A, tmp_right.B,
            #                             tmp_right.C, tmp_right.D)
            # self.save_img(rrrrr, 'RIGHT_ '+str(step)+'.png')
            # rt = Image.fromarray(right, mode='RGB')
            # self.save_img(rt, 'RIGHT__ '+str(step)+'.png')


        print("Minimun (h) distanze between borders find at step " + str(min_diff_right[1]) + ": " + str(
            min_diff_right[0]))

        #++++++++++++++++++++++++++++++++++++++++++++++++++
        # vertical search
        step = 0
        min_diff_bottom = (1, 0)  # tuple containing (min difference, step)

        # bordo top partendo dalla coordinata 0 della selezione dell'utenete
        top_border = self.selection.get_mat((self.top_border.A, self.top_border.B,
                                             self.top_border.C, self.top_border.D),
                                             self.delta_idx_TB, self.delta_idx_RL[:self.border])
        # tb = Image.fromarray(top_border, mode='RGB')
        # self.save_img(tb, 'TOP______.png')
        f.write("\n\n#top" + str(self.top_border.start) + " " + str(self.top_border.end) + "\n")

        # +++++++++++ fissato top, sposto il bordo bottom
        tmp_bottom = Coordinates((self.bottom_border.A.x, self.bottom_border.A.y),
                                 (self.bottom_border.B.x, self.bottom_border.B.y),
                                 (self.bottom_border.C.x, self.bottom_border.C.y),
                                 (self.bottom_border.D.x, self.bottom_border.D.y))

        while step < 2 * self.bv:  # ricerca  nell'area tra -bo e +bo

            bottom = self.selection.get_mat((tmp_bottom.A, tmp_bottom.B,
                                             tmp_bottom.C, tmp_bottom.D),
                                            self.delta_idx_TB, self.delta_idx_RL[:self.border])

            # TODO  ricontrolla normalize
            diff = self.normalize(bottom) - self.normalize(top_border)
            m_norm = sum(sum(sum(abs(diff)))) / bottom.size  # Manhattan norm
            if m_norm < min_diff_bottom[0]:
                min_diff_bottom = (m_norm, step)
                min_bottom_border = Coordinates(tmp_bottom.A.tuple, tmp_bottom.B.tuple,
                                                tmp_bottom.C.tuple, tmp_bottom.D.tuple)
            v_diff_values.append(m_norm)
            step += 1
            tmp_bottom = Coordinates(self.tuple_sum(self.bottom_border.A, self.delta_idx_RL[step]),
                                     self.tuple_sum(self.bottom_border.B, self.delta_idx_RL[step]),
                                     self.tuple_sum(self.bottom_border.B, self.delta_idx_RL[step + self.border - 1]),
                                     self.tuple_sum(self.bottom_border.A, self.delta_idx_RL[step + self.border - 1]))

            f.write(str(step) + " " + str(tmp_bottom) + " " + str(m_norm) + "\n")
            # bt = Image.fromarray(bottom, mode='RGB')
            # self.save_img(bt, 'BOTTOM__ '+str(step)+'.png')


        end_time = time.time()

        print("Minimun (v) distanze between borders find at step " + str(min_diff_bottom[1]) + ": " + str(
            min_diff_bottom[0]))
        # print("bottom", bottom)
        # print("bottom shape", bottom.shape)
        # rrrrr = self._get_masked_img(tmp_bottom.A, tmp_bottom.B,
                                     # tmp_bottom.C, tmp_bottom.D)
        # self.save_img(rrrrr, 'bbbbbb.png')
        # print("delta rl ", self.delta_idx_RL)
        # print("delta tb ", self.delta_idx_TB)

        self.selection.get_mat((tmp_bottom.A, tmp_bottom.B,
                                         tmp_bottom.C, tmp_bottom.D),
                                        self.delta_idx_TB, self.delta_idx_RL[:self.border], mss="print")


        f.write("\n\n tot time: " + str(end_time - start_time) + " sec\n")
        #++++++++++++++++++++++++++++++++++++++++++++++++++
        # chiusura file dati
        f.close()

        self.bottom_border = min_bottom_border
        self.right_border = min_right_border

        # left, top, right, bottom
        if self.shear is None:
            mod_coord = (self.start[0], self.start[1], self.right_border.start.x, self.bottom_border.start.y)
            module = self.image.crop(mod_coord)
            # tile extracted module
            imgm = Image.fromarray(np.array(module.convert('RGB')), mode='RGB')
            self.tiled = self.tile_image(imgm)
            self.save_img(self.image.crop((self.left_border.start.x, self.left_border.start.y,
                                           self.left_border.end.x, self.left_border.end.y)), 'left_border.png')
            self.save_img(self.image.crop((self.right_border.start.x, self.right_border.start.y,
                                           self.right_border.end.x, self.right_border.end.y)), 'right_border.png')
            self.save_img(self.image.crop((self.top_border.start.x, self.top_border.start.y,
                                           self.top_border.end.x, self.top_border.end.y)), 'top_border.png')
            self.save_img(self.image.crop((self.bottom_border.start.x, self.bottom_border.start.y,
                                           self.bottom_border.end.x, self.bottom_border.end.y)), 'bottom_border.png')

            imgc = Image.fromarray(np.array(self.crop(self.image, self.start, self.end).convert('RGB')), mode='RGB')
            self.save_img(imgc, 'user_crop.png')
            self.save_img(self.tiled, file_name="tiled.png")
            self.save_img(imgm, 'extracted_module.png')

            # area di ricerca
            search_area = og_img[self.start[1]: self.end[1],
                          self.end[0] - self.bo: self.end[0] + self.bo, :]
            imgs = Image.fromarray(search_area, mode='RGB')
            self.save_img(imgs, 'search_area.png')

            if self.maps is not None:
                self.crop_maps(mod_coord)
        else:
            p1 = (self.right_border.A.x, self.right_border.A.y)
            p2 = (self.right_border.D.x, self.right_border.D.y)
            p3 = (self.bottom_border.A.x, self.bottom_border.A.y)
            p4 = (self.bottom_border.B.x, self.bottom_border.B.y)

            module_img = self._get_masked_img(self.left_border.A, self.right_border.A,
                                              self.line_intersection((p1, p2), (p3, p4)),
                                              self.bottom_border.A)
            self.save_img(module_img, 'module_shear.png')

            rrrrr = self._get_masked_img(self.left_border.A, self.left_border.B,
                                        self.left_border.C, self.left_border.D)
            self.save_img(rrrrr, 'LEFT.png')

            llll = self._get_masked_img(self.right_border.A, self.right_border.B,
                                        self.right_border.C, self.right_border.D)
            self.save_img(llll, 'RIGHT.png')
            #TODO riscrivi per togliere ripetizione

        self.plot(h_diff_values, self.bo, file_name="h_plot.png")
        self.plot(v_diff_values, self.bv, file_name="v_plot.png")

    # def _drop_alpha(self, img):
    #     return img if img.shape[-1] == 3 else img[:, :, 1:]

    def crop_maps(self, coords):
        for f in self.maps:
            img = Image.open(f)
            if img.width == self.image.width and img.height == self.image.height:
                img = img.crop(coords)
                # self.tiled = self.tile_image(imgm)
                # self.save_img(self.tiled, file_name="tiled.png")
                img_name = os.path.basename(f)
                name = os.path.splitext(img_name)[0] + "_Module" + os.path.splitext(img_name)[1]
                self.save_img(img, file_name=name)
            else:
                print("Texture map " + os.path.basename(f) + " has not the same dimensions of the processed texture.")
            img.close()

    @staticmethod
    def line_intersection(line1, line2):
        xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
        ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

        def det(a, b):
            return a[0] * b[1] - a[1] * b[0]

        div = det(xdiff, ydiff)
        if div == 0:
            raise Exception('lines do not intersect')

        d = (det(*line1), det(*line2))
        x = det(d, xdiff) / div
        y = det(d, ydiff) / div
        return int(x), int(y)

    #TODO mettere i metodi statici in utils.py ?
    @staticmethod
    def get_line(a, b):
        rr, cc = line(int(a[0]), int(a[1]),
                      int(b[0]), int(b[1]))
        return list(zip(rr, cc))

    @staticmethod
    def crop(img: Image.Image, start, end, h_border=0, v_border=0) -> Image.Image:
        # left, top, right, bottom = self._get_coords(self.start, self.end)
        left, top = start.x, start.y
        right, bottom = end.x, end.y
        cropped = img.crop((left - h_border, top - v_border, right + h_border, bottom + v_border))
        return cropped

    def tile_image(self, tile: Image.Image):
        og_w = self.image.size[0]
        og_h = self.image.size[1]
        tile_w, tile_h = tile.size

        # get how many times to tile module to fit original image
        xrepeat = og_w // tile_w
        yrepeat = og_h // tile_h
        # 2x2 tiling even if module is big
        xrepeat = 2 if xrepeat == 1 else xrepeat
        yrepeat = 2 if yrepeat == 1 else yrepeat

        tiled = Image.new('RGB', (xrepeat * tile_w, yrepeat * tile_h))

        for i in range(0, xrepeat * tile_w, tile_w):
            for j in range(0, yrepeat * tile_h, tile_h):
                tiled.paste(tile, (i, j))

        return tiled

    def normalize(self, arr):
        normalized = (arr - np.min(arr)) / (np.max(arr) - np.min(arr))
        return normalized

    def save_img(self, img: Image.Image, file_name="image.png"):
        ts = TSTAMP
        currTS2 = datetime.now().strftime("%Y%m%d%H%M%S_") if TSTAMP else ""
        file_path = os.path.join(OUT_DIR, currTS2 + file_name)
        if not os.path.isdir(OUT_DIR):
            os.mkdir(OUT_DIR)
        # print("immagine da salvare - size - "+ str(img.size))
        img.save(file_path)

    def plot(self, values, range_limit, direction=0, file_name="plot.png"):
        fig, ax = plt.subplots()
        # data
        end_y = len(values) - range_limit
        points = range(-range_limit, end_y)

        if direction == 0:
            y = points
            x = values
        else:
            y = values
            x = points

        ax.plot(y, x, linewidth=1.0, color='red')

        min_x = np.argmin(x)
        min_y = np.min(x)

        plt.scatter(y[min_x], min_y, c='r', label='min @ iter # ' + str(min_x))
        plt.legend()
        plt.ylabel('Q')
        plt.xlabel('pixel')
        # plt.show()
        ts = TSTAMP
        currTS2 = datetime.now().strftime("%Y%m%d%H%M%S_") if TSTAMP else ""
        file_path = os.path.join(OUT_DIR, currTS2 + file_name)
        # file_path = os.path.join(OUT_DIR, file_name)
        fig.savefig(file_path)
        plt.close()

    @staticmethod
    def tuple_sum(a, b):
        return tuple([sum(x) for x in zip(a, b)])

    @staticmethod
    def angle3(a, b, c):
        # ang = math.degrees(math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(a[1] - b[1], a[0] - b[0]))
        ang = math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(a[1] - b[1], a[0] - b[0])
        return ang  #+ 360 if ang < 0 else ang


class Application(tk.Frame):
    # Default selection object options.
    SELECT_OPTS = dict(dash=(2, 2), stipple='gray25', fill='white',
                       outline='')

    def __init__(self, parent, coords=None, imgpath=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.master.rowconfigure(0, weight=1)  # make the CanvasImage widget expandable
        self.master.columnconfigure(0, weight=1)
        self.canvas = CanvasImage(self.master, path=imgpath, coords=coords)  # create widget
        self.canvas.grid(row=0, column=0)  # show widget

        self.folder_maps = None

        #menu bar creation
        self.tiling = None
        parent.option_add('*tearOff', tk.FALSE)
        self.menubar = tk.Menu(parent)
        parent['menu'] = self.menubar
        menu_file = tk.Menu(self.menubar)
        menu_edit = tk.Menu(self.menubar)
        menu_tiling = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=menu_file, label='File')
        menu_file.add_command(label="Open single image...", accelerator="Ctrl+O", command=self.load_image)
        menu_file.add_command(label="Open image map in folder...", accelerator="Ctrl+F", command=self.load_folder)
        self.menubar.add_cascade(menu=menu_edit, label='Edit')
        self.menubar.add_cascade(menu=menu_tiling, label='Tiling')
        menu_tiling.add_command(label="Start Tiling", accelerator="Ctrl+T", command=self.start_tiling)
        menu_tiling.add_command(label="Update image with tiled texture", accelerator="Ctrl+U",
                                command=self.update_image)

        parent.bind_all("<Control-o>", self.load_image)
        parent.bind_all("<Control-O>", self.load_image)
        parent.bind_all("<Control-f>", self.load_folder)
        parent.bind_all("<Control-F>", self.load_folder)
        parent.bind_all("<Control-t>", self.start_tiling)
        parent.bind_all("<Control-T>", self.start_tiling)
        parent.bind_all("<Control-u>", self.update_image)
        parent.bind_all("<Control-U>", self.update_image)

        menu_file.add_separator()
        menu_file.add_command(label="Exit", command=root.destroy)
        parent.config(menu=self.menubar)

        # pop-up menu creation
        self.popup_menu = tk.Menu(parent, tearoff=0)
        # self.popup_menu.add_command(label="Crop selection", command=self.crop_selected)
        self.popup_menu.add_command(label="Save selection", command=self.save_selected)
        # TODO cambia menù a pop up in una tendina del menù sopra
        #  per il salvataggio del crop e per la ricarica dell'immagine iniziale (es: dopo tiling automatico)
        # parent.bind("<Button-3>", self.do_popup)

    def load_image(self, event=None):
        file_path = filedialog.askopenfilename(title="Open Image...",
                                               filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.ico")])
        if file_path:
            self.tiling = None
            self.canvas.destroy()
            self.canvas = CanvasImage(self.master, path=file_path)  # create widget
            self.canvas.grid(row=0, column=0)
        # if file_path:
        #     self.canvas.img = Image.open(file_path)
        #     self.canvas.pht_img = ImageTk.PhotoImage(self.canvas.img)
        #     self.canvas.orig = self.canvas.pht_img
        #     # self.canvas.itemconfig(self.displayed_img, image=self.canvas.pht_img)
        #     # self.canvas.config(height=self.canvas.pht_img.height(), width=self.canvas.pht_img.width())
        #     self.canvas.canvas.itemconfig(self.canvas.displayed_img, image=self.canvas.pht_img)
        #     self.canvas.canvas.config(height=self.canvas.pht_img.height(), width=self.canvas.pht_img.width())
        #     self.canvas.selection_obj.height = self.canvas.pht_img.height()
        #     self.canvas.selection_obj.width = self.canvas.pht_img.width()
        #     self.canvas.selection_obj.clear()

    def load_folder(self, event=None):
        """ Open single image to tile in a folder containing all texture maps.
        """
        file_path = filedialog.askopenfilename(title="Open image map in folder...",
                                               filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.ico")])
        file_path = os.path.abspath(file_path)
        if file_path:
            folder_path = os.path.dirname(file_path)
            # if os.path.isdir(folder_path):
            #     folder_files = [join(folder_path, f) for f in listdir(folder_path) if isfile(join(folder_path, f))]
            if os.path.isdir(folder_path):
                folder_files = [join(folder_path, f) for f in listdir(folder_path) if isfile(join(folder_path, f))]
                maps = [f for f in folder_files if not os.path.basename(file_path) in f]
            else:
                sys.exit("Cannot open the provided directory.")

            self.canvas.destroy()
            self.canvas = CanvasImage(self.master, path=file_path)  # create widget
            self.canvas.grid(row=0, column=0)
            self.folder_maps = maps
            # self.tiling = Tiling(self.master, self.canvas.canvas.img, self.canvas.selection_obj.start,
            #                      self.canvas.selection_obj.end, folder=folder_path, start_tiling=False)
        else:
            sys.exit("Cannot open image.")

    def start_tiling(self, event=None):
        # if self.tiling is None:
        #     self.tiling = Tiling(self.master, self.canvas.canvas.img, self.canvas.selection_obj.start,
        #                          self.canvas.selection_obj.end)
        # else:
        #     self.tiling.start_search()
        #TODO qui la separazione sui casi rect o shear rect

        # self.tiling = Tiling(self.master, self.canvas.canvas.img, self.canvas.selection_obj.start,
        #                      self.canvas.selection_obj.end, maps=self.folder_maps)
        self.tiling = Tiling(self.master, self.canvas.canvas.img, self.canvas.selection_obj.start,
                             self.canvas.selection_obj.end, self.canvas.selection_obj,
                             shear=self.canvas.selection_obj.coordinates,
                             maps=self.folder_maps)

    def do_popup(self, event=None):
        """ Right click event handler to open the popup menu.
        """
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.popup_menu.grab_release()

    # def crop_selected(self):
    #     img = self.canvas.selection_obj.crop()
    #     self.canvas.img = img
    #     self.canvas.pht_img = ImageTk.PhotoImage(self.canvas.img)
    #     self.canvas.canvas.itemconfig(self.canvas.displayed_img, image=self.canvas.pht_img)
    #     self.canvas.canvas.config(height=self.canvas.pht_img.height(), width=self.canvas.pht_img.width())
    #     self.canvas.selection_obj.height = self.canvas.pht_img.height()
    #     self.canvas.selection_obj.width = self.canvas.pht_img.width()
    #     self.canvas.selection_obj.clear()

    def save_selected(self):
        img = self.canvas.selection_obj.crop()
        file = filedialog.asksaveasfile(mode='w', defaultextension=".png")
        if file:
            abs_path = os.path.abspath(file.name)
            img.save(abs_path)  # saves the image to the input file name.

    def update_image(self):
        if self.tiling is not None:
            self.canvas.destroy()
            self.canvas = CanvasImage(self.master, img=self.tiling.tiled)  # create widget
            self.canvas.grid(row=0, column=0)
        else:
            tk.messagebox.showinfo("Update image with tiled texture",
                                   "Nothing to update. Start the tiling method before updating.")


if __name__ == '__main__':
    global TSTAMP
    global BATCH
    global COORDS
    global IMGPATH

    parser = argparse.ArgumentParser()
    # Adding optional argument
    parser.add_argument("-c", "--Coords", help="Insert manual coordinates for tiling.",
                        nargs=4, default=None, const=None, type=int)
    parser.add_argument("-t", "--Timestamp", help="Add timestamps to filename of saved images.",
                        nargs='?', default=None, const=True, type=bool)
    parser.add_argument("-b", "--Batch", help="Command line execution.",
                        nargs='?', default=None, const=True, type=bool)
    parser.add_argument("-i", "--Image", help="Path to the image to open.", nargs='?',
                        default="img/2fili.png", const="img/2fili.png", type=str)
    # parser.add_argument("-b", "--Batch", help="Batch mode.")
    # Read arguments from command line
    args = parser.parse_args()

    TSTAMP = args.Timestamp
    print("TSTAMP: ", TSTAMP)
    BATCH = args.Batch
    print("BATCH: ", BATCH)
    # COORDS = tuple(int(num) for num in args.Coords.strip("()").split(','))
    COORDS = args.Coords
    print("COORDS: ", COORDS)
    IMGPATH = args.Image
    print("IMGPATH: ", IMGPATH)

    TITLE = 'Tiling'
    root = tk.Tk()
    root.title(TITLE)
    root.geometry('%sx%s' % (WIDTH, HEIGHT))
    root.configure(background=BACKGROUND)
    if BATCH:
        print("cl mode")
        if IMGPATH is not None:
            image = Image.open(IMGPATH)
            coords = (0, 0, image.width, image.height) if COORDS is None else COORDS
            tiling = Tiling(root, image, (coords[0], coords[1]), (coords[2], coords[3]))  #TODO
        else:
            sys.exit('Cannot open image')
    else:
        app = Application(root, coords=COORDS, background=BACKGROUND, imgpath=IMGPATH)
        app.mainloop()
