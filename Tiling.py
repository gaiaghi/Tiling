import os
import os.path
import tkinter as tk
import numpy as np
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image, ImageTk

from CanvasImage import CanvasImage
from CanvasImage import SelectionObject
from CanvasImage import MousePositionTracker


OUT_DIR = './out/'
#TODO uncomment tutto sotto
#
# class MousePositionTracker(tk.Frame):
#     """ Tkinter Canvas mouse position widget. """
#
#     def __init__(self, canvas):
#         super().__init__()
#         self.canvas = canvas
#         self.canv_width = self.canvas.cget('width')
#         self.canv_height = self.canvas.cget('height')
#         self.reset()
#
#         # Create canvas cross-hair lines.
#         xhair_opts = dict(dash=(3, 2), fill='white', state=tk.HIDDEN)
#         self.lines = (self.canvas.create_line(0, 0, 0, self.canv_height, **xhair_opts),
#                       self.canvas.create_line(0, 0, self.canv_width, 0, **xhair_opts))
#
#     def cur_selection(self):
#         return (self.start, self.end)
#
#     def begin(self, event):
#         self.hide()
#         self.start = (event.x, event.y)  # Remember position (no drawing).
#
#     def update(self, event):
#         self.end = (event.x, event.y)
#         self._update(event)
#         self._command(self.start, (event.x, event.y))  # User callback.
#
#     def _update(self, event):
#         # Update cross-hair lines.
#         self.canvas.coords(self.lines[0], event.x, 0, event.x, self.canv_height)
#         self.canvas.coords(self.lines[1], 0, event.y, self.canv_width, event.y)
#         self.show()
#
#     def reset(self):
#         self.start = self.end = None
#
#     def hide(self):
#         self.canvas.itemconfigure(self.lines[0], state=tk.HIDDEN)
#         self.canvas.itemconfigure(self.lines[1], state=tk.HIDDEN)
#
#     def show(self):
#         self.canvas.itemconfigure(self.lines[0], state=tk.NORMAL)
#         self.canvas.itemconfigure(self.lines[1], state=tk.NORMAL)
#
#     def autodraw(self, command=lambda *args: None):
#         """Setup automatic drawing; supports command option"""
#         self.reset()
#         self._command = command
#         self.canvas.bind("<Button-1>", self.begin)
#         self.canvas.bind("<B1-Motion>", self.update)
#         self.canvas.bind("<ButtonRelease-1>", self.quit)
#
#     def quit(self, event):
#         self.hide()  # Hide cross-hairs.
#         self.reset()
#
#
# class SelectionObject:
#     """ Widget to display a rectangular area on given canvas defined by two points
#         representing its diagonal.
#     """
#
#     def __init__(self, canvas, select_opts):
#         # Create attributes needed to display selection.
#         self.canvas = canvas
#         self.select_opts1 = select_opts
#         self.width = int(self.canvas.cget('width'))
#         self.height = int(self.canvas.cget('height'))
#         self.start = (0, 0)
#         self.end = (self.width, self.height)
#
#         # Options for areas outside rectanglar selection.
#         select_opts1 = self.select_opts1.copy()  # Avoid modifying passed argument.
#         select_opts1.update(state=tk.HIDDEN)  # Hide initially.
#         # Separate options for area inside rectanglar selection.
#         select_opts2 = dict(dash=(2, 2), fill='', outline='white', state=tk.HIDDEN)
#
#         # Initial extrema of inner and outer rectangles.
#         imin_x, imin_y, imax_x, imax_y = 0, 0, 1, 1
#         omin_x, omin_y, omax_x, omax_y = 0, 0, self.width, self.height
#
#         self.rects = (
#             # Area *outside* selection (inner) rectangle.
#             self.canvas.create_rectangle(omin_x, omin_y, omax_x, imin_y, **select_opts1),
#             self.canvas.create_rectangle(omin_x, imin_y, imin_x, imax_y, **select_opts1),
#             self.canvas.create_rectangle(imax_x, imin_y, omax_x, imax_y, **select_opts1),
#             self.canvas.create_rectangle(omin_x, imax_y, omax_x, omax_y, **select_opts1),
#             # Inner rectangle.
#             self.canvas.create_rectangle(imin_x, imin_y, imax_x, imax_y, **select_opts2)
#         )
#
#         self.canvas.bind("<Double-Button-1>", self.clear)
#
#     def update(self, start, end):
#         # Current extrema of inner and outer rectangles.
#         imin_x, imin_y, imax_x, imax_y = self._get_coords(start, end)
#         omin_x, omin_y, omax_x, omax_y = 0, 0, self.width, self.height
#         self.start = (imin_x, imin_y)
#         self.end = (imax_x, imax_y)
#         # Update coords of all rectangles based on these extrema.
#         self.canvas.coords(self.rects[0], omin_x, omin_y, omax_x, imin_y),
#         self.canvas.coords(self.rects[1], omin_x, imin_y, imin_x, imax_y),
#         self.canvas.coords(self.rects[2], imax_x, imin_y, omax_x, imax_y),
#         self.canvas.coords(self.rects[3], omin_x, imax_y, omax_x, omax_y),
#         self.canvas.coords(self.rects[4], imin_x, imin_y, imax_x, imax_y),
#
#         for rect in self.rects:  # Make sure all are now visible.
#             self.canvas.itemconfigure(rect, state=tk.NORMAL)
#
#     def _get_coords(self, start, end):
#         """ Determine coords of a polygon defined by the start and
#             end points one of the diagonals of a rectangular area.
#         """
#         clamp = lambda n, minn, maxn: max(min(maxn, n), minn)
#
#         s0 = clamp(start[0], 0, self.canvas.pht_img.width() - 1)
#         e0 = clamp(end[0], 0, self.canvas.pht_img.width() - 1)
#         s1 = clamp(start[1], 0, self.canvas.pht_img.height() - 1)
#         e1 = clamp(end[1], 0, self.canvas.pht_img.height() - 1)
#
#         return ((min((s0, e0)), min((s1, e1)),
#                  max((s0, e0)), max((s1, e1))))
#
#     def hide(self):
#         for rect in self.rects:
#             self.canvas.itemconfigure(rect, state=tk.HIDDEN)
#
#     def clear(self, event=None):
#         self.hide()
#         self.start = (0, 0)
#         self.end = (self.width, self.height)
#
#     # def crop(self) -> Image.Image:
#     #     left, top, right, bottom = self._get_coords(self.start, self.end)
#     #     cropped = self.canvas.img.crop((left, top, right, bottom))
#     #     # print("width= " + str(cropped.width) + ", height= " + str(cropped.height))
#     #     # cropped.show()
#     #     return cropped
#
#     def crop(self, h_border=0, v_border=0) -> Image.Image:
#         left, top, right, bottom = self._get_coords(self.start, self.end)
#         cropped = self.canvas.img.crop((left - h_border, top - v_border, right + h_border, bottom + v_border))
#         # print("width= " + str(cropped.width) + ", height= " + str(cropped.height))
#         # cropped.show()
#         return cropped


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
    def __init__(self, image: Image.Image, selection: SelectionObject, border=5, search_area=0.15):
        # overlap border size with respect to the original image dimensions
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

        self.save_img(self.left_border.img, 'left_border.png')
        self.save_img(self.right_border.img, 'right_border.png')
        self.save_img(self.top_border.img, 'top_border.png')
        self.save_img(self.bottom_border.img, 'bottom_border.png')

        imgc = Image.fromarray(np.array(self.selection.crop().convert('RGB')), mode='RGB')
        self.save_img(imgc, 'user_crop.png')

        imgm = Image.fromarray(np.array(module.convert('RGB')), mode='RGB')
        self.tile_image(imgm)
        self.save_img(imgm, 'extracted_module.png')

        # area di ricerca
        search_area = og_img[self.selection.start[1]: self.selection.end[1],
                      self.selection.end[0] - self.bo: self.selection.end[0] + self.bo, :]
        imgs = Image.fromarray(search_area, mode='RGB')
        self.save_img(imgs, 'search_area.png')

        self.plot(h_diff_values, self.bo, file_name="h_plot.png")
        self.plot(v_diff_values, self.bv, file_name="v_plot.png")

    # def _drop_alpha(self, img):
    #     return img if img.shape[-1] == 3 else img[:, :, 1:]

    def tile_image(self, tile: Image.Image):
        #     # Opens an image
        # bg = Image.open("NOAHB.png")
        #     # The width and height of the background tile
        # bg_w, bg_h = bg.size
        #     # Creates a new empty image, RGB mode, and size 1000 by 1000
        # new_im = Image.new('RGB', (1000, 1000))
        #     # The width and height of the new image
        # w, h = new_im.size
        #     # Iterate through a grid, to place the background tile
        # for i in xrange(0, w, bg_w):
        #     for j in xrange(0, h, bg_h):
        #             # Change brightness of the images, just to emphasise they are unique copies
        #         bg = Image.eval(bg, lambda x: x + (i + j) / 1000)
        #             # paste the image at location i, j:
        #         new_im.paste(bg, (i, j))
        # new_im.show()
        og_w = self.image.size[0]
        og_h = self.image.size[1]
        tile_w, tile_h = tile.size
        xrepeat = og_w // tile_w
        yrepeat = og_h // tile_h
        tiled = Image.new('RGB', (xrepeat*tile_w, yrepeat*tile_h))

        for i in range(0, xrepeat*tile_w, tile_w):
            for j in range(0, yrepeat*tile_h, tile_h):
                tiled.paste(tile, (i, j))
        self.save_img(tiled, file_name="tiled.png")

    def normalize(self, arr):
        normalized = (arr - np.min(arr)) / (np.max(arr) - np.min(arr))
        return normalized

    def save_img(self, img: Image.Image, file_name="image.png"):

        file_path = os.path.join(OUT_DIR, file_name)
        if not os.path.isdir(OUT_DIR):
            os.mkdir(OUT_DIR)
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
        self.canvas = CanvasImage(self.master, "img/2fili.png")  # create widget
        self.canvas.grid(row=0, column=0)  # show widget

        #menu bar creation
        self.tiling = None
        parent.option_add('*tearOff', tk.FALSE)
        self.menubar = tk.Menu(parent)
        parent['menu'] = self.menubar
        menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=menu_file, label='File')
        menu_file.add_command(label="Open image...", accelerator="Ctrl+O", command=self.load_image)
        menu_file.add_command(label="Start Tiling", accelerator="Ctrl+T", command=self.start_tiling)

        parent.bind_all("<Control-o>", self.load_image)
        parent.bind_all("<Control-O>", self.load_image)
        parent.bind_all("<Control-t>", self.start_tiling)
        parent.bind_all("<Control-T>", self.start_tiling)

        menu_file.add_separator()
        menu_file.add_command(label="Exit", command=root.destroy)
        parent.config(menu=self.menubar)

        # pop-up menu creation
        self.popup_menu = tk.Menu(parent, tearoff=0)
        self.popup_menu.add_command(label="Crop selection", command=self.crop_selected)
        self.popup_menu.add_command(label="Save selection", command=self.save_selected)
        # TODO cambia menù a pop up in una tendina del menù sopra
        # parent.bind("<Button-3>", self.do_popup)

        # path = "static/flox.jpg"
        #TODO UNCOMMENT tutto il pezzo sotto
        #
        # path = "img/basket_normal.png"
        # img = Image.open(path)
        # pht_img = ImageTk.PhotoImage(img)
        # self.canvas = tk.Canvas(root, width=pht_img.width(), height=pht_img.height(),
        #                         borderwidth=0, highlightthickness=0)
        # self.canvas.pack(expand=True)
        #
        # self.displayed_img = self.canvas.create_image(0, 0, image=pht_img, anchor=tk.NW)
        # self.canvas.pht_img = pht_img  # Keep reference of current PhotoImage
        # self.canvas.img = img
        # self.canvas.orig = self.canvas.pht_img  # keep reference of original image
        #
        # # Create selection object to show current selection boundaries.
        # self.selection_obj = SelectionObject(self.canvas, self.SELECT_OPTS)
        #
        # # Callback function to update it given two points of its diagonal.
        # def on_drag(start, end, **kwarg):  # Must accept these arguments.
        #     self.selection_obj.update(start, end)
        #
        # # Create mouse position tracker that uses the function.
        # self.posn_tracker = MousePositionTracker(self.canvas)
        # self.posn_tracker.autodraw(command=on_drag)  # Enable callbacks.

#   TODO sistema queste funzioni se riesco a metterci lo zoom ecc
    def load_image(self, event=None):
        file_path = filedialog.askopenfilename(title="Open Image...",
                                               filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.ico")])
        if file_path:
            self.canvas.img = Image.open(file_path)
            self.canvas.pht_img = ImageTk.PhotoImage(self.canvas.img)
            self.canvas.orig = self.canvas.pht_img
            self.canvas.itemconfig(self.displayed_img, image=self.canvas.pht_img)
            self.canvas.config(height=self.canvas.pht_img.height(), width=self.canvas.pht_img.width())
            self.selection_obj.height = self.canvas.pht_img.height()
            self.selection_obj.width = self.canvas.pht_img.width()
            self.selection_obj.clear()

    def start_tiling(self, event=None):
        self.tiling = Tiling(self.canvas.img, self.selection_obj)

    def do_popup(self, event=None):
        """ Right click event handler to open the popup menu.
        """
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.popup_menu.grab_release()

    def crop_selected(self):
        img = self.selection_obj.crop()
        self.canvas.img = img
        self.canvas.pht_img = ImageTk.PhotoImage(self.canvas.img)
        self.canvas.itemconfig(self.displayed_img, image=self.canvas.pht_img)
        self.canvas.config(height=self.canvas.pht_img.height(), width=self.canvas.pht_img.width())
        self.selection_obj.height = self.canvas.pht_img.height()
        self.selection_obj.width = self.canvas.pht_img.width()
        self.selection_obj.clear()

    def save_selected(self):
        img = self.selection_obj.crop()
        file = filedialog.asksaveasfile(mode='w', defaultextension=".png")
        if file:
            abs_path = os.path.abspath(file.name)
            img.save(abs_path)  # saves the image to the input file name.


if __name__ == '__main__':
    WIDTH, HEIGHT = 900, 900
    BACKGROUND = '#292929'
    TITLE = 'Tiling'

    root = tk.Tk()
    root.title(TITLE)
    root.geometry('%sx%s' % (WIDTH, HEIGHT))
    root.configure(background=BACKGROUND)

    app = Application(root, background=BACKGROUND)
    #TODO UNNCOMMENT riga sotto
    # app.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.TRUE)
    app.mainloop()
