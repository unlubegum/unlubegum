"""Topların önizleme görseli (analitik ışın izleme) -> onizleme.png"""
import numpy as np
from PIL import Image
from futbol_topu import G, is_pent, GROOVE_W, GROOVE_D, CUT

W, H = 1200, 700
img = np.zeros((H, W, 3)) + np.array([250, 240, 245]) / 255
yy, xx = np.mgrid[0:H, 0:W]
img[yy > 470] = np.array([255, 214, 226]) / 255   # pasta kreması
L = np.array([-0.5, 0.6, 0.8]); L /= np.linalg.norm(L)
# (merkez x, zemin y, çap mm) — piksel/mm = 4
balls = [(220, 560, 35), (420, 560, 50), (620, 560, 50), (820, 560, 50), (1010, 560, 35)]
for cx, gy, d in balls:
    R = d / 2 * 4
    cy = gy - R * CUT
    dx, dy = (xx - cx) / R, (cy - yy) / R
    r2 = dx ** 2 + dy ** 2
    m = (r2 < 1) & (dy > -CUT)
    nz = np.sqrt(np.clip(1 - r2, 0, 1))
    n = np.stack([dx, dy, nz], -1)
    # Dünya -> top: hafif eğik bakış
    a = np.radians(-18); b = np.radians(25)
    Rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    Ry = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    p = n[m] @ (Ry @ Rx)
    p = p[:, [0, 2, 1]] * [1, 1, 1]  # modelde z yukarı
    sc = p @ G.T
    o = np.argsort(-sc, 1)
    i, j = o[:, 0], o[:, 1]
    g = G[i] - G[j]
    dist = (d / 2) * (sc[np.arange(len(p)), i] - sc[np.arange(len(p)), j]) / np.linalg.norm(g, axis=1)
    col = np.where(is_pent[i][:, None], 0.12, 0.96) * np.ones((1, 3))
    groove = dist < GROOVE_W / 2
    col[groove] = 0.35
    diff = np.clip(n[m] @ L, 0, 1)
    spec = np.clip(n[m] @ ((L + [0, 0, 1]) / np.linalg.norm(L + [0, 0, 1])), 0, 1) ** 40
    shade = col * (0.35 + 0.65 * diff[:, None]) + 0.35 * spec[:, None]
    img[m] = np.clip(shade, 0, 1)
    # gölge
    sh = (((xx - cx) / (R * 1.0)) ** 2 + ((yy - gy - 4) / (R * 0.18)) ** 2 < 1) & ~m & (yy >= gy - 2)
    img[sh] *= 0.85
im = Image.fromarray((img * 255).astype(np.uint8))
im.save("onizleme.png")
