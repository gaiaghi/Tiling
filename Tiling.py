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
from CanvasImage import CanvasImage
from CanvasImage import RectangleObject

OUT_DIR = './out/'
WIDTH, HEIGHT = 900, 900
BACKGROUND = '#292929'


#TODO dataclass ?
class Box:
    def __init__(self, img: Image.Image, left, top, right, bottom):
        self.og = img
        self.start = (left, top)  #TODO mettere x e y classe 2D coord?
        self.end = (right, bottom)
        self.img = img.crop((left, top, right, bottom))
        self.mat = np.array(self.img.convert('RGB'))

    def update(self, left, top, right, end):
        self.start = (left, top)
        self.end = (right, end)
        self.img = self.og.crop((left, top, right, end))
        self.mat = np.array(self.img.convert('RGB'))

    def set_end(self, right, bottom):
        self.end = (right, bottom)
        self._reload()

    def set_start(self, left, top):
        self.start = (left, top)
        self._reload()

    def _reload(self):
        self.img = self.og.crop((self.start[0], self.start[1], self.end[0], self.end[1]))
        self.mat = np.array(self.img.convert('RGB'))


class ShearBox(Box):
    def __init__(self, img: Image.Image, left, top, right, bottom, coordinates):
        self.og = img
        self.start = (left, top)
        self.end = (right, bottom)
        # self.img = img.crop((left, top, right, bottom))
        # self.mat = np.array(self.img.convert('RGB'))
        self.coord = coordinates
        self.width = max(self.coord[2][0], self.coord[3][0]) - min(self.coord[0][0], self.coord[1][0])
        self.height = max(self.coord[1][1], self.coord[2][1]) - min(self.coord[0][1], self.coord[3][1])

        rr, cc = line(int(self.coord[0][1]), int(self.coord[0][0]), int(self.coord[3][1]), int(self.coord[3][0]))
        self.v_line_pixels = list(zip(rr, cc))
        rr, cc = line(int(self.coord[0][1]), int(self.coord[0][0]), int(self.coord[1][1]), int(self.coord[1][0]))
        self.h_line_pixels = list(zip(rr, cc))
        print("h line "+ str(self.h_line_pixels))

        #TODO sposta codice e cambia border
        border = 5
        search_area = 0.15
        bo = int(self.width * search_area)
        print("larghezza sel " + str(self.width))

        theta = self.angle3(self.coord[1], self.coord[0], (self.coord[2][0], self.coord[0][1]))
        left_ends = [
            (int(self.coord[0][0] + border * math.cos(theta)), int(self.coord[0][1] + border * math.sin(theta))),
            (int(self.coord[3][0] + border * math.cos(theta)), int(self.coord[3][1] + border * math.sin(theta)))]
        print("self.coord " + str(self.coord))
        print("theta " + str(theta))
        print("left_ends " + str(left_ends))

        left_path = Path((self.coord[0], left_ends[0], left_ends[1], self.coord[3]))
        # xminL, yminL, xmaxL, ymaxL = np.asarray(left_path.get_extents(), dtype=int).ravel()

        #TODO parti da -search_area
        right_starts = [
            (int((self.coord[1][0] - bo) + border * math.cos(theta)), int(self.coord[1][1] + border * math.sin(theta))),
            (int((self.coord[2][0] - bo) + border * math.cos(theta)), int(self.coord[2][1] + border * math.sin(theta)))]
        right_ends = [(int((self.coord[1][0] - bo + border) + border * math.cos(theta)), right_starts[0][1]),
                      (int((self.coord[2][0] - bo + border) + border * math.cos(theta)), right_starts[1][1])]
        right_path = Path((right_starts[0], right_ends[0], right_ends[1], right_starts[1]))
        # xminR, yminR, xmaxR, ymaxR = np.asarray(right_path.get_extents(), dtype=int).ravel()

        # create a mesh grid for the whole image
        x, y = np.mgrid[:self.og.height, :self.og.width]
        # mesh grid to a list of points
        points = np.vstack((x.ravel(), y.ravel())).T
        # select points included in the path
        left_mask = left_path.contains_points(points)
        left_points = points[np.where(left_mask)]
        print("Left\n" + str(len(left_points)))
        print(left_points.shape)

        right_mask = right_path.contains_points(points)
        right_points = points[np.where(right_mask)]
        print("Right\n" + str(len(right_points)))
        print(right_points.shape)

        fig, ax = plt.subplots()

        # masked image plot
        img_mask = left_mask.reshape(x.shape).T
        ax.imshow(img * img_mask[..., None])
        idx = np.random.choice(np.arange(left_points.shape[0]), 200)
        ax.scatter(left_points[idx, 0], left_points[idx, 1], alpha=0.3, color='cyan')
        idx2 = np.random.choice(np.arange(right_points.shape[0]), 200)
        ax.scatter(right_points[idx2, 0], right_points[idx2, 1], alpha=0.3, color='yellow')

        fig.savefig("prova_points.jpg")

        # ---------ritagliare la selezione utente
        # image = self.og
        # background = Image.new("RGBA", image.size, (0, 0, 0, 0))
        # mask = Image.new("RGBA", image.size, 0)
        # draw = ImageDraw.Draw(mask)
        # draw.polygon((self.coord[0], self.coord[1], self.coord[2], self.coord[3]), fill='green', outline=None)
        # # prova = ImageTransform.QuadTransform((self.coord[0][0], self.coord[0][1], self.coord[1][0], self.coord[1][1],
        # #                                      self.coord[2][0], self.coord[2][1], self.coord[3][0], self.coord[3][1]))
        # new_img = Image.composite(image, background, mask)
        # new_img.show()
        #
        # selection = np.array(new_img)
        # extract = []
        # for line in selection:
        #     if not all(p[3] == 0 for p in line):
        #         extract.append(line)
        #
        # extract = np.array(extract)
        # idx = np.argwhere(np.all(extract[..., :] == 0, axis=0))
        # a2 = np.delete(extract, idx, axis=1)
        #
        # cropped = Image.fromarray(np.array(a2)[:,:,:3], mode='RGB')
        #
        # cropped.show()
        # print(a2.shape)

    @staticmethod
    def angle3(a, b, c):
        ang = math.degrees(math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(a[1] - b[1], a[0] - b[0]))
        return ang + 360 if ang < 0 else ang


class Tiling:
    #TODO (solo dopo) riorganizza classi in file diversi
    #TODO fai prove su mappe diverse, temporizza per il report
    #TODO prova a parallelizzare calcolo differenze

    # def __init__(self, master, image: Image.Image, selection: SelectionObject, border=5, search_area=0.15):
    def __init__(self, master, image: Image.Image, start, end, shear=None, border=5, search_area=0.15, maps=None,
                 start_tiling=True):
        # overlap border size with respect to the original image dimensions
        self.tiled = None
        self.master = master
        self.search_ratio = search_area
        # overlap border size
        self.border = border  #TODO prova con 5, 10 e 15, 25
        # original image
        self.image = image
        # start and end of selected area
        self.start = start
        self.end = end
        self.shear = shear  # coordinates of sheared rect
        self.maps = maps
        # width and height of the user-selected area
        self.width = self.end[0] - self.start[0]
        self.height = self.end[1] - self.start[1]
        # vertical search area (size)
        self.bv = int(self.height * self.search_ratio)
        # orizontal search area (size)
        self.bo = int(self.width * self.search_ratio)
        if self.bv < 1:
            self.bv = 1
        if self.bo < 1:
            self.bo = 1

        # self.module = Box(self.image, self.start[0], self.start[1],
        #                   self.end[0], self.end[1])

        # check if image overflow
        if (self.end[0] + self.bo) > self.image.width:
            start_h = (self.image.width - 2 * self.bo - self.border, self.start[1])
            end_h = (self.image.width - 2 * self.bo, self.end[1])
        else:
            start_h = (self.end[0] - self.bo, self.start[1])
            end_h = (self.end[0] - self.bo + self.border, self.end[1])

        # self.left_border = Box(self.image, self.start[0], self.start[1],
        #                        self.start[0] + self.border, self.end[1])
        # self.right_border = Box(self.image, start_h[0], start_h[1],
        #                         end_h[0], end_h[1])
        #
        # self.top_border = Box(image, self.start[0], self.start[1],
        #                       self.end[0], self.start[1] + self.border)

        if (self.end[1] + self.bv) > self.image.height:
            start_v = (self.start[0], self.image.height - 2 * self.bv - self.border)
            end_v = (self.end[0], self.image.height - 2 * self.bv)
        else:
            start_v = (self.start[0], self.end[1] - self.bv)
            end_v = (self.end[0], self.end[1] - self.bv + self.border)

        if self.shear is None:
            self._rect_setup(start_h, end_h, start_v, end_v)
        else:
            self._shear_setup()

        # self.bottom_border = Box(image, start_v[0], start_v[1], end_v[0], end_v[1])

        # crop_img = self.crop(self.image, self.start, self.end, self.bo, self.bv)
        # # user-selected image (with border) to matrix
        # matrix = crop_img.convert('RGB')
        # self.cropped = np.array(matrix)

        # start module search
        # if start_tiling:
        # self.start_search()

    def _rect_setup(self, start_h, end_h, start_v, end_v):
        self.module = Box(self.image, self.start[0], self.start[1],
                          self.end[0], self.end[1])

        self.left_border = Box(self.image, self.start[0], self.start[1],
                               self.start[0] + self.border, self.end[1])

        self.right_border = Box(self.image, start_h[0], start_h[1],
                                end_h[0], end_h[1])

        self.top_border = Box(image, self.start[0], self.start[1],
                              self.end[0], self.start[1] + self.border)

        self.bottom_border = Box(image, start_v[0], start_v[1], end_v[0], end_v[1])

        # crop_img = self.crop(self.image, self.start, self.end, self.bo, self.bv)
        # # user-selected image (with border) to matrix
        # matrix = crop_img.convert('RGB')
        # self.cropped = np.array(matrix)

    def _shear_setup(self):
        sheared = ShearBox(self.image, self.start[0], self.start[1], self.end[0], self.end[1], self.shear)

    def start_search(self):
        # TODO togli tutte le stampe
        og_img = self.image.convert('RGB')
        og_img = np.array(og_img)
        h_diff_values = []
        v_diff_values = []
        txt_path = os.path.join(OUT_DIR, "search_info.txt")
        f = open(txt_path, "w")

        # ricerca orizzontale
        # print("h border search area (size) " + str(self.bo))
        # print("width " + str(self.width) + " border search area ratio " + str(self.search_ratio))
        step = 0
        min_diff_right = (1, 0)  # tuple containing (min difference, step)

        # bordo sinistro partendo dalla coordinata 0 della selezione dell'utenete
        left_border = self.left_border.mat

        f.write("#left" + str(self.left_border.start) + " " + str(self.left_border.end) + "\n")

        start_time = time.time()
        #+++++++++++ fissato a sx, sposto il bordo di dx
        while step < 2 * self.bo:  # ricerca  nell'area tra -bo e +bo

            r_start = (self.right_border.start[0] + step, self.right_border.start[1])
            r_end = (self.right_border.end[0] + step, self.right_border.end[1])

            right_border = og_img[r_start[1]: r_end[1], r_start[0]: r_end[0], :]

            diff = self.normalize(right_border) - self.normalize(left_border)
            m_norm = sum(sum(sum(abs(diff)))) / right_border.size  # Manhattan norm
            if m_norm < min_diff_right[0]:
                min_diff_right = (m_norm, step)
            h_diff_values.append(m_norm)
            step += 1
            f.write(str(step) + " " + str(r_start) + " " + str(r_end) + " " + str(m_norm) + "\n")

        print("Minimun (h) distanze between borders find at step " + str(min_diff_right[1]) + ": " + str(
            min_diff_right[0]))

        #++++++++++++++++++++++++++++++++++++++++++++++++++
        # vertical search
        step = 0
        min_diff_bottom = (1, 0)  # tuple containing (min difference, step)

        # bordo top partendo dalla coordinata 0 della selezione dell'utenete
        top_border = self.top_border.mat

        f.write("\n\n#top" + str(self.top_border.start) + " " + str(self.top_border.end) + "\n")
        # +++++++++++ fissato top, sposto il bordo bottom
        while step < 2 * self.bv:  # ricerca  nell'area tra -bo e +bo

            b_start = (self.bottom_border.start[0], self.bottom_border.start[1] + step)
            b_end = (self.bottom_border.end[0], self.bottom_border.end[1] + step)

            bottom_border = og_img[b_start[1]: b_end[1], b_start[0]: b_end[0], :]
            # TODO  ricontrolla normalize
            diff = self.normalize(bottom_border) - self.normalize(top_border)
            m_norm = sum(sum(sum(abs(diff)))) / bottom_border.size  # Manhattan norm
            if m_norm < min_diff_bottom[0]:
                min_diff_bottom = (m_norm, step)
            v_diff_values.append(m_norm)
            step += 1
            f.write(str(step) + " " + str(b_start) + " " + str(b_end) + " " + str(m_norm) + "\n")

        end_time = time.time()

        print("Minimun (v) distanze between borders find at step " + str(min_diff_bottom[1]) + ": " + str(
            min_diff_bottom[0]))

        f.write("\n\n tot time: " + str(end_time - start_time) + " sec\n")
        #++++++++++++++++++++++++++++++++++++++++++++++++++
        # chiusura file dati
        f.close()

        #aggiornamento valori bordo dx
        self.right_border.update(self.right_border.start[0] + min_diff_right[1], self.right_border.start[1],
                                 self.right_border.end[0] + min_diff_right[1], self.right_border.end[1])

        #aggiornamento valori bordo sotto
        self.bottom_border.update(self.bottom_border.start[0], self.bottom_border.start[1] + min_diff_bottom[1],
                                  self.bottom_border.end[0], self.bottom_border.end[1] + min_diff_bottom[1])

        # definizione estremi del modulo
        self.module.set_end(self.right_border.start[0],
                            self.bottom_border.start[1])
        self.module.set_start(self.start[0], self.start[1])

        # left, top, right, bottom
        module = self.image.crop((self.module.start[0], self.module.start[1], self.module.end[0], self.module.end[1]))

        # tile extracted module
        imgm = Image.fromarray(np.array(module.convert('RGB')), mode='RGB')
        self.tiled = self.tile_image(imgm)

        self.save_img(self.left_border.img, 'left_border.png')
        self.save_img(self.right_border.img, 'right_border.png')
        self.save_img(self.top_border.img, 'top_border.png')
        self.save_img(self.bottom_border.img, 'bottom_border.png')

        imgc = Image.fromarray(np.array(self.crop(self.image, self.start, self.end).convert('RGB')), mode='RGB')
        # print("selection crop "+str(self.selection.width)+" x "+str(self.selection.height))
        self.save_img(imgc, 'user_crop.png')

        self.save_img(self.tiled, file_name="tiled.png")

        self.save_img(imgm, 'extracted_module.png')

        # area di ricerca
        search_area = og_img[self.start[1]: self.end[1],
                      self.end[0] - self.bo: self.end[0] + self.bo, :]
        imgs = Image.fromarray(search_area, mode='RGB')
        self.save_img(imgs, 'search_area.png')

        self.plot(h_diff_values, self.bo, file_name="h_plot.png")
        self.plot(v_diff_values, self.bv, file_name="v_plot.png")
        # return self.tiled

        if self.maps is not None:
            self.crop_maps()

    # def _drop_alpha(self, img):
    #     return img if img.shape[-1] == 3 else img[:, :, 1:]

    def crop_maps(self):
        for f in self.maps:
            img = Image.open(f)
            if img.width == self.image.width and img.height == self.image.height:
                img = img.crop((self.module.start[0], self.module.start[1], self.module.end[0], self.module.end[1]))
                # self.tiled = self.tile_image(imgm)
                # self.save_img(self.tiled, file_name="tiled.png")
                img_name = os.path.basename(f)
                name = os.path.splitext(img_name)[0] + "_Module" + os.path.splitext(img_name)[1]
                self.save_img(img, file_name=name)
            else:
                print("Texture map " + os.path.basename(f) + " has not the same dimensions of the processed texture.")
            img.close()

    def crop(self, img: Image.Image, start, end, h_border=0, v_border=0) -> Image.Image:
        # left, top, right, bottom = self._get_coords(self.start, self.end)
        left, top = start
        right, bottom = end
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
                             self.canvas.selection_obj.end, shear=self.canvas.selection_obj.coordinates,
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
            tiling = Tiling(root, image, (coords[0], coords[1]), (coords[2], coords[3]))
        else:
            sys.exit('Cannot open image')
    else:
        app = Application(root, coords=COORDS, background=BACKGROUND, imgpath=IMGPATH)
        app.mainloop()
