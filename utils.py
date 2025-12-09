class TwoDPoint(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.tuple = (x, y)

    def __getitem__(self, idx):
        if idx == 0:
            return self.x
        else:
            return self.y

    def __setitem__(self, idx, val):
        if idx == 0:
            self.x = val
        if idx == 1:
            self.y = val

    def __str__(self):
        return "(" + str(self.x) + "," + str(self.y) + ")"

    def __eq__(self, other):
        if self.x == other.x and self.y == other.y:
            return True
        else:
            return False


class Coordinates(object):
    def __init__(self, a: tuple[int, int], b: tuple[int, int], c: tuple[int, int], d: tuple[int, int]):
        self.A = TwoDPoint(a[0], a[1])
        self.B = TwoDPoint(b[0], b[1])
        self.C = TwoDPoint(c[0], c[1])
        self.D = TwoDPoint(d[0], d[1])
        self.start = self.A
        self.end = self.C

    def set_a(self, a):
        self.A = a
        self.start = self.A

    def set_b(self, b):
        self.B = b

    def set_c(self, c):
        self.C = c
        self.start = self.C

    def set_d(self, d):
        self.D = d

    def max(self):
        maxx = max(self.A[0], self.B[0], self.C[0], self.D[0])
        maxy = max(self.A[1], self.B[1], self.C[1], self.D[1])
        return (maxx, maxy)

    def min(self):
        minx = min(self.A[0], self.B[0], self.C[0], self.D[0])
        miny = min(self.A[1], self.B[1], self.C[1], self.D[1])
        return (minx, miny)

    def __getitem__(self, idx):
        if idx == 0:
            return self.A
        if idx == 1:
            return self.B
        if idx == 2:
            return self.C
        if idx == 3:
            return self.D

    def __setitem__(self, idx, val: TwoDPoint):
        if idx == 0:
            self.A = val
        if idx == 1:
            self.B = val
        if idx == 2:
            self.C = val
        if idx == 3:
            self.D = val

    def __str__(self):
        return "[" + str(self.A) + "," + str(self.B) + "," + str(self.C) + "," + str(self.D) + "]"
