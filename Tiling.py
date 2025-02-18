import os
import os.path
import tkinter as tk
import numpy as np
from tkinter import filedialog
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image, ImageTk
from datetime import datetime

from CanvasImage import CanvasImage
from CanvasImage import SelectionObject
from CanvasImage import MousePositionTracker

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


class Tiling:
    def __init__(self, master, image: Image.Image, selection: SelectionObject, border=5, search_area=0.15):
        # overlap border size with respect to the original image dimensions
        self.tiled = None
        self.master = master
        self.search_ratio = search_area
        # overlap border size
        self.border = border  #TODO prova con 5, 10 e 15, 25
        # original image
        self.image = image
        # user selection
        self.selection = selection

        # width and height of the user-selected area
        self.width = self.selection.end[0] - self.selection.start[0]
        self.height = self.selection.end[1] - self.selection.start[1]
        # vertical search area (size)
        self.bv = int(self.height * self.search_ratio)
        # orizontal search area (size)
        self.bo = int(self.width * self.search_ratio)
        if self.bv < 1:
            self.bv = 1
        if self.bo < 1:
            self.bo = 1

        self.module = Box(image, self.selection.start[0], self.selection.start[1],
                          self.selection.end[0], self.selection.end[1])

        if (self.selection.end[0] + self.bo) > self.image.width:
            start_h = (self.image.width - 2 * self.bo - self.border, self.selection.start[1])
            end_h = (self.image.width - 2 * self.bo, self.selection.end[1])
        else:
            start_h = (self.selection.end[0] - self.bo, self.selection.start[1])
            end_h = (self.selection.end[0] - self.bo + self.border, self.selection.end[1])

        self.left_border = Box(image, self.selection.start[0], self.selection.start[1],
                               self.selection.start[0] + self.border, self.selection.end[1])
        self.right_border = Box(image, start_h[0], start_h[1],
                                end_h[0], end_h[1])

        self.top_border = Box(image, self.selection.start[0], self.selection.start[1],
                              self.selection.end[0], self.selection.start[1] + self.border)

        if (self.selection.end[1] + self.bv) > self.image.height:
            start_v = (self.selection.start[0], self.image.height - 2 * self.bv - self.border)
            end_v = (self.selection.end[0], self.image.height - 2 * self.bv)
        else:
            start_v = (self.selection.start[0], self.selection.end[1] - self.bv)
            end_v = (self.selection.end[0], self.selection.end[1] - self.bv + self.border)

        self.bottom_border = Box(image, start_v[0], start_v[1], end_v[0], end_v[1])

        crop_img = selection.crop(self.bo, self.bv)
        # user-selected image (with border) to matrix
        matrix = crop_img.convert('RGB')
        self.crop = np.array(matrix)

        # start module search
        self.start_search()

    def start_search(self):
        # TODO togli tutte le stampe
        # TODO modifica questione controllo/overflow bande se selezione sul bordo
        og_img = self.image.convert('RGB')
        og_img = np.array(og_img)
        h_diff_values = []
        v_diff_values = []

        # ricerca orizzontale
        print("h border search area (size) " + str(self.bo))
        print("width " + str(self.width) + " border search area ratio " + str(self.search_ratio))
        step = 0
        min_diff_right = (1, 0)  # tuple containing (min difference, step)

        # bordo sinistro partendo dalla coordinata 0 della selezione dell'utenete
        left_border = self.left_border.mat

        #+++++++++++ fissato a sx, sposto il bordo di dx
        while step < 2 * self.bo:  # ricerca  nell'area tra -bo e +bo
            print("############### STEP " + str(step))

            r_start = (self.right_border.start[0] + step, self.right_border.start[1])
            r_end = (self.right_border.end[0] + step, self.right_border.end[1])

            right_border = og_img[r_start[1]: r_end[1], r_start[0]: r_end[0], :]

            if step == 0:
                print("user selection coord " + str(self.selection.start) + " " + str(self.selection.end))
                print("orig. selected wxh = " + str(self.width) + "x" + str(self.height))
                print("left border shape = " + str(left_border.shape))
                print("right border shape = " + str(right_border.shape))

            diff = self.normalize(right_border) - self.normalize(left_border)
            m_norm = sum(sum(sum(abs(diff)))) / right_border.size  # Manhattan norm
            if m_norm < min_diff_right[0]:
                min_diff_right = (m_norm, step)
            h_diff_values.append(m_norm)
            print("diff (M norm): " + str(m_norm))
            step += 1

        print("Minimun (h) distanze between borders find at step " + str(min_diff_right[1]) + ": " + str(
            min_diff_right[0]))

        #++++++++++++++++++++++++++++++++++++++++++++++++++
        # vertical search
        step = 0
        min_diff_bottom = (1, 0)  # tuple containing (min difference, step)

        # bordo top partendo dalla coordinata 0 della selezione dell'utenete
        top_border = self.top_border.mat

        # +++++++++++ fissato top, sposto il bordo bottom
        while step < 2 * self.bv:  # ricerca  nell'area tra -bo e +bo
            print("############### v STEP " + str(step))

            b_start = (self.bottom_border.start[0], self.bottom_border.start[1] + step)
            b_end = (self.bottom_border.end[0], self.bottom_border.end[1] + step)

            bottom_border = og_img[b_start[1]: b_end[1], b_start[0]: b_end[0], :]

            if step == 0:
                print("user selection coord " + str(self.selection.start) + " " + str(self.selection.end))
                print("orig. selected wxh = " + str(self.width) + "x" + str(self.height))
                print("right border shape = " + str(top_border.shape))
                print("bottom border shape = " + str(bottom_border.shape))

            diff = self.normalize(bottom_border) - self.normalize(top_border)
            m_norm = sum(sum(sum(abs(diff)))) / bottom_border.size  # Manhattan norm
            if m_norm < min_diff_bottom[0]:
                min_diff_bottom = (m_norm, step)
            v_diff_values.append(m_norm)
            print("diff (M norm): " + str(m_norm))
            step += 1

        print("Minimun (v) distanze between borders find at step " + str(min_diff_bottom[1]) + ": " + str(
            min_diff_bottom[0]))

        #++++++++++++++++++++++++++++++++++++++++++++++++++

        #aggiornamento valori bordo dx
        self.right_border.update(self.right_border.start[0] + min_diff_right[1], self.right_border.start[1],
                                 self.right_border.end[0] + min_diff_right[1], self.right_border.end[1])

        #aggiornamento valori bordo sotto
        self.bottom_border.update(self.bottom_border.start[0], self.bottom_border.start[1] + min_diff_bottom[1],
                                  self.bottom_border.end[0], self.bottom_border.end[1] + min_diff_bottom[1])

        # definizione estremi del modulo
        self.module.set_end(self.right_border.start[0],
                            self.bottom_border.start[1])
        self.module.set_start(self.selection.start[0], self.selection.start[1])

        # left, top, right, bottom
        module = self.image.crop((self.module.start[0], self.module.start[1], self.module.end[0], self.module.end[1]))

        # tile extracted module
        imgm = Image.fromarray(np.array(module.convert('RGB')), mode='RGB')
        self.tiled = self.tile_image(imgm)

        self.save_img(self.left_border.img, 'left_border.png')
        self.save_img(self.right_border.img, 'right_border.png')
        self.save_img(self.top_border.img, 'top_border.png')
        self.save_img(self.bottom_border.img, 'bottom_border.png')

        imgc = Image.fromarray(np.array(self.selection.crop().convert('RGB')), mode='RGB')
        print("selection crop "+str(self.selection.width)+" x "+str(self.selection.height))
        print("crop size - "+str(imgc.size))
        self.save_img(imgc, 'user_crop.png')

        self.save_img(self.tiled, file_name="tiled.png")

        self.save_img(imgm, 'extracted_module.png')

        # area di ricerca
        search_area = og_img[self.selection.start[1]: self.selection.end[1],
                      self.selection.end[0] - self.bo: self.selection.end[0] + self.bo, :]
        imgs = Image.fromarray(search_area, mode='RGB')
        self.save_img(imgs, 'search_area.png')

        self.plot(h_diff_values, self.bo, file_name="h_plot.png")
        self.plot(v_diff_values, self.bv, file_name="v_plot.png")
        # return self.tiled

    # def _drop_alpha(self, img):
    #     return img if img.shape[-1] == 3 else img[:, :, 1:]

    def tile_image(self, tile: Image.Image):
        og_w = self.image.size[0]
        og_h = self.image.size[1]
        tile_w, tile_h = tile.size
        xrepeat = og_w // tile_w
        yrepeat = og_h // tile_h
        tiled = Image.new('RGB', (xrepeat * tile_w, yrepeat * tile_h))

        for i in range(0, xrepeat * tile_w, tile_w):
            for j in range(0, yrepeat * tile_h, tile_h):
                tiled.paste(tile, (i, j))

        return tiled

    def normalize(self, arr):
        normalized = (arr - np.min(arr)) / (np.max(arr) - np.min(arr))
        return normalized

    def save_img(self, img: Image.Image, file_name="image.png"):

        currTS2 = datetime.now().strftime("%Y%m%d%H%M%S")
        file_path = os.path.join(OUT_DIR, currTS2+"_"+file_name)
        if not os.path.isdir(OUT_DIR):
            os.mkdir(OUT_DIR)
        # print("immagine da salvare - size - "+ str(img.size))
        img.save(file_path)

    def plot(self, values, range_limit, direction=0, file_name="plot.png"):
        fig, ax = plt.subplots()
        # data
        end_y = len(values) - range_limit
        points = range(-range_limit, end_y)
        print("x: " + str(len(values)))
        print("y: " + str(len(points)))
        print(points)

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
        file_path = os.path.join(OUT_DIR, file_name)
        fig.savefig(file_path)


class Application(tk.Frame):
    # TODO metti la possibilità di zoommare (+ pan) l'immagine/canvas
    # Default selection object options.
    SELECT_OPTS = dict(dash=(2, 2), stipple='gray25', fill='white',
                       outline='')

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.master.rowconfigure(0, weight=1)  # make the CanvasImage widget expandable
        self.master.columnconfigure(0, weight=1)
        self.canvas = CanvasImage(self.master, path="img/2fili.png")  # create widget
        self.canvas.grid(row=0, column=0)  # show widget

        #menu bar creation
        self.tiling = None
        parent.option_add('*tearOff', tk.FALSE)
        self.menubar = tk.Menu(parent)
        parent['menu'] = self.menubar
        menu_file = tk.Menu(self.menubar)
        menu_edit = tk.Menu(self.menubar)
        menu_tiling = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=menu_file, label='File')
        menu_file.add_command(label="Open image...", accelerator="Ctrl+O", command=self.load_image)
        self.menubar.add_cascade(menu=menu_edit, label='Edit')
        self.menubar.add_cascade(menu=menu_tiling, label='Tiling')
        menu_tiling.add_command(label="Start Tiling", accelerator="Ctrl+T", command=self.start_tiling)
        menu_tiling.add_command(label="Update image with tiled texture", accelerator="Ctrl+U", command=self.update_image)

        parent.bind_all("<Control-o>", self.load_image)
        parent.bind_all("<Control-O>", self.load_image)
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

    def start_tiling(self, event=None):
        self.tiling = Tiling(self.master, self.canvas.canvas.img, self.canvas.selection_obj)

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
            tk.messagebox.showinfo("Update image with tiled texture", "Nothing to update. Start the tiling method before updating.")

if __name__ == '__main__':
    TITLE = 'Tiling'

    root = tk.Tk()
    root.title(TITLE)
    root.geometry('%sx%s' % (WIDTH, HEIGHT))
    root.configure(background=BACKGROUND)

    app = Application(root, background=BACKGROUND)
    app.mainloop()
