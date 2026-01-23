import os
import time
from settings import *
from patch_fitting import *


class Subpatch:

    def __init__(self, im_name, region_s, region_e, method='subpatch', maps_path=None, use_old_cut=False, use_grad=True,
                 expansion=False, expansion_ratio=1.5, patch_fraction=1.2, blur=True):

        self.im_name = im_name
        self.maps_path = maps_path
        self.place_method = method  # random, entire, subpatch, auto
        self.error_region = Region(region_s[1], region_s[0], region_e[1], region_e[0]) #r x c
        self.use_old_cut = use_old_cut
        self.use_grad = use_grad
        self.expansion = expansion
        self.expansion_ratio = expansion_ratio
        self.patch_fraction = patch_fraction
        self.blur = blur
        self.im_src = None
        self.seam_map = None
        self.src_map = None
        self.maps = []

        self.im = Image.open(im_name).convert('RGB')  # --->  width x height
        print(self.im.size)
        self.im_input = np.array(self.im, dtype=np.uint8)  # --->  row x column
        print(self.im_input.shape)

        if self.maps_path is not None:
            for i in range(len(self.maps_path)):
                self.maps.append(np.array(Image.open(self.maps_path[i])))
            # print("Lenght maps", len(self.maps))

        self.h, self.w, _ = self.im_input.shape
        # print("h,w ", self.h, self.w)

        if not os.path.isdir(OUT_DIR_SUBPATCH):
            os.makedirs(OUT_DIR_SUBPATCH)

        if expansion:
            # final image size
            height, width = int(expansion_ratio * self.h), int(expansion_ratio * self.w)
            # final image:
            self.im_src = np.zeros([height, width, _])
            # final map
            self.src_map = np.zeros([height, width]).astype(bool)
        else:
            self.height, self.width = self.h, self.w
            self.im_src = np.array(self.im, dtype=np.uint8)
            self.im_src[self.error_region.x1:self.error_region.x2, self.error_region.y1:self.error_region.y2, :] = 0
            self.src_map = np.ones([self.height, self.width]).astype(bool)
            self.src_map[self.error_region.x1:self.error_region.x2, self.error_region.y1:self.error_region.y2] = 0

        self.seam_map = SeamMap(self.height, self.width)


    def subpatching(self):
        start = time.time()
        sp_im = self.im
        i = 0
        offset = (0, 0)
        while not self.src_map.all():
            print("############# ", i)
            if self.expansion:
                patch_size = (int(self.h // self.patch_fraction), int(self.w // self.patch_fraction))
            else:
                patch_size = (
                    int((self.error_region.x2 - self.error_region.x1) / self.patch_fraction),
                    int((self.error_region.y2 - self.error_region.y1) / self.patch_fraction))
                # print("patch region size ", patch_size)

            patch_region = get_error_region(self.src_map, self.seam_map, patch_size)
            print("PATCH region: x1, x2 - y1, y2: (", patch_region.x1, ", ", patch_region.x2, ") - (", patch_region.y1,
                  ", ", patch_region.y2, ")")

            # if self.place_method == 'random':
            #     offset = get_offset_random(self.im_src, self.src_map, self.im_input)
            if self.place_method == 'entire':
                #TODO se ritenuto necessario è da integrare all'interfaccia grafica (per espansione/sintesi texture non tileable)
                offset = get_offset_entire_matching(self.im_src, self.src_map, self.im_input)
            elif self.place_method == 'subpatch':
                offset = get_offset_subpatch_matching(self.im_src, self.src_map, self.im_input, patch_region, patch_size, i)

            self.im_src = patch_fitting(self.im_src, self.src_map, self.im_input, offset, self.seam_map,
                                        patch_region, self.maps, self.maps_path, patch_size, i, self.use_old_cut,
                                        self.use_grad, self.blur)

            sp_im = Image.fromarray(self.im_src.astype(np.uint8))
            # sp_im.save(
            #     '%s-%s-%d.png' % (OUT_DIR_SUBPATCH + os.path.basename(self.im_name).split('.')[0], self.place_method, i))
            # for mm in range(len(self.maps)):
            #     sp_im = Image.fromarray(self.maps[mm].astype(np.uint8))
                # sp_im.save(
                #     '%s-%s-m%d.png' % (
                #     OUT_DIR_SUBPATCH + os.path.basename(self.maps_path[mm]).split('.')[0], self.place_method, i))
            i += 1

        end = time.time()
        print("computed in (s): ", end - start)
        ts = time.strftime("%Y%m%d-%H%M%S")
        sp_im.save(
            '%s-%s-%s.png' % (OUT_DIR_SUBPATCH + os.path.basename(self.im_name).split('.')[0], self.place_method, ts))
        for mm in range(len(self.maps)):
            sp_im = Image.fromarray(self.maps[mm].astype(np.uint8))
            sp_im.save(
                '%s-%s-m%s.png' % (OUT_DIR_SUBPATCH +
                                   os.path.basename(self.maps_path[mm]).split('.')[0], self.place_method, ts))
        return sp_im


if __name__ == '__main__':

    im_name = 'data/asciugamano_edit.png'
    rstart = (250, 220)  # asciugamano edit
    rend = (330, 300)
    Subpatch(im_name, rstart, rend)
