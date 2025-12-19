from settings import *
import os
import tkinter as tk
from tkinter import filedialog, simpledialog
from tkinter import messagebox
from os import listdir
from os.path import isfile, join
import argparse
import sys
from CanvasImage import CanvasImage
from Tiling import Tiling
from PIL import Image
from Subpatch import Subpatch
from utils import TwoDPoint


class Dialog(tk.Toplevel):

    def __init__(self, parent):

        tk.Toplevel.__init__(self, parent)
        self.transient(parent)
        self.title("Subpatch parameters")
        self.parent = parent
        self.result = None
        body = tk.Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5)
        self.buttonbox()
        self.grab_set()
        if not self.initial_focus:
            self.initial_focus = self
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50,
                                  parent.winfo_rooty() + 50))
        self.initial_focus.focus_set()
        self.wait_window(self)

    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden
        pass

    def buttonbox(self):
        # add standard button box. override if you don't want the
        # standard buttons
        box = tk.Frame(self)
        w = tk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def ok(self, event=None):
        if not self.validate():
            self.initial_focus.focus_set()  # put focus back
            return
        self.withdraw()
        self.update_idletasks()
        self.apply()
        self.cancel()

    def cancel(self, event=None):
        # put focus back to the parent window
        self.parent.focus_set()
        self.destroy()

    def validate(self):
        return 1  # override

    def apply(self):
        pass


class MultiDialog(Dialog):

    def __init__(self, parent):
        self.cb = None
        self.e1 = None
        self.CheckVar = tk.IntVar(value=1)
        self.EntryVar = tk.StringVar(value="1")
        super().__init__(parent)

    def body(self, master):
        tk.Label(master, text="Patch fraction (patch size \nwith respect to error region)").grid(row=0, padx=10)
        # tk.Label(master, text="Second:").grid(row=1, sticky=tk.W)

        self.e1 = tk.Entry(master, textvariable=self.EntryVar)
        # self.e2 = tk.Entry(master)
        self.e1.grid(row=0, column=1, padx=10)
        # self.e2.grid(row=1, column=1)
        self.cb = tk.Checkbutton(master, text="Blur cut edges", variable=self.CheckVar)
        self.cb.grid(row=1, columnspan=1, sticky=tk.W)
        return self.e1  # initial focus

    def validate(self):
        try:
            fraction = float(self.EntryVar.get())
            blur = bool(self.CheckVar.get())
            self.result = fraction, blur
            print("Dialog result", self.result)
            return 1
        except ValueError:
            tk.messagebox.showwarning(
                "Bad input",
                "Illegal values, please try again"
            )
            return 0



class Application(tk.Frame):
    # Default selection object options.
    SELECT_OPTS = dict(dash=(2, 2), stipple='gray25', fill='white',
                       outline='')

    def __init__(self, parent, coords=None, imgpath=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.root = parent
        # default selection mode: rectangle
        self.selection_mode = tk.IntVar()
        self.selection_mode.set(1)
        self.selection_value = 1
        self.imgpath = imgpath
        self.coords = coords
        self.master.rowconfigure(0, weight=1)  # make the CanvasImage widget expandable
        self.master.columnconfigure(0, weight=1)
        self.canvas = CanvasImage(self.master, path=imgpath, coords=coords)  # create widget
        self.canvas.grid(row=0, column=0)  # show widget

        self.weight_file = None
        self.folder_maps = None

        #menu bar creation
        self.tiling = None
        parent.option_add('*tearOff', tk.FALSE)
        self.menubar = tk.Menu(parent)
        parent['menu'] = self.menubar
        menu_file = tk.Menu(self.menubar)
        menu_selection = tk.Menu(self.menubar)
        menu_edit = tk.Menu(self.menubar)
        menu_tiling = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=menu_file, label='File')
        menu_file.add_command(label="Open single image...", accelerator="Ctrl+O", command=self.load_image)
        menu_file.add_command(label="Open image map in folder...", accelerator="Ctrl+F", command=self.load_folder)
        self.menubar.add_cascade(menu=menu_edit, label='Edit')
        menu_edit.add_command(label="Subpatch", accelerator="Ctrl+P", command=self.start_subpatch)
        menu_edit.add_command(label="Restore image", accelerator="Ctrl+R", command=self.restore_og_image)
        self.menubar.add_cascade(menu=menu_tiling, label='Tiling')
        menu_tiling.add_command(label="Start Tiling", accelerator="Ctrl+T", command=self.start_tiling)
        menu_tiling.add_command(label="Update image with tiled texture", accelerator="Ctrl+U",
                                command=self.update_image)

        theme_menu = tk.Menu(self.menubar, tearoff=False)
        theme_menu.add_radiobutton(
            label="Rectangle",
            variable=self.selection_mode,
            value=1,
            command=self.change_selection_mode
        )
        theme_menu.add_radiobutton(
            label="Parallelogram",
            value=2,
            variable=self.selection_mode,
            command=self.change_selection_mode
        )
        menu_selection.add_cascade(menu=theme_menu, label="Selection mode")
        self.menubar.add_cascade(menu=menu_selection, label="Selection")

        parent.bind_all("<Control-o>", self.load_image)
        parent.bind_all("<Control-O>", self.load_image)
        parent.bind_all("<Control-f>", self.load_folder)
        parent.bind_all("<Control-F>", self.load_folder)
        parent.bind_all("<Control-t>", self.start_tiling)
        parent.bind_all("<Control-T>", self.start_tiling)
        parent.bind_all("<Control-u>", self.update_image)
        parent.bind_all("<Control-U>", self.update_image)
        parent.bind_all("<Control-P>", self.start_subpatch)
        parent.bind_all("<Control-p>", self.start_subpatch)
        parent.bind_all("<Control-R>", self.restore_og_image)
        parent.bind_all("<Control-r>", self.restore_og_image)

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
            # self.percorso = file_path
            self.tiling = None
            self.imgpath = file_path
            self.canvas.destroy()
            self.canvas = CanvasImage(self.master, path=file_path, selection_mode=self.selection_value)  # create widget
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
        self.folder_maps = None

    def load_folder(self, event=None):
        """ Open single image to tile in a folder containing all texture maps.
        """
        # try:
        #     int("not_a_number")
        # except ValueError as e:
        #     print("str():", str(e))
        #     print("repr():", repr(e))

        file_path = filedialog.askopenfilename(title="Open image map in folder...",
                                               filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.ico")])
        # if file_path:
        try:
            with open(file_path, "r") as _:
                abs_file_path = os.path.abspath(file_path)
                self.imgpath = abs_file_path
                folder_path = os.path.dirname(abs_file_path)
                # if os.path.isdir(folder_path):
                #     folder_files = [join(folder_path, f) for f in listdir(folder_path) if isfile(join(folder_path, f))]
                if os.path.isdir(folder_path):
                    folder_files = [join(folder_path, f) for f in listdir(folder_path) if isfile(join(folder_path, f))]
                    txtfile = [x for x in folder_files if x.endswith('.txt')]
                    self.weight_file = txtfile[0] if len(txtfile) >= 1 else None
                    print("txt file ", self.weight_file)
                    folder_files = [f for f in folder_files if
                                    (f.endswith((".jpg", ".png", ".bmp", ".ico", ".jpeg", ".gif")))]
                    self.folder_maps = folder_files
                    print("folder files ", folder_files)
                    # maps = [f for f in folder_files if not os.path.basename(file_path) in f]
                    # print(maps)
                    # self.percorso=file_path
                else:
                    print("Cannot open the provided directory.")

            self.canvas.destroy()
            self.canvas = CanvasImage(self.master, path=abs_file_path,
                                      selection_mode=self.selection_value)  # create widget
            self.canvas.grid(row=0, column=0)
            # self.tiling = Tiling(self.master, self.canvas.canvas.img, self.canvas.selection_obj.start,
            #                      self.canvas.selection_obj.end, folder=folder_path, start_tiling=False)
        except FileNotFoundError:
            print("Error: The file ", file_path, " was not found.")
            content = IMGPATH
            print("Using default single image:")
            print(content)

    def change_selection_mode(self, event=None):
        self.selection_value = self.selection_mode.get()
        self.update_canvas(path=self.imgpath)

    def restore_og_image(self, event=None):
        self.update_canvas(path=self.imgpath)

    def start_subpatch(self, event=None):
        # print("start, end ", self.canvas.selection_obj.start, self.canvas.selection_obj.end)
        # print("canvas size ", self.canvas.imwidth, " ", self.canvas.imheight)
        dh = self.canvas.selection_obj.end.x - self.canvas.selection_obj.start.x
        dw = self.canvas.selection_obj.end.y - self.canvas.selection_obj.start.y

        if self.canvas.selection_obj.start == TwoDPoint(0, 0) and self.canvas.selection_obj.end == TwoDPoint(
                self.canvas.imwidth, self.canvas.imheight):
            tk.messagebox.showinfo("Subpatch edit", "Select a small area within the image to apply the edit.")
        # due controlli: l'area selezionata non può essere troppo vicina al bordo dell'immagine dx e top altrimenti non c'è abbastanza
        # area di confronto per la ricerca del patch.
        #TODO si può rimuovere il controllo flippando tutto e prendendo quindi l'angolo opposto
        elif self.canvas.selection_obj.start.x < dh / 5:
            tk.messagebox.showinfo("Subpatch edit", "The selected area is too close to the right border of the image.")
        elif self.canvas.selection_obj.start.y < dw / 5:
            tk.messagebox.showinfo("Subpatch edit", "The selected area is too close to the top border of the image.")
        else:
            d_inputs = MultiDialog(root)
            # patch_fr = simpledialog.askfloat("Subpatch parameters",
            #                                  "Patch fraction (patch size with respect to error region)", initialvalue=1)
            if d_inputs is not None:
                patch_fr, blur_var = d_inputs.result
                print("parch_fr, blur_var", patch_fr, blur_var)
                img = self.imgpath
                # print("PATCH FRACTION ", patch_fr)
                subpatch = Subpatch(img, self.canvas.selection_obj.start, self.canvas.selection_obj.end,
                                    maps_path=self.folder_maps, patch_fraction=(1 / patch_fr), blur=blur_var).subpatching()
                # subpatch = Subpatch(img, (500,500), (600,600), patch_fraction=patch_fr).subpatching()
                self.update_canvas(img=subpatch)
        #TODO finisci

    def start_tiling(self, event=None):
        # if self.tiling is None:
        #     self.tiling = Tiling(self.master, self.canvas.canvas.img, self.canvas.selection_obj.start,
        #                          self.canvas.selection_obj.end)
        # else:
        #     self.tiling.start_search()

        # self.tiling = Tiling(self.master, self.canvas.canvas.img, self.canvas.selection_obj.start,
        #                      self.canvas.selection_obj.end, maps=self.folder_maps)
        img_name = os.path.basename(self.imgpath)
        self.tiling = Tiling(self.canvas.canvas.img, self.canvas.selection_obj.start,
                             self.canvas.selection_obj.end, self.canvas.selection_obj,
                             shear=self.canvas.selection_obj.coordinates,
                             maps=self.folder_maps, weights=self.weight_file, filename=img_name, timestamp=TSTAMP)
        self.canvas.selection_obj.rect_module(*self.tiling.cmod)

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

    def update_canvas(self, img=None, path=None):
        self.canvas.destroy()
        self.canvas = CanvasImage(self.master, img=img, path=path, selection_mode=self.selection_value)
        self.canvas.grid(row=0, column=0)

    def update_image(self, event=None):
        if self.tiling is not None:
            self.update_canvas(img=self.tiling.tiled)
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
                        default="img/damascato.jpg", const="img/img/damascato.jpg", type=str)
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
            img_name = os.path.basename(IMGPATH)
            tiling = Tiling(image, (coords[0], coords[1]), (coords[2], coords[3]), filename=img_name)  #TODO
        else:
            sys.exit('Cannot open image')
    else:
        app = Application(root, coords=COORDS, background=BACKGROUND, imgpath=IMGPATH)
        app.mainloop()
