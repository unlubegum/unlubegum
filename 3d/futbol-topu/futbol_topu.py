"""Pasta süsü futbol topu (kesik ikosahedron) STL üretici.

Her boy için üç dosya çıkar:
  top-<D>mm-tek-renk.stl  -> tek parça; dikiş oyukları boyama kılavuzu olur
  top-<D>mm-beyaz.stl     -> çok renkli baskı için beyaz gövde
  top-<D>mm-siyah.stl     -> çok renkli baskı için siyah beşgenler
Alt kısmı düz kesik (destek gerekmez, pastada devrilmez), altta çubuk deliği var.
"""
import numpy as np
import trimesh
import manifold3d as mf

SIZES = {"buyuk": 50.0, "orta": 35.0}  # çap (mm)
GROOVE_W = 1.0      # dikiş oyuğu genişliği (mm)
GROOVE_D = 0.6      # dikiş oyuğu derinliği (mm)
BLACK_T = 1.2       # siyah beşgen kabuk kalınlığı (mm)
CUT = 0.70          # alt düz kesim: merkezden R*CUT aşağıda (~44° eğim, destek gerekmez)
HOLE_D = 4.2        # kürdan/çubuk deliği çapı (mm)

# --- Kesik ikosahedron yüzleri: 12 beşgen + 20 altıgen ---
phi = (1 + 5 ** 0.5) / 2
ico_v = np.array([[-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
                  [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
                  [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1]], float)
ico_f = np.array([[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4],
                  [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8],
                  [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]])
# Bir beşgen tam üstte olsun
z = ico_v[0] / np.linalg.norm(ico_v[0])
a = np.cross(z, [0, 0, 1.0]); s = np.linalg.norm(a); c = z @ [0, 0, 1.0]
K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
Rot = np.eye(3) + K + K @ K * ((1 - c) / s ** 2)
ico_v = ico_v @ Rot.T

nbrs = {i: set() for i in range(12)}
for f in ico_f:
    for i in range(3):
        nbrs[f[i]].add(f[(i + 1) % 3]); nbrs[f[i]].add(f[(i + 2) % 3])

faces = []  # (birim normal, düzlem uzaklığı, köşeler, beşgen mi)
for i in range(12):
    pts = np.array([ico_v[i] + (ico_v[j] - ico_v[i]) / 3 for j in nbrs[i]])
    faces.append((pts, True))
for f in ico_f:
    pts = []
    for k in range(3):
        p, q = ico_v[f[k]], ico_v[f[(k + 1) % 3]]
        pts += [p + (q - p) / 3, p + 2 * (q - p) / 3]
    faces.append((np.array(pts), False))
N = np.array([p.mean(0) / np.linalg.norm(p.mean(0)) for p, _ in faces])
D = np.array([p.mean(0) @ n for (p, _), n in zip(faces, N)])
G = N / D[:, None]   # nokta p, max(p·G) olan yüze düşer (merkezî izdüşüm)
is_pent = np.array([pent for _, pent in faces])


def to_manifold(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                               tri_verts=np.asarray(m.faces, np.uint32)))


def to_trimesh(man):
    m = man.to_mesh()
    t = trimesh.Trimesh(m.vert_properties[:, :3], m.tri_verts, process=True, validate=True)
    # Kesişimlerden kalan sıfır hacimli kırıntıları at
    parts = [q for q in t.split(only_watertight=False) if abs(q.volume) > 1e-3]
    return trimesh.util.concatenate(parts)


def grooved_sphere(diam):
    """Dikiş oyuklu tam küre (merkez orijinde)."""
    R = diam / 2
    sph = trimesh.creation.icosphere(subdivisions=7 if diam > 40 else 6)
    u = sph.vertices / np.linalg.norm(sph.vertices, axis=1, keepdims=True)
    sc = u @ G.T
    order = np.argsort(-sc, axis=1)
    i, j = order[:, 0], order[:, 1]
    g = G[i] - G[j]
    dist = R * (sc[np.arange(len(u)), i] - sc[np.arange(len(u)), j]) / np.linalg.norm(g, axis=1)
    x = np.clip(dist / (GROOVE_W / 2), 0, 1)
    r = R - GROOVE_D * (1 - x ** 2) * (x < 1)
    sph.vertices = u * r[:, None]
    return to_manifold(sph)


def pent_shell(R):
    """Siyah beşgenlerin dış kabuğu: beşgen konileri − iç küre."""
    cones = None
    for (pts, pent) in faces:
        if not pent:
            continue
        # Sınırı oyuk tabanından 0.2 mm içeri al (yüzeyler çakışıp bozulmasın)
        ctr = pts.mean(0)
        pts = ctr + (pts - ctr) * (1 - 0.2 / (0.357 * R))
        hull = mf.Manifold.hull_points(np.vstack([[0, 0, 0], pts / np.linalg.norm(pts, axis=1, keepdims=True) * 3 * R]))
        cones = hull if cones is None else cones + hull
    return cones - mf.Manifold.sphere(R - GROOVE_D - BLACK_T, 256)


def ball(diam):
    R = diam / 2
    body = grooved_sphere(diam)
    # Alt düz kesim + çubuk deliği
    big = 4 * R
    body = body - mf.Manifold.cube([big, big, big], center=True).translate([0, 0, -R * CUT - big / 2])
    hole = mf.Manifold.cylinder(R * 0.9, HOLE_D / 2, HOLE_D / 2, 32).translate([0, 0, -R * CUT - 0.1])
    body = body - hole
    shell = pent_shell(R)
    black = body ^ shell
    white = body - shell
    # Yere otursun
    lift = [0, 0, R * CUT]
    return [to_trimesh(x.translate(lift)) for x in (body, white, black)]


def tabla():
    """Snapmaker U1 gibi çok renkli yazıcılar için: 3 büyük + 2 orta, tek tabla, 2 parça (beyaz/siyah)."""
    import glob
    yer = [("50mm", -58, 32), ("50mm", 0, 32), ("50mm", 58, 32), ("35mm", -30, -30), ("35mm", 30, -30)]
    whites, blacks = [], []
    for tag, x, y in yer:
        whites.append(trimesh.load(f"stl/top-{tag}-beyaz.stl").apply_translation([x, y, 0]))
        blacks.append(trimesh.load(f"stl/top-{tag}-siyah.stl").apply_translation([x, y, 0]))
    sc = trimesh.Scene()
    sc.add_geometry(trimesh.util.concatenate(whites), node_name="beyaz", geom_name="beyaz")
    sc.add_geometry(trimesh.util.concatenate(blacks), node_name="siyah", geom_name="siyah")
    sc.export("stl/tabla-3-buyuk-2-orta-iki-renk.3mf")


if __name__ == "__main__":
    import os
    os.makedirs("stl", exist_ok=True)
    for name, d in SIZES.items():
        one, white, black = ball(d)
        tag = f"{int(d)}mm"
        one.export(f"stl/top-{tag}-tek-renk.stl")
        white.export(f"stl/top-{tag}-beyaz.stl")
        black.export(f"stl/top-{tag}-siyah.stl")
        sc = trimesh.Scene()
        sc.add_geometry(white, node_name="beyaz", geom_name="beyaz")
        sc.add_geometry(black, node_name="siyah", geom_name="siyah")
        sc.export(f"stl/top-{tag}-iki-renk.3mf")
        print(tag, "watertight:", one.is_watertight, white.is_watertight, black.is_watertight,
              "boyut:", np.round(one.extents, 1))
    tabla()
