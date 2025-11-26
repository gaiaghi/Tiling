from settings import *
import os
import os.path
import math
import time
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw
from datetime import datetime
from skimage.draw import line
import Selection
from utils import Coordinates, TwoDPoint


class Tiling:
    #TODO
    # temporizza
    # prova a parallelizzare calcolo differenze

    # def __init__(self, master, image: Image.Image, selection: SelectionObject, border=5, search_area=0.15):
    def __init__(self, img: Image.Image, start: TwoDPoint, end: TwoDPoint, selection: Selection,
                 shear: Coordinates = None, border=10,
                 search_area=0.25,
                 maps=None, weights=None, start_tiling=True, filename="", timestamp=True):
        self.TSTAMP = timestamp
        # self.percorso = percorso
        self.weight_file = weights
        self.filename = filename
        self.selection = selection
        self.tiled = None
        self.cmod = None
        # self.master = master
        self.search_ratio = search_area
        # overlap border size
        self.border = border
        self.image = img  # original image
        # start and end of selected area
        self.start = start
        self.end = end
        self.gc_margin = 72

        if shear is None:
            self.shear = Coordinates((start.x, start.y), (end.x, start.y), (start.x, end.y), (end.x, end.y))
        else:
            self.shear = Coordinates(shear[0], shear[1], shear[2], shear[3])  # coordinates of sheared rect

        if type(self.selection).__name__ == "ShearRectangle":
            self.start.x = self.shear.min()[0]
            self.start.y = self.shear.min()[1]
            self.end.x = self.shear.max()[0]
            self.end.y = self.shear.max()[1]
            print("update start, end ", self.start.x, self.start.y, self.end.x, self.end.y)

        self.maps_path = maps  # all image maps
        # width and height of the user-selected area
        # self.start.x = 203  #TODO rimuovi
        # self.start.y = 214
        # self.end.x = 430
        # self.end.y = 659
        # self.shear.A.x = 203
        # self.shear.A.y = 214
        # self.shear.B.x = 430
        # self.shear.B.y = 214
        # self.shear.C.x = 430
        # self.shear.C.y = 659
        # self.shear.D.x = 203
        # self.shear.D.y = 659
        self.delta_idx_RL = None
        self.delta_idx_TB = None
        # self.width = self.end.x - self.start.x
        # self.height = self.end.y - self.start.y
        self.width = abs(self.shear.B.x - self.shear.A.x)
        self.height = abs(self.shear.D.y - self.shear.A.y)
        # vertical search area (size)
        self.bv = int(self.height * self.search_ratio)
        # horizontal search area (size)
        self.bo = int(self.width * self.search_ratio)

        if self.maps_path is not None:
            if self.weight_file is not None:
                with open(self.weight_file) as f:
                    txt = f.read()
                    weights = list(map(int, txt.split(";")))
                if len(weights) != len(self.maps_path):
                    weights = list(np.ones(len(self.maps_path), dtype=int))
                    print("self.weights ", weights)
            else:
                weights = list(np.ones(len(self.maps_path), dtype=int))
                print("weights... ", weights)

            self.maps = np.array(Image.open(self.maps_path[0] * weights[0]))
            for i in range(1, len(self.maps_path)):
                m = self.maps_path[i]
                self.maps = np.dstack((self.maps, np.array(Image.open(m)) * math.sqrt(weights[i])))
            # for m in self.maps_path[1:]:
            #     self.maps = np.dstack((self.maps, np.array(Image.open(m))))
            print("shape maps ", self.maps.shape)
        else:
            self.maps = np.array(self.image)

        if self.bv < 1:
            self.bv = 1
        if self.bo < 1:
            self.bo = 1
        print("bo, bv ", self.bo, self.bv)

        # check if image overflow
        #TODO idea: se shear overflow1 (orizzontale) allora, in realtà potrebbe essere da spostare anche il bottom
        # ma in che direzione? questo è da capire
        if (self.end.x + self.bo + self.border) > self.image.width:
            start_h = (self.image.width - 2 * self.bo - self.border, self.start.y)
            end_h = (self.image.width - 1 - 2 * self.bo, self.end.y)
            print("overflow1")
        else:
            start_h = (self.end.x - self.bo + 1, self.start.y)
            end_h = (self.end.x - self.bo + self.border, self.end.y)

        if (self.end.y + self.bv + self.border) > self.image.height:
            start_v = (self.start.x, self.image.height - 2 * self.bv - self.border)
            end_v = (self.end.x, self.image.height - 2 * self.bv - 1)
            print("overflow2")
        else:
            start_v = (self.start.x, self.end.y - self.bv + 1)
            end_v = (self.end.x, self.end.y - self.bv + self.border)

        self.left_pixels = self.get_line(self.shear.A, self.shear.D)
        self.right_pixels = self.get_line(self.shear.B, self.shear.C)
        self.top_pixels = self.get_line(self.shear.A, self.shear.B)
        self.bottom_pixels = self.get_line(self.shear.D, self.shear.C)

        self.delta_idx_RL = [(p[0] - self.right_pixels[0][0], p[1] - self.right_pixels[0][1]) for p in
                             self.right_pixels]
        self.delta_idx_TB = [(p[0] - self.top_pixels[0][0], p[1] - self.top_pixels[0][1]) for p in self.top_pixels]

        # Borders setup
        if type(self.selection).__name__ == "RectangleObject":
            self._rect_setup(start_h, end_h, start_v, end_v)
        elif type(self.selection).__name__ == "ShearRectangle":
            self._shear_setup(start_h, end_h, start_v, end_v)
        # self._rect_setup(start_h, end_h, start_v, end_v)

        # start module search
        if start_tiling:
            self.start_search()

    def _rect_setup(self, start_h, end_h, start_v, end_v):
        self.left_border = Coordinates((self.start[0], self.start[1]),
                                       (self.start[0] + self.border - 1, self.start[1]),
                                       (self.start[0] + self.border - 1, self.end[1]),
                                       (self.start[0], self.end[1]))

        self.right_border = Coordinates((start_h[0], start_h[1]),
                                        (end_h[0], start_h[1]),
                                        (end_h[0], end_h[1]),
                                        (start_h[0], end_h[1]))

        self.top_border = Coordinates((self.start[0], self.start[1]),
                                      (self.end[0], self.start[1]),
                                      (self.end[0], self.start[1] + self.border - 1),
                                      (self.start[0], self.start[1] + self.border - 1), )

        self.bottom_border = Coordinates((start_v[0], start_v[1]),
                                         (end_v[0], start_v[1]),
                                         (end_v[0], end_v[1]),
                                         (start_v[0], end_v[1]))
        print("left b ", self.left_border)
        print("right b ", self.right_border)
        print("top b ", self.top_border)
        print("bottom b ", self.bottom_border)

        # crop_img = self.crop(self.image, self.start, self.end, self.bo, self.bv)
        # # user-selected image (with border) to matrix
        # matrix = crop_img.convert('RGB')
        # self.cropped = np.array(matrix)

    def _shear_setup(self, start_h, end_h, start_v, end_v):

        self.left_border = Coordinates((self.shear.A.x, self.shear.A.y), self.top_pixels[self.border - 1],
                                       self.bottom_pixels[self.border - 1], (self.shear.D.x, self.shear.D.y))

        self.right_border = Coordinates(self.top_pixels[-self.bo],
                                        self.tuple_sum(self.top_pixels[-self.bo], self.delta_idx_TB[self.border - 1]),
                                        self.tuple_sum(self.bottom_pixels[-self.bo],
                                                       self.delta_idx_TB[self.border - 1]),
                                        self.bottom_pixels[-self.bo])

        self.top_border = Coordinates((self.shear.A.x, self.shear.A.y),
                                      (self.shear.B.x, self.shear.B.y),
                                      self.right_pixels[self.border - 1],
                                      self.left_pixels[self.border - 1], )

        self.bottom_border = Coordinates(self.left_pixels[-self.bv],
                                         self.right_pixels[-self.bv],
                                         self.tuple_sum(self.right_pixels[-self.bv],
                                                        self.delta_idx_RL[self.border - 1]),
                                         self.tuple_sum(self.left_pixels[-self.bv], self.delta_idx_RL[self.border - 1]))

        print("self left" + str(self.left_border))
        print("self right" + str(self.right_border))
        print("self top" + str(self.top_border))
        print("self bottom" + str(self.bottom_border))

    # def _get_masked_img(self, a, b, c, d):
    def _get_masked_img(self, image: Image.Image, a, b, c, d, px=None):
        print("a,b,c,d -> ", a, b, c, d)
        # image = self.image
        background = Image.new("RGBA", image.size, (0, 0, 0, 0))
        mask = Image.new("RGBA", image.size, 0)
        draw = ImageDraw.Draw(mask)
        if px is None:
            draw.polygon(((a[0], a[1]), (b[0], b[1]),
                          (c[0], c[1]), (d[0], d[1])), fill='green',
                         outline=None)
        else:
            draw.polygon(px, fill='green',
                         outline=None)
        minx = min(a[0], b[0], c[0], d[0])
        maxx = max(a[0], b[0], c[0], d[0])
        miny = min(a[1], b[1], c[1], d[1])
        maxy = max(a[1], b[1], c[1], d[1])
        new_img = Image.composite(image, background, mask)
        # if px is not None: # solo per testing
        #     testimg = copy(self.image)
        #     testdr = ImageDraw.Draw(testimg)
        #     testdr.polygon(px)
        #     testimg.save("test.png")
        #     new_img.save("composite.png")
        if a[0] == d[0] or a[1] == b[1]:
            new_img.crop((minx, miny, maxx + 1, maxy + 1)).save(
                OUT_DIR + os.path.splitext(self.filename)[0] + "_" + "OG_Module.png")
            new_img = self.reshape_module(a, b, c, d, new_img)
        else:
            new_img = new_img.crop((minx, miny, maxx + 1, maxy + 1))

        return new_img

    def reshape_module(self, a, b, c, d, img):
        imgmat = np.array(img)
        stx = a[0]
        endx = c[0]
        sty = a[1]
        endy = c[1]
        if a[0] == d[0]:
            #   |\
            #   |  \
            #   |   |
            #    \  |
            #      \|

            if a[1] < b[1]:
                if d[1] > b[1]:
                    print("----caso 1, taglio 1")
                    imgmat = self.cut_paste(imgmat, a[1], b[1], a[0], b[0], d[1] + 1, c[1] + 1, d[0], c[0])

                    sty = b[1]
                    endy = c[1]
                else:
                    print("----caso 1, taglio 2")
                    dy = d[1] - a[1]
                    imgmat = self.cut_paste(imgmat, a[1], d[1], a[0], b[0], d[1] + 1, d[1] + dy + 1, a[0], b[0])

                    dy2 = c[1] - (d[1] + dy)
                    imgmat = self.cut_paste(imgmat, d[1] + dy, c[1], a[0], b[0] + 1, b[1] - dy2 - 1, b[1] - 1, a[0],
                                            b[0] + 1)

                    sty = d[1]
                    endy = d[1] + dy

            else:
                if c[1] > a[1]:
                    print("-----caso 2, taglio 1")
                    imgmat = self.cut_paste(imgmat, b[1], a[1] + 1, a[0], b[0] + 1, c[1] + 1, d[1] + 2, a[0], b[0] + 1)

                    sty = a[1]
                    endy = d[1]
                else:
                    print("-----caso 2, taglio 2")
                    dy = c[1] - b[1]
                    imgmat = self.cut_paste(imgmat, b[1], c[1], a[0], b[0] + 1, c[1] + 1, c[1] + dy + 1, a[0], b[0] + 1)

                    dy2 = d[1] - (c[1] + dy)
                    imgmat = self.cut_paste(imgmat, c[1] + dy, d[1] + 1, a[0], b[0], a[1] - dy2 - 1, a[1], a[0], b[0])

                    sty = c[1]
                    endy = d[1] - dy2

            # img = Image.fromarray(imgmat).crop((stx, sty, endx, endy))
        elif a[1] == b[1]:
            #     ____________
            #     \           \
            #      \           \
            #       ------------
            stx = a[0]
            endx = b[0]
            sty = a[1]
            endy = c[1]
            if a[0] < d[0]:
                if d[0] < b[0]:
                    print("-----caso 3, taglio 1")
                    imgmat = self.cut_paste(imgmat, b[1], c[1] + 1, b[0], c[0] + 1, a[1], c[1] + 1, a[0] - 1, d[0])
                else:
                    print("-----caso 3, taglio 2")
                    dx = c[0] - d[0]
                    imgmat = self.cut_paste(imgmat, a[1], c[1] + 1, d[0], c[0], a[1], c[1] + 1, d[0] - dx - 1, d[0] - 1)
                    dx2 = (d[0] - dx) - a[0]
                    imgmat = self.cut_paste(imgmat, a[1], d[1] + 1, a[0], a[0] + dx2, a[1], d[1] + 1, b[0] + 1,
                                            b[0] + dx2 + 1)
                    stx = d[0] - dx
                    endx = d[0]
            else:
                if a[0] < c[0]:
                    print("-----caso 4, taglio 1")
                    imgmat = self.cut_paste(imgmat, b[1], c[1], c[0], b[0], b[1], c[1], d[0] - 1, a[0] - 1)
                    stx = d[0]
                    endx = c[0]
                else:
                    print("-----caso 4, taglio 2")
                    dx = b[0] - a[0]
                    imgmat = self.cut_paste(imgmat, a[1], c[1], a[0], b[0], a[1], c[1], a[0] - dx - 1, a[0] - 1)
                    dx2 = a[0] - c[0]
                    imgmat = self.cut_paste(imgmat, a[1], c[1] + 1, d[0], d[0] + dx2, a[1], c[1] + 1, c[0] + 1,
                                            c[0] + dx2 + 1)
                    stx = a[0] - dx
                    endx = a[0]
        img = Image.fromarray(imgmat).crop((stx, sty, endx + 1, endy + 1))
        # else:
        #     new_img = new_img.crop((minx, miny, maxx + 1, maxy + 1))
        #     mask.save("mask.png")
        return img

    @staticmethod
    def cut_paste(imgmat, s1_r, e1_r, s1_c, e1_c, s2_r, e2_r, s2_c, e2_c):

        crop = imgmat[s1_r:e1_r, s1_c:e1_c]
        idx = list(range(s2_r, e2_r))
        idy = list(range(s2_c, e2_c))
        tmp = imgmat[np.ix_(idx, idy)]
        ids = crop != 0
        tmp[ids] = crop[ids]
        imgmat[np.ix_(idx, idy)] = tmp

        return imgmat

    def start_search(self):
        og_img = np.array(self.image)
        h_diff_values = []
        v_diff_values = []
        txt_path = os.path.join(OUT_DIR, "search_info.txt")
        f = open(txt_path, "w")

        # ricerca orizzontale
        step = 0
        min_diff_right = (1, 0)  # tuple containing (min difference, step)
        # bordo sinistro partendo dalla coordinata 0 della selezione dell'utenete (fissato)
        left_border = self.selection.get_mat(self.maps, (self.left_border.A, self.left_border.B,
                                                         self.left_border.C, self.left_border.D),
                                             self.delta_idx_TB[:self.border], self.delta_idx_RL)

        f.write("#left" + str(self.left_border.start) + " " + str(self.left_border.end) + "\n")

        start_time = time.time()

        tmp_right = Coordinates((self.right_border.A.x, self.right_border.A.y),
                                (self.right_border.B.x, self.right_border.B.y),
                                (self.right_border.C.x, self.right_border.C.y),
                                (self.right_border.D.x, self.right_border.D.y))
        min_right_border = Coordinates(tmp_right.A.tuple, tmp_right.B.tuple, tmp_right.C.tuple,
                                       tmp_right.D.tuple)
        #+++++++++++ fissato a sx, sposto il bordo di dx
        while step < 2 * self.bo and tmp_right.B.x < self.image.width and tmp_right.C.x < self.image.width:  # ricerca nell'area tra -bo e +bo

            right = self.selection.get_mat(self.maps, (tmp_right.A, tmp_right.B,
                                                       tmp_right.C, tmp_right.D),
                                           self.delta_idx_TB[:self.border], self.delta_idx_RL)

            m_norm = math.sqrt(np.sum(np.power(right - left_border, 2))) / right.size
            if m_norm < min_diff_right[0]:
                min_diff_right = (m_norm, step)
                min_right_border = Coordinates(tmp_right.A.tuple, tmp_right.B.tuple, tmp_right.C.tuple,
                                               tmp_right.D.tuple)

            h_diff_values.append(m_norm)
            step += 1
            tmp_right = Coordinates(self.tuple_sum(self.right_border.A, self.delta_idx_TB[step]),
                                    self.tuple_sum(self.right_border.A, self.delta_idx_TB[step + self.border - 1]),
                                    self.tuple_sum(self.right_border.D, self.delta_idx_TB[step + self.border - 1]),
                                    self.tuple_sum(self.right_border.D, self.delta_idx_TB[step]))
            f.write(str(step) + " " + str(tmp_right) + " " + str(m_norm) + "\n")

        print("Min (h) distanze between borders find at step " + str(min_diff_right[1] - self.bo) + ": " + str(
            min_diff_right[0]))

        #++++++++++++++++++++++++++++++++++++++++++++++++++
        # vertical search
        step = 0
        min_diff_bottom = (1, 0)  # tuple containing (min difference, step)

        # bordo top partendo dalla coordinata 0 della selezione dell'utenete
        top_border = self.selection.get_mat(self.maps, (self.top_border.A, self.top_border.B,
                                                        self.top_border.C, self.top_border.D),
                                            self.delta_idx_TB, self.delta_idx_RL[:self.border])

        f.write("\n\n#top" + str(self.top_border.start) + " " + str(self.top_border.end) + "\n")

        # +++++++++++ fissato top, sposto il bordo bottom
        tmp_bottom = Coordinates((self.bottom_border.A.x, self.bottom_border.A.y),
                                 (self.bottom_border.B.x, self.bottom_border.B.y),
                                 (self.bottom_border.C.x, self.bottom_border.C.y),
                                 (self.bottom_border.D.x, self.bottom_border.D.y))
        min_bottom_border = Coordinates(tmp_bottom.A.tuple, tmp_bottom.B.tuple,
                                        tmp_bottom.C.tuple, tmp_bottom.D.tuple)
        while step < 2 * self.bv and tmp_right.C.y < self.image.width and tmp_right.D.y < self.image.height:
            bottom = self.selection.get_mat(self.maps, (tmp_bottom.A, tmp_bottom.B,
                                                        tmp_bottom.C, tmp_bottom.D),
                                            self.delta_idx_TB, self.delta_idx_RL[:self.border])

            m_norm = math.sqrt(np.sum(np.power(bottom - top_border, 2))) / bottom.size
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

        end_time = time.time()

        print("Min (v) distanze between borders find at step " + str(min_diff_bottom[1] - self.bv) + ": " + str(
            min_diff_bottom[0]))

        f.write("\n\n tot time: " + str(end_time - start_time) + " sec\n")
        #++++++++++++++++++++++++++++++++++++++++++++++++++
        # chiusura file dati
        f.close()

        self.bottom_border = min_bottom_border
        self.right_border = min_right_border

        iname = os.path.splitext(self.filename)[0] + "_"
        module_img = None
        mod_coord = None
        if type(self.selection).__name__ == "RectangleObject":
            mod_coord = (self.start[0], self.start[1], self.right_border.start.x, self.bottom_border.start.y)

            module = self.image.crop(mod_coord)
            module_img = Image.fromarray(np.array(module.convert('RGBA')), mode='RGBA')

            self.save_img(module_img, iname + 'Module.png')

            deltaXS = self.start[0] - self.gc_margin
            deltaXE = self.right_border.start.x + self.gc_margin
            deltaYS = self.start[1] - self.gc_margin
            deltaYE = self.bottom_border.start.y + self.gc_margin
            margin_mod_coords = (deltaXS if deltaXS > 0 else 0,
                                 deltaYS if deltaYS > 0 else 0,
                                 deltaXE if deltaXE < self.image.width else self.image.width,
                                 deltaYE if deltaYE < self.image.height else self.image.height)
            margin_module = self.image.crop(margin_mod_coords)
            margin_module_img = Image.fromarray(np.array(margin_module.convert('RGBA')), mode='RGBA')
            self.save_img(margin_module_img, iname + 'Module+MARGIN.png')

            if self.maps_path is not None:
                self.crop_maps(mod_coord)
            mod_coord = [(mod_coord[0], mod_coord[1]), (mod_coord[2], mod_coord[1]),
                         (mod_coord[2], mod_coord[3]), (mod_coord[0], mod_coord[3])]

        elif type(self.selection).__name__ == "ShearRectangle":
            #+1 per includere una riga di sovrapposizione
            print("top pixels s e ", self.top_pixels[0], self.top_pixels[-1])
            print("bottom pixels s e ", self.bottom_pixels[0], self.bottom_pixels[-1])
            print("left pixels s e ", self.left_pixels[0], self.left_pixels[-1])
            print("right pixels s e ", self.right_pixels[0], self.right_pixels[-1])
            tpx = self.top_pixels[:-(self.bo - min_diff_right[1]) + 1] if min_diff_right[
                                                                              1] + 1 < self.bo else self.top_pixels
            if min_diff_right[1] + 1 >= self.bo:
                p = self.top_pixels[-1]
                tail = [(p[0] + delta[0], p[1] + delta[1]) for delta in
                        self.delta_idx_TB[:(min_diff_right[1] - self.bo + 1)]]
                tpx = tpx + tail
            lpx = self.left_pixels[:-(self.bv - min_diff_bottom[1]) + 1] if min_diff_bottom[
                                                                                1] + 1 < self.bv else self.left_pixels
            if min_diff_bottom[1] + 1 >= self.bv:
                p = self.left_pixels[-1]
                tail = [(p[0] + delta[0], p[1] + delta[1]) for delta in
                        self.delta_idx_RL[:(min_diff_bottom[1] - self.bv + 1)]]
                lpx = lpx + tail

            delta_lpx = [(p[0] - lpx[0][0], p[1] - lpx[0][1]) for p in lpx]
            delta_tpx = [(p[0] - tpx[0][0], p[1] - tpx[0][1]) for p in tpx]
            rpx = [(tpx[-1][0] + delta[0], tpx[-1][1] + delta[1]) for delta in delta_lpx]

            bpx = [(lpx[-1][0] + delta[0], lpx[-1][1] + delta[1]) for delta in delta_tpx]
            module_img = self._get_masked_img(self.image, tpx[0], rpx[0],
                                              # self.line_intersection((p1, p2), (p3, p4)),
                                              rpx[-1], lpx[-1],
                                              tpx + rpx + bpx[::-1] + lpx[::-1])
            mod_coord = [tpx[0], rpx[0], rpx[-1], lpx[-1]]

            if self.maps_path is not None:
                self.crop_maps([tpx[0], rpx[0], rpx[-2], lpx[-2]], tpx=tpx, rpx=rpx, lpx=lpx, bpx=bpx)
                # for f in self.maps_path:
                #     m = self._get_masked_img(Image.open(f), tpx[0], rpx[0],
                #                              rpx[-1], lpx[-1],
                #                              tpx + rpx + bpx[::-1] + lpx[::-1])
                #     img_name = os.path.basename(f)
                #     name = os.path.splitext(img_name)[0] + "_Module" + os.path.splitext(img_name)[1]
                #     self.save_img(m, name)
            else:
                # module_save = self._get_masked_img(self.image, tpx[0], rpx[0],
                #                                    rpx[-2], lpx[-2],
                #                                    tpx + rpx + bpx[::-2] + lpx[::-2])
                #TODO ritaglia modulo e rendilo quadrato se shear in una sola dimensione
                self.save_img(module_img, iname + 'Module.png')

            # rrrrr = self._get_masked_img(self.left_border.A, self.left_border.B,
            #                              self.left_border.C, self.left_border.D)
            # self.save_img(rrrrr, 'LEFT.png')
            #
            # llll = self._get_masked_img(self.right_border.A, self.right_border.B,
            #                             self.right_border.C, self.right_border.D)
            # self.save_img(llll, 'RIGHT.png')

            # tiled = self.tile_image(Image.fromarray(module_img, mode='RGBA'), [tpx[0], rpx[0], rpx[-1], lpx[-1]])

        self.tiled = self.selection.tile_image(module_img, mod_coord)
        self.cmod = mod_coord
        self.save_img(self.tiled, file_name=iname + "tiled.png")
        self.plot(h_diff_values, self.bo, file_name=iname + "h_plot.png")
        self.plot(v_diff_values, self.bv, file_name=iname + "v_plot.png")

    def crop_maps(self, coord, lpx=None, rpx=None, tpx=None, bpx=None):
        mss = False
        img = None
        for f in self.maps_path:
            imgog = Image.open(f)
            if imgog.width == self.image.width and imgog.height == self.image.height:
                name = os.path.basename(f)
                margin_name = os.path.splitext(name)[0] + "_Module+MARGIN" + os.path.splitext(name)[1]
                name = os.path.splitext(name)[0] + "_Module" + os.path.splitext(name)[1]
                if type(self.selection).__name__ == "RectangleObject":
                    img = imgog.crop(coord)

                    deltaXS = self.start[0] - self.gc_margin
                    deltaXE = self.right_border.start.x + self.gc_margin
                    deltaYS = self.start[1] - self.gc_margin
                    deltaYE = self.bottom_border.start.y + self.gc_margin
                    margin_mod_coords = (deltaXS if deltaXS > 0 else 0,
                                         deltaYS if deltaYS > 0 else 0,
                                         deltaXE if deltaXE < self.image.width else self.image.width,
                                         deltaYE if deltaYE < self.image.height else self.image.height)
                    margin_module = imgog.crop(margin_mod_coords)
                    # margin_module_img = Image.fromarray(np.array(margin_module.convert('RGBA')), mode='RGBA')
                    self.save_img(margin_module, margin_name)

                elif type(self.selection).__name__ == "ShearRectangle":
                    img = self._get_masked_img(imgog, tpx[0], rpx[0],
                                               rpx[-1], lpx[-1],
                                               tpx + rpx + bpx[::-1] + lpx[::-1])

                self.save_img(img, file_name=name)
            else:
                print("Texture map " + os.path.basename(f) + " has not the same dimensions of the processed texture.")
            img.close()

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

    def save_img(self, img: Image.Image, file_name="image.png"):
        ts = self.TSTAMP
        currTS2 = datetime.now().strftime("%Y%m%d%H%M%S_") if self.TSTAMP else ""
        file_path = os.path.join(OUT_DIR, currTS2 + file_name)
        if not os.path.isdir(OUT_DIR):
            os.mkdir(OUT_DIR)
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
        currTS2 = datetime.now().strftime("%Y%m%d%H%M%S_") if self.TSTAMP else ""
        file_path = os.path.join(OUT_DIR, currTS2 + file_name)
        # file_path = os.path.join(OUT_DIR, file_name)
        fig.savefig(file_path)
        plt.close()

    @staticmethod
    def tuple_sum(a, b):
        return tuple([sum(x) for x in zip(a, b)])
