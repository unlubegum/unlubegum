"""Yarım kürelerin önizlemesi (ressam algoritmasıyla basit çizim) -> yarim_onizleme.png"""
import numpy as np
import trimesh
from PIL import Image, ImageDraw

W, H = 1200, 560
img = Image.new("RGB", (W, H), (250, 240, 245))
dr = ImageDraw.Draw(img)
L = np.array([-0.4, -0.5, 0.75]); L /= np.linalg.norm(L)


def draw(path_w, path_b, cx, cy, scale, rx, rz, flip=False):
    tris, cols = [], []
    for path, base in ((path_w, 0.95), (path_b, 0.13)):
        m = trimesh.load(path)
        v = m.vertices - [0, 0, 0]
        if flip:  # düz yüz kameraya baksın
            v = v * [1, -1, -1]
        c, s = np.cos(rz), np.sin(rz)
        v = v @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]).T
        c, s = np.cos(rx), np.sin(rx)
        v = v @ np.array([[1, 0, 0], [0, c, -s], [0, s, c]]).T
        f = v[m.faces]
        n = np.cross(f[:, 1] - f[:, 0], f[:, 2] - f[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        vis = n[:, 1] < 0  # kamera -y yönünden bakıyor
        shade = np.clip(0.35 + 0.65 * np.clip(-(n @ [L[0], L[2], -L[1]]), 0, 1), 0, 1)
        shade = np.clip(0.3 + 0.7 * np.abs(n @ np.array([-0.3, -0.8, 0.5]) / np.linalg.norm([-0.3, -0.8, 0.5])), 0, 1)
        for tri, sh in zip(f[vis], shade[vis]):
            tris.append(tri); cols.append(base * sh)
    tris = np.array(tris)
    order = np.argsort(-tris[:, :, 1].mean(1))
    for k in order:
        t = tris[k]
        pts = [(cx + p[0] * scale, cy - p[2] * scale) for p in t]
        g = int(255 * cols[k])
        dr.polygon(pts, fill=(g, g, g))


import tempfile, os
from PIL import ImageFont
# Ayrı beyaz/siyah STL'ler yalnızca 3MF içinde; önizleme için yeniden üret
from yarim_top import halves
h = halves(50)
tmp = tempfile.mkdtemp()
for side in ("ust", "alt"):
    h[side][1].export(f"{tmp}/w_{side}.stl"); h[side][2].export(f"{tmp}/b_{side}.stl")
draw(f"{tmp}/w_ust.stl", f"{tmp}/b_ust.stl", 300, 330, 7, np.radians(-35), np.radians(20))
draw(f"{tmp}/w_alt.stl", f"{tmp}/b_alt.stl", 880, 300, 7, np.radians(55), np.radians(-20))
font = ImageFont.truetype("DejaVuSans.ttf", 22)
dr.text((300, 490), "Düz yüz: 3 hizalama deliği", fill=(60, 60, 60), font=font, anchor="mm")
dr.text((880, 490), "Alt kutup: kürdan deliği", fill=(60, 60, 60), font=font, anchor="mm")
img.save("yarim_onizleme.png")
