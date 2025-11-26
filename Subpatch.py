import os
import time
from settings import *
from patch_fitting import *


class Subpatch:

    def __init__(self, im_name, region_s, region_e, method='subpatch', use_old_cut=False, use_grad=True,
                 expansion=False, expansion_ratio=1.5, patch_ratio=1):

        self.place_method = method  # random, entire, subpatch, auto
        self.error_region = Region(region_s[1], region_s[0], region_e[1], region_e[0]) #r x c
        self.use_old_cut = use_old_cut
        self.use_grad = use_grad
        self.expansion = expansion
        self.expansion_ratio = expansion_ratio
        self.patch_ratio = patch_ratio

        self.im = Image.open(im_name).convert('RGB')  # --->  width x height
        print(self.im.size)
        self.im_input = np.array(self.im, dtype=np.uint8)  # --->  row x column
        print(self.im_input.shape)

        self.h, self.w, _ = self.im_input.shape
        print("h,w ", self.h, self.w)

        if not os.path.isdir(OUT_DIR_SUBPATCH):
            os.makedirs(OUT_DIR_SUBPATCH)

        if expansion:
            # final image size
            height, width = int(expansion_ratio * self.h), int(expansion_ratio * self.w)
            # final image:
            im_src = np.zeros([height, width, _])
            # final map
            src_map = np.zeros([height, width]).astype(bool)
        else:
            height, width = self.h, self.w
            im_src = np.array(self.im, dtype=np.uint8)
            im_src[self.error_region.x1:self.error_region.x2, self.error_region.y1:self.error_region.y2, :] = 0
            Image.fromarray(im_src).show()
            src_map = np.ones([height, width]).astype(bool)
            src_map[self.error_region.x1:self.error_region.x2, self.error_region.y1:self.error_region.y2] = 0

        seam_map = SeamMap(height, width)

        start = time.time()
        i = 0
        offset = (0,0)
        while not src_map.all():
            print("############# ", i)
            if expansion:
                patch_size = (int(self.h // self.patch_ratio), int(self.w // self.patch_ratio))
            else:
                patch_size = (
                    int((self.error_region.x2 - self.error_region.x1) / self.patch_ratio),
                    int((self.error_region.y2 - self.error_region.y1) / self.patch_ratio))
                print("patch region size ", patch_size)

            patch_region = get_error_region(src_map, seam_map, patch_size)
            print("PATCH region: x1, x2 - y1, y2: (", patch_region.x1, ", ", patch_region.x2, ") - (", patch_region.y1,
                  ", ", patch_region.y2, ")")

            if self.place_method == 'random':
                offset = get_offset_random(im_src, src_map, self.im_input)
            elif self.place_method == 'entire':
                offset = get_offset_entire_matching(im_src, src_map, self.im_input)
            elif self.place_method == 'subpatch':
                offset = get_offset_subpatch_matching(im_src, src_map, self.im_input, patch_region, patch_size, i)

            patch_fitting(im_src, src_map, self.im_input, offset, seam_map, patch_region, patch_size, i,
                          self.use_old_cut,
                          self.use_grad)

            show_im = Image.fromarray(im_src.astype(np.uint8))
            show_im.save('%s-%s-%d.jpg' % (OUT_DIR_SUBPATCH+os.path.basename(im_name).split('.')[0], self.place_method, i))
            i += 1

        end = time.time()
        print("time: ", end - start)


if __name__ == '__main__':

    im_name = 'data/asciugamano_edit.png'
    # im_name = 'data/damascato_crop.jpg'
    # error_regionIN = Region(18, 18, 80, 80) # damascato crop
    rstart = (250, 220)  # asciugamano edit
    rend = (330, 300)
    Subpatch(im_name, rstart, rend)
