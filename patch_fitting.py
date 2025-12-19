import numpy as np
import networkx as nx
from PIL import Image, ImageChops, ImageFilter
import random
from scipy.signal import *
from settings import *

INF = 1e8
EPS = 1e-8


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.idx = (x, y)

    def neighbors(self):
        i = self.x
        j = self.y
        return [Point(i - 1, j), Point(i + 1, j), Point(i, j - 1), Point(i, j + 1)]

    def left_nbr(self):
        return Point(self.x, self.y - 1)

    def top_nbr(self):
        return Point(self.x - 1, self.y)


class Region:
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2

    def contains(self, x, y):
        return self.x1 <= x and x < self.x2 and self.y1 <= y and y < self.y2

    def slice(self):
        return (slice(self.x1, self.x2), slice(self.y1, self.y2))

    def points_iter(self):
        for x in range(self.x1, self.x2):
            for y in range(self.y1, self.y2):
                yield Point(x, y)

    def clip(self, x1, y1, x2, y2):
        self.x1 = max(self.x1, x1)
        self.y1 = max(self.y1, y1)
        self.x2 = min(self.x2, x2)
        self.y2 = min(self.y2, y2)


class SeamMap:
    def __init__(self, height, width):
        self.has_left = np.full([height, width], False, bool)
        self.has_top = np.full([height, width], False, bool)
        self.left_nbr_cost = np.full([height, width], 0, np.float32)
        self.top_nbr_cost = np.full([height, width], 0, np.float32)
        self.offset = np.full([height, width, 2], 0)


def show(a):
    print(a.astype(np.uint8))


def get_grad(im):
    # im = im.convert('L')
    im = im.astype(float)
    grad_x = np.gradient(im, axis=0)
    grad_y = np.gradient(im, axis=1)
    grad_x = np.sum(grad_x ** 2, axis=2)
    grad_y = np.sum(grad_y ** 2, axis=2)

    # grad_x = np.sqrt(grad_x)
    # grad_y = np.sqrt(grad_y)

    return grad_x, grad_y


def get_l2_energy_cost(s: Point, t: Point, im_src: np.ndarray, im_dst: np.ndarray, A_grad=None, B_grad=None,
                       use_grad=False) -> float:
    # print(s.idx, t.idx)
    cost = np.square(im_src[s.idx] - im_dst[s.idx]).sum(-1) + np.square(im_src[t.idx] - im_dst[t.idx]).sum(-1)

    if use_grad:
        # A_grad = get_grad(im_src)
        # B_grad = get_grad(im_dst)
        cost = get_grad_cost(s.x, s.y, t.x, t.y, cost, A_grad, B_grad)

    return cost


def get_l2_norm_cost(x_s, y_s, x_t, y_t, im_diff):
    # M = 0
    return im_diff[x_s, y_s] + im_diff[x_t, y_t]


def get_grad_cost(x_s, y_s, x_t, y_t, M, A_grad, B_grad):
    A_grad_x, A_grad_y = A_grad
    B_grad_x, B_grad_y = B_grad

    if x_s == x_t:
        grad_src = A_grad_y
        grad_dst = B_grad_y
    else:
        grad_src = A_grad_x
        grad_dst = B_grad_x

    grad_sum = grad_src[x_s, y_s] + grad_src[x_t, y_t] + grad_dst[x_s, y_s] + grad_dst[x_t, y_t]

    return M / (grad_sum + EPS)
    # return M


def get_bound_box(im_map) -> Region:
    if not im_map.any(): return None
    temp_coords = np.where(im_map > 0)
    r, c = temp_coords
    x_min, x_max = min(r), max(r)
    y_min, y_max = min(c), max(c)
    return Region(x_min, y_min, x_max + 1, y_max + 1)


def get_seam_node(u: Point, v: Point, im_src: np.ndarray) -> Point:
    height, width, _ = im_src.shape

    return Point(u.x * height + v.x, u.y * width + v.y)


def build_graph(im_src, src_map, im_input, offset, seam_map: SeamMap, error_region: Region, region_size=None, i=None,
                use_old_cut=False,
                use_grad=True):
    height, width = im_src[:, :, 0].shape
    im_dst, dst_map = handle_input_offset(height, width, im_input, offset, error_region, region_size, i)

    overlap_map = src_map & dst_map
    Image.fromarray(overlap_map).save(OUT_DIR_SUBPATCH+"_overlap_map_" + str(i) + ".png")

    if (overlap_map == src_map).all() or (not overlap_map.any()):
        print("Controllo su Overlap map")
        im_src[:, :] = im_dst[:, :]
        src_map |= dst_map
        return (None, im_dst, dst_map)

    # calculate grad
    A_grad = get_grad(im_src)
    B_grad = get_grad(im_dst)

    overlap_region = get_bound_box(overlap_map)
    Image.fromarray(im_dst[overlap_region.x1:overlap_region.x2, overlap_region.y1:overlap_region.y2, :].astype(np.uint8)).save(OUT_DIR_SUBPATCH+"TEST_01_dst" + str(i) + ".png")
    Image.fromarray(im_src[overlap_region.x1:overlap_region.x2, overlap_region.y1:overlap_region.y2, :].astype(np.uint8)).save(OUT_DIR_SUBPATCH+"TEST_02_src" + str(i) + ".png")

    map_region = Region(0, 0, height, width)

    #GG - questa variabile non viene usata
    # im_diff = (im_src - im_dst) ** 2
    # im_diff = np.sum(im_diff, axis=2)

    super_src = Point(-1, -1)
    super_dst = Point(height, width)

    G = nx.Graph()

    for curr in overlap_region.points_iter():
        # curr = Point(-1, -1)
        if not overlap_map[curr.idx]: continue
        left_nbr = curr.left_nbr()
        top_nbr = curr.top_nbr()

        connect_src = False
        connect_dst = False

        for nbr in curr.neighbors():
            if not map_region.contains(nbr.x, nbr.y): continue

            if not overlap_map[nbr.idx] and src_map[nbr.idx]: connect_src = True
            if not overlap_map[nbr.idx] and dst_map[nbr.idx]:
                connect_dst = True
        if connect_src and not connect_dst:
            G.add_edge(super_src.idx, curr.idx, weight=INF)
        if connect_dst and not connect_src:
            G.add_edge(super_dst.idx, curr.idx, weight=INF)

        if map_region.contains(left_nbr.x, left_nbr.y):
            if overlap_map[left_nbr.idx]:
                if use_old_cut and seam_map.has_left[curr.idx]:

                    seam_node = get_seam_node(left_nbr, curr, im_src)

                    left_offset = seam_map.offset[left_nbr.idx]
                    curr_offset = seam_map.offset[curr.idx]

                    left_patch, _ = handle_input_offset(height, width, im_input, left_offset, error_region, region_size)
                    curr_patch, _ = handle_input_offset(height, width, im_input, curr_offset, error_region, region_size)

                    seam_to_dst_cost = get_l2_energy_cost(left_nbr, curr, left_patch, curr_patch)
                    left_to_seam_cost = get_l2_energy_cost(left_nbr, curr, left_patch, im_dst)
                    seam_to_curr_cost = get_l2_energy_cost(left_nbr, curr, im_dst, curr_patch)

                    G.add_edge(seam_node.idx, super_dst.idx, weight=seam_to_dst_cost)
                    G.add_edge(left_nbr.idx, seam_node.idx, weight=left_to_seam_cost)
                    G.add_edge(seam_node.idx, curr.idx, weight=seam_to_curr_cost)

                    # pass
                else:
                    energe_cost = get_l2_energy_cost(left_nbr, curr, im_src, im_dst, A_grad, B_grad, use_grad)
                    G.add_edge(left_nbr.idx, curr.idx, weight=energe_cost)

        if map_region.contains(top_nbr.x, top_nbr.y):
            if overlap_map[top_nbr.idx]:
                if use_old_cut and seam_map.has_top[curr.idx]:
                    seam_node = get_seam_node(top_nbr, curr, im_src)

                    top_offset = seam_map.offset[top_nbr.idx]
                    curr_offset = seam_map.offset[curr.idx]

                    top_patch, _ = handle_input_offset(height, width, im_input, top_offset, error_region, region_size)
                    curr_patch, _ = handle_input_offset(height, width, im_input, curr_offset, error_region, region_size)

                    seam_to_dst_cost = get_l2_energy_cost(top_nbr, curr, top_patch, curr_patch)
                    top_to_seam_cost = get_l2_energy_cost(top_nbr, curr, top_patch, im_dst)
                    seam_to_curr_cost = get_l2_energy_cost(top_nbr, curr, im_dst, curr_patch)

                    G.add_edge(seam_node.idx, super_dst.idx, weight=seam_to_dst_cost)
                    G.add_edge(top_nbr.idx, seam_node.idx, weight=top_to_seam_cost)
                    G.add_edge(seam_node.idx, curr.idx, weight=seam_to_curr_cost)
                else:
                    energe_cost = get_l2_energy_cost(top_nbr, curr, im_src, im_dst, A_grad, B_grad, use_grad)
                    G.add_edge(top_nbr.idx, curr.idx, weight=energe_cost)

    src_map |= dst_map

    return (G, im_dst, dst_map)


def update_seam_map(G: nx.Graph, seam_map: SeamMap, src_set: set, dst_set: set, curr: Point, im_src, left=True):
    left_nbr = curr.left_nbr()
    top_nbr = curr.top_nbr()
    if curr.idx in dst_set:
        if left:
            if left_nbr.idx in src_set:
                seam_map.has_left[curr.idx] = True
                seam_node = get_seam_node(left_nbr, curr, im_src)
                if G.has_node(seam_node.idx):
                    temp_node = curr if seam_node in src_set else left_nbr
                    seam_map.left_nbr_cost[curr.idx] = G[seam_node.idx][temp_node.idx]['weight']
                else:
                    seam_map.left_nbr_cost[curr.idx] = G[left_nbr.idx][curr.idx]['weight']
            else:
                seam_map.has_left[curr.idx] = False
                seam_map.left_nbr_cost[curr.idx] = 0
        else:
            if top_nbr.idx in src_set:
                seam_map.has_top[curr.idx] = True
                seam_node = get_seam_node(top_nbr, curr, im_src)
                if G.has_node(seam_node.idx):
                    temp_node = curr if seam_node in src_set else top_nbr
                    seam_map.top_nbr_cost[curr.idx] = G[seam_node.idx][temp_node.idx]['weight']
                else:
                    seam_map.top_nbr_cost[curr.idx] = G[top_nbr.idx][curr.idx]['weight']
            else:
                seam_map.has_top[curr.idx] = False
                seam_map.top_nbr_cost[curr.idx] = 0


def patch_fitting(im_src, src_map, im_input, offset, seam_map: SeamMap, error_region: Region, maps=None, maps_path=None,
                  region_size=None, iter=None, use_old_cut=True, use_grad=False, blur=True):
    off_x, off_y = offset
    if use_old_cut: use_grad = False
    if maps is None: maps = []
    if maps_path is None: maps_path = []
    orig_maps = []
    tran_ims = []
    for i in range(len(maps_path)):
        orig_maps.append(np.array(Image.open(maps_path[i])))
        tran_ims.append(np.array(ImageChops.offset(Image.fromarray(orig_maps[i].astype(np.uint8)), off_y, off_x)))

    # background and mask - setup for blurring
    ud_area = np.full(im_src.shape, 255, dtype=np.uint8)
    ud_mask = np.full(im_src[:, :, 0].shape, 0, dtype=np.uint8)
    if blur:
        img_bg = np.copy(im_src)
        img_bg[np.where(src_map == 0)] = im_input[np.where(src_map == 0)]
        prev_maps = []
        for m in maps:
            prev_maps.append(np.copy(m))

    (G, im_dst, dst_map) = build_graph(im_src, src_map, im_input, offset, seam_map, error_region, region_size, iter,
                                       use_old_cut,
                                       use_grad)

    Image.fromarray(im_dst.astype(np.uint8)).save(OUT_DIR_SUBPATCH+"_im_dst_" + str(iter) + ".png")
    print("-----finito costruzione grafo")



    height, width = im_src[:, :, 0].shape
    if not region_size:
        h, w, _ = im_input.shape
    else:
        h, w = region_size[0], region_size[1]

    if G:
        print("-----if G")
        super_src = Point(-1, -1)
        super_dst = Point(height, width)
        if not (G.has_node(super_src.idx) and G.has_node(super_dst.idx)):
            print('fitting nothing....')
            return

        _, partion = nx.minimum_cut(G, super_src.idx, super_dst.idx, 'weight')
        print("-----finito mincut")
        # flow = G.maxflow()
        # partion = [set(), set()]
        # gnx = G.get_nx_graph()

        img_left = np.ones(im_src.shape, dtype=np.uint8)
        left, right = partion
        for ll in left:
            img_left[ll] = (1, 0, 0)
        for rr in right:
            if rr != (height, width):
                img_left[rr] = (0, 1, 0)
        Image.fromarray((255 * img_left).astype(np.uint8)).save(OUT_DIR_SUBPATCH+"_left_right_" + str(iter) + ".png")

    print("°°°°°°°°°°° offset ", off_x, off_y)
    copy_region = Region(error_region.x1, error_region.y1, error_region.x2, error_region.y2)
    copy_region.clip(0, 0, height, width)
    print("copy region: x1, x2 - y1, y2: (", copy_region.x1, ", ", copy_region.x2, ") - (", copy_region.y1, ", ",
          copy_region.y2, ")")

    for curr in copy_region.points_iter():
        if not G or not G.has_node(curr.idx):
            im_src[curr.idx] = im_dst[curr.idx]
            for i in range(len(maps)):
                maps[i][curr.idx] = np.array(tran_ims[i])[curr.idx]
            ud_area[curr.idx] = im_dst[curr.idx]
            ud_mask[curr.idx] = 255
            seam_map.offset[curr.idx] = offset
            seam_map.has_left[curr.idx] = False
            seam_map.has_top[curr.idx] = False
            seam_map.top_nbr_cost[curr.idx] = 0
            seam_map.left_nbr_cost[curr.idx] = 0
        else:
            if curr.idx in right:
                im_src[curr.idx] = im_dst[curr.idx]
                for i in range(len(maps)):
                    maps[i][curr.idx] = np.array(tran_ims[i])[curr.idx]
                ud_area[curr.idx] = im_dst[curr.idx]
                ud_mask[curr.idx] = 255

                seam_map.offset[curr.idx] = offset

                update_seam_map(G, seam_map, left, right, curr, im_src, True)
                update_seam_map(G, seam_map, left, right, curr, im_src, False)

                right_nbr = Point(curr.x, curr.y + 1)
                bottom_nbr = Point(curr.x + 1, curr.y)
                if right_nbr.idx in left:
                    update_seam_map(G, seam_map, right, left, right_nbr, im_src, True)
                if bottom_nbr.idx in left:
                    update_seam_map(G, seam_map, right, left, bottom_nbr, im_src, False)

    im3 = Image.fromarray(ud_area.astype(np.uint8))


    if blur:
        # traslo l'immagine di input dell'offset scelto così estraggo l'immagine patch direttamente con le sue coordinate
        tran_im_og = ImageChops.offset(Image.fromarray(im_input.astype(np.uint8)), off_y, off_x)
        # tran_im_og.show()
        tran_im_og = np.array(tran_im_og, dtype=np.uint8)
        # scelto empiricamente
        blr_value = ((w+h)/2) / 100 + 0.5
        print("blur value: ", blr_value)
        mask = Image.fromarray(ud_mask.astype(np.uint8), mode="L")
        blr_mask = mask.filter(ImageFilter.GaussianBlur(blr_value))
        img_prev = Image.fromarray(img_bg.astype(np.uint8))
        img_upd = Image.fromarray(tran_im_og.astype(np.uint8))
        # blr_mask.show()
        # Image.composite(img_upd.convert("RGBA"), img_prev.convert("RGBA"), blr_mask).show()
        im_src = np.array((Image.composite(img_upd.convert("RGBA"), img_prev.convert("RGBA"), blr_mask)).convert("RGB"))
        for i in range(len(maps)):
            map_img = Image.fromarray(maps[i].astype(np.uint8))
            map_prev = Image.fromarray(prev_maps[i].astype(np.uint8))
            maps[i] = np.array((Image.composite(map_img.convert("RGBA"), map_prev.convert("RGBA"), blr_mask)).convert("RGB"))
        im_src[np.where(src_map == 0)] = 0

    im3.save(OUT_DIR_SUBPATCH+"_updated_area_" + str(iter) + ".png")

    # if im3.mode != 'RGBA':
    #     im3 = im3.convert('RGBA')
    # width, height = im3.size
    # gradient = Image.new('L', (width, 1), color=0xFF)
    # for x in range(width):
    #     gradient.putpixel((x, 0), 255-x)
    # alpha = gradient.resize(im3.size)


    return im_src


def handle_input_offset(height, width, im_input, offset, error_region: Region = None, region_size=None, i=0):
    dst_map = np.zeros([height, width]).astype(bool)
    im_dst = np.zeros([height, width, 3])

    h_in, w_in, _ = im_input.shape
    if region_size:
        h, w = region_size[0], region_size[1]
    else:
        h, w = h_in, w_in
    off_x, off_y = offset
    print("offset / region size in handle input offset ", off_x, off_y, " / ", region_size, " / ", h, w)

    dst_map[error_region.x1:error_region.x2, error_region.y1:error_region.y2] = 1
    im_input_copy = np.copy(im_input)
    im_input_copy[error_region.x1 - off_x:error_region.x1 - off_x + h,
    error_region.y1 - off_y:error_region.y1 - off_y + w] = 0
    Image.fromarray((im_input[error_region.x1 - off_x:error_region.x1 - off_x + h,
                     error_region.y1 - off_y:error_region.y1 - off_y + w]).astype(np.uint8)).save(
        OUT_DIR_SUBPATCH+"_TMP_IM_" + str(i) + ".png")

    Image.fromarray((im_input_copy).astype(np.uint8)).save(OUT_DIR_SUBPATCH+"_COPY_IM_" + str(i) + ".png")

    im_dst[error_region.x1:error_region.x2, error_region.y1:error_region.y2] = im_input[
                                                                               error_region.x1 - off_x:error_region.x1 - off_x + h,
                                                                               error_region.y1 - off_y:error_region.y1 - off_y + w]
    Image.fromarray((im_dst).astype(np.uint8)).save(OUT_DIR_SUBPATCH+"_IM_DST_" + str(i) + ".png")
    return im_dst, dst_map


def update_src_map(src_map, dst_map):
    src_map |= dst_map


def get_offset_random(im_src, src_map, im_input):
    if not src_map.any(): return (0, 0)
    h, w, _ = im_input.shape
    temp = np.where(src_map == 0)
    r, c = temp

    off_x_max = h // 2
    off_y_max = w // 2
    offset = [random.randint(r[0] - h, r[0] - 1), random.randint(c[0] - w, c[0] - 1)]
    return offset


# def get_cost(im_src, im_dst, src_map, dst_map):
#     overlap_map = src_map & dst_map
#     if not overlap_map.any(): return INF
#     im_diff = (im_src - im_dst) ** 2
#     im_diff = np.sum(im_diff, axis=2)
#     # im_diff = np.sqrt(im_diff)
#     At = im_diff[overlap_map]
#
#     return np.mean(At)


def get_conv(im_src, src_map, im_input):
    rev_im_input = im_input[::-1, ::-1]
    h, w, _ = im_input.shape
    rev_dst_map = np.ones([h, w])

    im_src_square = im_src.astype(float) ** 2
    im_input_square = im_input.astype(float) ** 2

    rev_im_input_square = im_input_square[::-1, ::-1]

    conv_overlap = fftconvolve(src_map, rev_dst_map)
    h, w = conv_overlap.shape

    conv_src = np.zeros([h, w, 3])
    conv_dst = np.zeros([h, w, 3])
    conv_cross = np.zeros([h, w, 3])

    for c in range(3):
        conv_src[:, :, c] = fftconvolve(im_src_square[:, :, c], rev_dst_map)
        conv_dst[:, :, c] = fftconvolve(src_map, rev_im_input_square[:, :, c])
        conv_cross[:, :, c] = fftconvolve(im_src[:, :, c], rev_im_input[:, :, c])

    return conv_src, conv_dst, conv_cross, conv_overlap


def get_cost_fft_based(conv_src, conv_dst, conv_cross, conv_overlap, offset, im_input):
    off_x, off_y = offset
    h, w, _ = im_input.shape
    x, y = off_x + h - 1, off_y + w - 1
    At = conv_src[x, y] + conv_dst[x, y] - 2 * conv_cross[x, y]
    At = np.sum(At, axis=-1)

    card = conv_overlap[x, y]
    return At / card


def get_offset_entire_matching(im_src, src_map, im_input):
    height, width, _ = im_src.shape
    h, w, _ = im_input.shape
    if not src_map.any(): return (0, 0)


    temp = np.where(src_map == 0)
    r, c = temp
    off_x_min = int(r[0] - 0.75 * h)
    off_x_max = int(r[0] - 0.25 * h)
    off_y_min = int(c[0] - 0.75 * w)
    off_y_max = int(c[0] - 0.25 * w)

    sigma = np.var(im_input)
    k = 0.01

    prob_map = np.zeros([h + height, w + width])
    idx_map = list(range(0, (h + height) * (w + width)))

    conv_src, conv_dst, conv_cross, conv_overlap = get_conv(im_src, src_map, im_input)

    for x in range(off_x_min, off_x_max):
        for y in range(off_y_min, off_y_max):
            # print(x, y)
            im_dst, dst_map = handle_input_offset(height, width, im_input, (x, y))
            # cost1 = get_cost(im_src, im_dst, src_map, dst_map)
            offset = (x, y)
            cost2 = get_cost_fft_based(conv_src, conv_dst, conv_cross, conv_overlap, offset, im_input)

            # print(cost1, cost2)
            prob = np.exp(-cost2 / (k * sigma + EPS))

            off_x = x - off_x_min
            off_y = y - off_y_min

            prob_map[off_x, off_y] = prob

    prob_map /= np.sum(prob_map)

    idx = np.random.choice(idx_map, size=1, p=prob_map.reshape(-1))
    # idx = np.argmax(prob_map.reshape(-1))
    off_x, off_y = np.unravel_index(idx, prob_map.shape)
    x, y = off_x + off_x_min, off_y + off_y_min
    return (int(x), int(y))


def get_error_cost(seam_map: SeamMap, error_region: Region):
    ret = 0
    for curr in error_region.points_iter():
        # curr = Point(-1, -1)
        left_nbr = curr.left_nbr()
        top_nbr = curr.top_nbr()
        if seam_map.has_left[curr.idx] and error_region.contains(left_nbr.x, left_nbr.y): ret += seam_map.left_nbr_cost[
            curr.idx]
        if seam_map.has_top[curr.idx] and error_region.contains(top_nbr.x, top_nbr.y): ret += seam_map.top_nbr_cost[
            curr.idx]

    return ret


def get_error_cost_fft_based(conv_left, conv_top, offset, region_size):
    rh, rw = region_size

    off_x, off_y = offset
    x, y = off_x + rh - 1, off_y + rw - 1
    return conv_left[x, y] + conv_top[x, y]


def get_first_unconverd_pixel(src_map: np.ndarray) -> Point:
    if src_map.all(): return Point(-1, -1)
    temp = np.where(src_map == 0)
    r, c = temp
    return Point(r[0], c[0])


def get_conv_error_region(seam_map: SeamMap, region_size):
    rh, rw = region_size
    region_map = np.ones([rh, rw]).astype(np.float32)
    conv_left = fftconvolve(seam_map.left_nbr_cost, region_map)
    conv_top = fftconvolve(seam_map.top_nbr_cost, region_map)

    return conv_left, conv_top


def get_error_region(src_map: np.ndarray, seam_map: SeamMap, region_size) -> Region:
    rh, rw = region_size
    height, width = src_map.shape
    ret_x = 0
    ret_y = 0

    temp = get_first_unconverd_pixel(src_map)

    if temp.idx == (-1, -1):
        conv_left, conv_top = get_conv_error_region(seam_map, region_size)
        max_error = -1
        for x in range(temp.x + 1, height - rh):
            for y in range(temp.y + 1, width - rw):
                # temp_error = get_error_cost(seam_map, Region(x, y, x + rh, y + rw))

                temp_error = get_error_cost_fft_based(conv_left, conv_top, (x, y), region_size)
                if temp_error > max_error:
                    max_error = temp_error
                    ret_x, ret_y = x, y

        ret_x += rh // 2
        ret_y += rw // 2
    else:
        ret_x = temp.x - rh // 2
        ret_y = temp.y - rw // 2

    ret_x = max(0, ret_x)
    ret_y = max(0, ret_y)
    ret_x = min(height - rh, ret_x)
    ret_y = min(width - rw, ret_y)
    return Region(ret_x, ret_y, ret_x + rh, ret_y + rw)


def get_offset_subpatch_matching(im_src, src_map, im_input, patch_region: Region, patch_size, i):
    if not src_map.any(): return 0, 0

    h, w, _ = im_input.shape
    rh, rw = patch_size

    im_src_subpatch = np.zeros(im_src.shape)
    dst_map = np.ones([h, w]).astype(bool)

    # region_slice = error_region.slice()
    #GG
    # region_slice = (slice(error_region.x1, error_region.x1 + region_size[0]), slice(error_region.y1, error_region.y1 + region_size[1]))
    #GG -> +20 serve è quello che funziona se si fa espansione con patch 60x60
    # region_slice = (slice(error_region.x1, error_region.x1 + 15), slice(error_region.y1, error_region.y1 + 15))
    # print("region slice ",region_slice)
    region_slice = (slice(patch_region.x1, patch_region.x2), slice(patch_region.y1, patch_region.y2))
    # region_slice = (slice(max(0, error_region.x1-region_size[0]), error_region.x1 ), slice(max(0, error_region.y1-region_size[1]), error_region.y1 ))
    # estrazione della zone di errore dalla immagine attuale (output incompleto)
    im_src_subpatch = im_src[region_slice]
    # print("subpatch shape ", im_src_subpatch[:, :, 0].shape)

    tmp_point = get_first_unconverd_pixel(im_src_subpatch[:, :, 0])
    print("tmp point ", tmp_point.x, tmp_point.y)
    if tmp_point.y == 0 and tmp_point.x > 0:
        region_slice = (slice(patch_region.x1, patch_region.x1 + tmp_point.x), slice(patch_region.y1, patch_region.y2))
    else:
        region_slice = (slice(patch_region.x1, patch_region.x2), slice(patch_region.y1, patch_region.y1 + tmp_point.y))
    print("-----region_slice aggiornata", region_slice)
    im_src_subpatch = im_src[region_slice]

    Image.fromarray(im_src_subpatch.astype(np.uint8)).save(OUT_DIR_SUBPATCH+"_im_SRC_" + str(i) + ".png")

    # print(im_src_subpatch)

    conv_src, conv_dst, conv_cross, conv_overlap = get_conv(im_input, dst_map, im_src_subpatch)
    Image.fromarray((conv_dst / conv_dst.max() * 255).astype(np.uint8)).save(OUT_DIR_SUBPATCH+"conv_dst_" + str(i) + ".png")
    Image.fromarray((conv_src / conv_src.max() * 255).astype(np.uint8)).save(OUT_DIR_SUBPATCH+"conv_src_" + str(i) + ".png")
    Image.fromarray((conv_cross / conv_cross.max() * 255).astype(np.uint8)).save(OUT_DIR_SUBPATCH+"conv_cross_" + str(i) + ".png")
    Image.fromarray((conv_overlap / conv_overlap.max() * 255).astype(np.uint8)).save(
        OUT_DIR_SUBPATCH+"conv_overlap_" + str(i) + ".png")

    #GG
    off_x_min = 0
    off_x_max = h - rh
    off_y_min = 0
    off_y_max = w - rw
    temp = np.where(src_map == 0)
    r, c = temp
    print("primo pixel vuoto ", r[0], c[0])
    print("offset max ", off_x_max, off_y_max)
    print("offset min ", off_x_min, off_y_min)
    # per la scelta dell'offset
    #GG
    sigma = np.var(im_src_subpatch)
    print("sigma ", sigma)
    # k = 0.01
    k = 0.05

    prob_map = np.zeros([h, w])
    cost_map = np.zeros([off_x_max - off_x_min, off_y_max - off_y_min])
    idx_map = list(range(0, (h) * (w)))

    for x in range(off_x_min, off_x_max):
        for y in range(off_y_min, off_y_max):
            offset = (x, y)
            cost2 = get_cost_fft_based(conv_src, conv_dst, conv_cross, conv_overlap, offset, im_src_subpatch)

            prob = np.exp(-cost2 / (k * sigma + EPS))

            off_x = x - off_x_min
            off_y = y - off_y_min

            prob_map[off_x, off_y] = prob
            cost_map[off_x, off_y] = cost2

    cost_map[max(0, patch_region.x1 - patch_size[0] // 2):patch_region.x2,
             max(0, patch_region.y1 - patch_size[1] // 2):patch_region.y2] = np.max(cost_map)

    if i == 0:
        np.savetxt(OUT_DIR_SUBPATCH+"cost2.csv", cost_map, delimiter=",")
        np.savetxt(OUT_DIR_SUBPATCH+"prob.csv", prob_map, delimiter=",")

    print("sum prob ", np.sum(prob_map))
    prob_map /= np.sum(prob_map)

    #GG tolto randomicità
    # argmax = np.argmax(prob_map.reshape(-1))

    # off_x, off_y = np.unravel_index(idx_map[argmax], prob_map.shape)
    # questo era per estrarre i primi 5
    # xs, ys = np.unravel_index(np.argsort(cost_map, axis=None), cost_map.shape)
    # ii = list(zip(xs[:5], ys[:5]))
    # off_x, off_y = random.choice(ii)

    #minimo assoluto (per stampa)
    off_x, off_y = np.unravel_index(cost_map.argmin(), cost_map.shape)
    print("offset costo MIN ", off_x, off_y)

    # argmin = np.argmin(cost_map)

    # estrazione dei minimi + scelta random
    epsilon = 0.15 #TODO parametrizzare per l'utente?
    mins_x, mins_y = np.where(cost_map < cost_map.min()*(1+epsilon))
    mins_coord = list(zip(mins_x, mins_y))
    off_x, off_y = random.choice(mins_coord)

    # perc = np.percentile(cost_map, 0.02)
    # mins_x, mins_y = np.where(cost_map<perc)
    # off_x, off_y = random.choice(list(zip(mins_x, mins_y)))

    print("cost value MIN ", (off_x, off_y), cost_map[off_x, off_y])
    # print("percentile ", perc)
    print("**altri minimi: ", len(list(zip(mins_x, mins_y))), list(zip(mins_x, mins_y)))
    print("offset random ", off_x, off_y)
    print("cost offset random ", cost_map[off_x, off_y])

    x, y = off_x + off_x_min, off_y + off_y_min

    true_x, true_y = patch_region.x1 - x, patch_region.y1 - y
    return (int(true_x), int(true_y))