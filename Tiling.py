import os
import tkinter as tk
import numpy as np
from tkinter import filedialog

from PIL import Image, ImageTk


class MousePositionTracker(tk.Frame):
    """ Tkinter Canvas mouse position widget. """

    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.canv_width = self.canvas.cget('width')
        self.canv_height = self.canvas.cget('height')
        self.reset()

        # Create canvas cross-hair lines.
        xhair_opts = dict(dash=(3, 2), fill='white', state=tk.HIDDEN)
        self.lines = (self.canvas.create_line(0, 0, 0, self.canv_height, **xhair_opts),
                      self.canvas.create_line(0, 0, self.canv_width, 0, **xhair_opts))

    def cur_selection(self):
        return (self.start, self.end)

    def begin(self, event):
        self.hide()
        self.start = (event.x, event.y)  # Remember position (no drawing).

    def update(self, event):
        self.end = (event.x, event.y)
        self._update(event)
        self._command(self.start, (event.x, event.y))  # User callback.

    def _update(self, event):
        # Update cross-hair lines.
        self.canvas.coords(self.lines[0], event.x, 0, event.x, self.canv_height)
        self.canvas.coords(self.lines[1], 0, event.y, self.canv_width, event.y)
        self.show()

    def reset(self):
        self.start = self.end = None

    def hide(self):
        self.canvas.itemconfigure(self.lines[0], state=tk.HIDDEN)
        self.canvas.itemconfigure(self.lines[1], state=tk.HIDDEN)

    def show(self):
        self.canvas.itemconfigure(self.lines[0], state=tk.NORMAL)
        self.canvas.itemconfigure(self.lines[1], state=tk.NORMAL)

    def autodraw(self, command=lambda *args: None):
        """Setup automatic drawing; supports command option"""
        self.reset()
        self._command = command
        self.canvas.bind("<Button-1>", self.begin)
        self.canvas.bind("<B1-Motion>", self.update)
        self.canvas.bind("<ButtonRelease-1>", self.quit)

    def quit(self, event):
        self.hide()  # Hide cross-hairs.
        self.reset()


class SelectionObject:
    """ Widget to display a rectangular area on given canvas defined by two points
        representing its diagonal.
    """

    def __init__(self, canvas, select_opts):
        # Create attributes needed to display selection.
        self.canvas = canvas
        self.select_opts1 = select_opts
        self.width = int(self.canvas.cget('width'))
        self.height = int(self.canvas.cget('height'))
        self.start = (0, 0)
        self.end = (self.width, self.height)

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

        self.canvas.bind("<Double-Button-1>", self.clear)

    def update(self, start, end):
        # Current extrema of inner and outer rectangles.
        imin_x, imin_y, imax_x, imax_y = self._get_coords(start, end)
        omin_x, omin_y, omax_x, omax_y = 0, 0, self.width, self.height
        self.start = (imin_x, imin_y)
        self.end = (imax_x, imax_y)
        # Update coords of all rectangles based on these extrema.
        self.canvas.coords(self.rects[0], omin_x, omin_y, omax_x, imin_y),
        self.canvas.coords(self.rects[1], omin_x, imin_y, imin_x, imax_y),
        self.canvas.coords(self.rects[2], imax_x, imin_y, omax_x, imax_y),
        self.canvas.coords(self.rects[3], omin_x, imax_y, omax_x, omax_y),
        self.canvas.coords(self.rects[4], imin_x, imin_y, imax_x, imax_y),

        for rect in self.rects:  # Make sure all are now visible.
            self.canvas.itemconfigure(rect, state=tk.NORMAL)

    def _get_coords(self, start, end):
        """ Determine coords of a polygon defined by the start and
            end points one of the diagonals of a rectangular area.
        """
        clamp = lambda n, minn, maxn: max(min(maxn, n), minn)

        s0 = clamp(start[0], 0, self.canvas.pht_img.width() - 1)
        e0 = clamp(end[0], 0, self.canvas.pht_img.width() - 1)
        s1 = clamp(start[1], 0, self.canvas.pht_img.height() - 1)
        e1 = clamp(end[1], 0, self.canvas.pht_img.height() - 1)

        return ((min((s0, e0)), min((s1, e1)),
                 max((s0, e0)), max((s1, e1))))

    def hide(self):
        for rect in self.rects:
            self.canvas.itemconfigure(rect, state=tk.HIDDEN)

    def clear(self, event=None):
        self.hide()
        self.start = (0, 0)
        self.end = (self.width, self.height)

    # def crop(self) -> Image.Image:
    #     left, top, right, bottom = self._get_coords(self.start, self.end)
    #     cropped = self.canvas.img.crop((left, top, right, bottom))
    #     # print("width= " + str(cropped.width) + ", height= " + str(cropped.height))
    #     # cropped.show()
    #     return cropped

    def crop(self, h_border=0, v_border=0) -> Image.Image:
        left, top, right, bottom = self._get_coords(self.start, self.end)
        cropped = self.canvas.img.crop((left - h_border, top - v_border, right + h_border, bottom + v_border))
        # print("width= " + str(cropped.width) + ", height= " + str(cropped.height))
        # cropped.show()
        return cropped


class Tiling:
    def __init__(self, image: Image.Image, selection: SelectionObject):
        # tollerance for minimum distance
        self.epsilon = 0.1
        # overlap border size with respect to the original image dimensions
        self.search_ratio = 0.05
        # search ratio
        self.ratio = 0.25
        # overlap border size
        self.border = 5  #TODO prova con 10 e 15
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

        # self.left_border = [(self.selection.start[0], self.selection.start[1] - self.bv),
        #                     (self.selection.start[0] + self.border, self.selection.end[1] + self.bv)]
        # self.right_border = [(self.selection.end[0] - self.bo, self.selection.start[1] - self.bv),
        #                      (self.selection.end[0] - self.bo + self.border, self.selection.end[1] + self.bv)]

        crop_img = selection.crop(self.bo, self.bv)
        # user-selected image (with border) to matrix
        matrix = crop_img.convert('RGB')
        self.crop = np.array(matrix)

        # extracted module (coordinates) init
        self.module = self.selection
        # start module search
        self.start_search()

    def start_search(self):
        # TODO togli tutte le stampe
        # TODO modifica questione controllo/overflow bande se selezione sul bordo
        og_img = self.image.convert('RGB')
        og_img = np.array(og_img)

        # ricerca orizzontale

        #h_border_size = int(self.width * self.border_ratio) #horizontal border size
        print("h border search area (size) " + str(self.bo))
        print("width " + str(self.width) + " border search area ratio " + str(self.search_ratio))
        step = 0
        min_diff_h = (1, 0)  # tuple containing (min difference, step)
        min_border = None

        # bordo sinistro partendo dalla coordinata 0 della selezione dell'utenete
        left_border = self.crop[:, self.bo: self.border + self.bo, :]
        print("coordinata inizio bordo sx: " + str(self.bo) + " - " + str(self.bo + self.border))
        print("left border estratto size: " + str(left_border.shape))
        # while width > int(self.width * self.ratio): # stops when minimum module size is reached

        #+++++++++++ fissato a sx, sposto il bordo di dx
        while step <= 2 * self.bo:  # ricerca  nell'area tra -bo e +bo
            print("############### STEP " + str(step))
            # print("crop shape: " + str(self.crop.shape))
            # r_start = ((self.selection.end[0] - step) % self.image.width, self.selection.start[1])
            # r_end = ((self.selection.end[0] + self.bo - step) % self.image.width, self.selection.end[1])

            # self.right_border = ((self.selection.end[0] - self.bo, self.selection.end[1] - self.bv),
            #                      (self.selection.end[0] - self.bo + self.border, self.selection.end[1] + self.bv))
            # coordinata sx del bordo dx, partendo da -bo rispetto alla selezione dell'utente
            # r_start = (self.right_border[0][0] + step, self.right_border[0][1])  #TODO classe per estremi rettangoli?
            # r_end = ((self.right_border[1][0] + step), self.right_border[1][1])
            r_start = (self.selection.end[0] - self.bo + step, self.selection.start[1] - self.bv )
            r_end = (self.selection.end[0]-self.bo+step+self.border, self.selection.end[1] + self.bv )
            print("start, end (border right) = " + str(r_start), str(r_end))

            right_border = og_img[r_start[1]: r_end[1], r_start[0]: r_end[0], :]

            # TODO sempre collegato al caso overflow
            # if r_end[0] < r_start[0]:
            #     right = og_img[r_start[1]: r_end[1], r_start[0]: self.image.width - 1, :]
            #     right_width = self.image.width - 1 - r_start[0]
            #     right_overflow = og_img[r_start[1]: r_end[1], l_start[0]: (l_start[0] + self.bo - right_width), :]
            #     right_border = np.concatenate([right, right_overflow], 1)

            if step == 0:
                print("orig. selected wxh = " + str(self.width) + "x" + str(self.height))
                print("left border shape = " + str(left_border.shape))
                print("right border shape = " + str(right_border.shape))

            diff = self.normalize(right_border) - self.normalize(left_border)
            m_norm = sum(sum(sum(abs(diff)))) / right_border.size  # Manhattan norm
            if m_norm < min_diff_h[0]:
                min_diff_h = (m_norm, step)
            print("diff (M norm): " + str(m_norm))
            step += 1

        print("Minimun (h) distanze between borders find at step " + str(min_diff_h[1]) + ": " + str(min_diff_h[0]))

        #aggiornamento valori bordo dx
        # self.right_border[0] = (self.selection.end[0] - self.bo + min_diff_h[1], self.right_border[0][1])
        # self.right_border[1] = (self.right_border[0][0] + self.border, self.right_border[1][1])

        #TODO pensa anche a come memorizzare questo
        module_end = (self.selection.end[0] - self.bo + min_diff_h[1],
                      self.selection.end[1])

        # +++++++++++ fissato a dx, sposto il bordo di sx
        step = 0
        min_diff_left = (1, 0)
        r_start = (module_end[0], self.selection.start[1] - self.bv)
        r_end = (module_end[0] + self.border, self.selection.end[1] + self.bv)
        # right_border = self.crop[:, r_start[0]: r_end[0], :]
        # right_border = og_img[self.right_border[0][1]: self.right_border[1][1],
        #                self.right_border[0][0]: self.right_border[1][0], :]
        right_border = og_img[r_start[1]: r_end[1], r_start[0]: r_end[0], :]
        print("right border shape = " + str(right_border.shape))

        while step <= 2 * self.bo:

            # self.left_border[0] = (self.selection.start[0] + step - self.bo, self.left_border[0][1])
            # self.left_border[1] = (self.selection.start[0] + step - self.bo + self.border, self.left_border[1][1])
            # left_border = og_img[self.left_border[0][1]: self.left_border[1][1],
            #               self.left_border[0][0]: self.left_border[1][0], :]
            l_start = (self.selection.start[0]-self.bo+step , self.selection.start[1]-self.bv)
            l_end = (self.selection.start[0]-self.bo+step+self.border, self.selection.end[1]+self.bv)
            left_border = og_img[l_start[1]: l_end[1], l_start[0]: l_end[0], :]

            if step == 0:
                print("orig. selected wxh = " + str(self.width) + "x" + str(self.height))
                print("left border shape = " + str(left_border.shape))
                print("right border shape = " + str(right_border.shape))

            diff = self.normalize(right_border) - self.normalize(left_border)
            m_norm = sum(sum(sum(abs(diff)))) / right_border.size  # Manhattan norm
            if m_norm < min_diff_left[0]:
                min_diff_left = (m_norm, step)
                # left_min_border = left_border
            print("step #" + str(step) + " - diff (M norm): " + str(m_norm))
            step += 1
        print("min step (h, sx): " + str(min_diff_left[1]))

        module_start = (self.selection.start[0] - self.bo + min_diff_left[1],
                        self.selection.start[1])
        # left, top, right, bottom
        module = self.image.crop((module_start[0], module_start[1], module_end[0], module_end[1]))

        # aggiornamento valori bordo sx
        # self.left_border[0] = (self.selection.start[0] + min_diff_left[1] - self.bo, self.left_border[0][1])
        # self.left_border[1] = (self.left_border[0][0] + self.border, self.left_border[1][1])
        # left_min_border = og_img[self.left_border[0][1]: self.left_border[1][1],
        #                   self.left_border[0][0]: self.left_border[1][0], :]
        l_start = (self.selection.start[0] - self.bo + min_diff_left[1], self.selection.start[1] - self.bv)
        l_end = (self.selection.start[0] - self.bo + min_diff_left[1] + self.border, self.selection.end[1] + self.bv)
        left_min_border = og_img[l_start[1]: l_end[1], l_start[0]: l_end[0], :]

        imgl = Image.fromarray(left_min_border, mode='RGB')
        imgl.save('left_border.png')  # TODO gestisci salvataggio nella cartella giusta

        imgr = Image.fromarray(right_border, mode='RGB')
        imgr.save('right_border.png')

        imgc = Image.fromarray(np.array(self.selection.crop().convert('RGB')), mode='RGB')
        imgc.save('user_crop.png')

        imgm = Image.fromarray(np.array(module.convert('RGB')), mode='RGB')
        imgm.save('extracted_module.png')

    # def _drop_alpha(self, img):
    #     return img if img.shape[-1] == 3 else img[:, :, 1:]

    def normalize(self, arr):
        normalized = (arr - np.min(arr)) / (np.max(arr) - np.min(arr))
        return normalized


class Application(tk.Frame):
    # TODO metti la possibilità di zoommare (+ pan) l'immagine/canvas
    # Default selection object options.
    SELECT_OPTS = dict(dash=(2, 2), stipple='gray25', fill='white',
                       outline='')

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

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
        parent.bind("<Button-3>", self.do_popup)

        # path = "static/flox.jpg"
        path = "img/basket_normal.png"
        img = Image.open(path)
        pht_img = ImageTk.PhotoImage(img)
        self.canvas = tk.Canvas(root, width=pht_img.width(), height=pht_img.height(),
                                borderwidth=0, highlightthickness=0)
        self.canvas.pack(expand=True)

        self.displayed_img = self.canvas.create_image(0, 0, image=pht_img, anchor=tk.NW)
        self.canvas.pht_img = pht_img  # Keep reference of current PhotoImage
        self.canvas.img = img
        self.canvas.orig = self.canvas.pht_img  # keep reference of original image

        # Create selection object to show current selection boundaries.
        self.selection_obj = SelectionObject(self.canvas, self.SELECT_OPTS)

        # Callback function to update it given two points of its diagonal.
        def on_drag(start, end, **kwarg):  # Must accept these arguments.
            self.selection_obj.update(start, end)

        # Create mouse position tracker that uses the function.
        self.posn_tracker = MousePositionTracker(self.canvas)
        self.posn_tracker.autodraw(command=on_drag)  # Enable callbacks.

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
    app.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.TRUE)
    app.mainloop()
