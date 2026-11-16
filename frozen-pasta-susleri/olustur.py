import sys, os, zipfile, numpy as np, cv2
from PIL import Image
from shapely.geometry import Polygon, MultiPolygon, box
from shapely.ops import unary_union
from sklearn.cluster import KMeans
import trimesh

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
P = np.array(Image.open(os.path.join(os.path.dirname(__file__), 'panel.png')).convert('RGB'))
H, W = P.shape[:2]

BASE_T = 2.4      # mm, govde kalinligi (arka duz)
COLOR_T = 0.6     # mm, ust renk katmani
DARK_EXTRA = 0.4  # en koyu renk biraz daha yuksek -> tek renk baskida da detay
STAKE_W = 6.0     # mm cubuk genisligi
STAKE_LEN = 40.0  # mm silüetin altindan uzunluk
STAKE_TIP = 10.0  # mm sivri uc

# --- Anna'nin uzerindeki kamera ikonunu temizle (inpaint) ---
ico = np.zeros((H, W), np.uint8)
cv2.circle(ico, (40, 1262), 48, 255, -1)
ico[:, 110:] = 0
P = cv2.inpaint(P, ico, 9, cv2.INPAINT_TELEA)

bg = np.array([227, 239, 255])
d = np.sqrt(((P.astype(int) - bg) ** 2).sum(2))
M = (d > 14).astype(np.uint8)
M = cv2.morphologyEx(M, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
M = cv2.morphologyEx(M, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
# Olaf ile Kristoff'u ayir
M[1080:1165, 409:412] = 0
# Kristoff ustundeki kar tanesini ayir
M[790:975, 580:742] = 0
n, LAB, ST, _ = cv2.connectedComponentsWithStats(M)

def comp_at(x, y):
    return LAB == LAB[y, x]

def fill_holes(m):
    m = m.astype(np.uint8)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = np.zeros_like(m)
    cv2.drawContours(out, cnts, -1, 1, -1)
    return out.astype(bool)

def largest(m):
    n, l, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8))
    if n <= 1: return m
    i = 1 + np.argmax(st[1:, 4])
    return l == i

NAMES = {
    'Beyaz': (245, 245, 245), 'Acik Mavi': (150, 200, 230), 'Turkuaz': (40, 150, 170),
    'Mavi': (40, 70, 170), 'Lacivert': (25, 35, 80), 'Koyu Gri': (50, 55, 60),
    'Siyah': (20, 20, 20), 'Ten': (235, 190, 160), 'Kahverengi': (110, 70, 40),
    'Mor/Bordo': (130, 30, 90), 'Kirmizi': (170, 40, 40), 'Turuncu': (230, 120, 40),
    'Sari/Sarisin': (230, 210, 150), 'Gri': (140, 140, 145), 'Bej': (200, 180, 160),
}
def cname(c):
    return min(NAMES, key=lambda k: np.sum((np.array(NAMES[k]) - c) ** 2))

UP = 4
def mask_to_geom(m, mmpx, smooth=1.2):
    """binary mask (rows=y down) -> shapely geometry in mm (y up)."""
    m8 = (m.astype(np.uint8) * 255)
    big = cv2.resize(m8, None, fx=UP, fy=UP, interpolation=cv2.INTER_LINEAR)
    big = cv2.GaussianBlur(big, (0, 0), smooth * UP)
    big = (big > 127).astype(np.uint8)
    cnts, hier = cv2.findContours(big, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None: return Polygon()
    hier = hier[0]
    polys = []
    s = mmpx / UP
    def tp(c):
        c = c[:, 0, :].astype(float)
        return [(x * s, -y * s) for x, y in c]
    for i, c in enumerate(cnts):
        if hier[i][3] != -1 or len(c) < 4: continue
        holes = []
        j = hier[i][2]
        while j != -1:
            if len(cnts[j]) >= 4: holes.append(tp(cnts[j]))
            j = hier[j][0]
        pg = Polygon(tp(c), holes).buffer(0)
        if not pg.is_empty: polys.append(pg)
    g = unary_union(polys).simplify(0.04)
    return g

def polys(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    return [p for p in getattr(g, 'geoms', []) if isinstance(p, Polygon)]

def extrude(g, z0, z1, min_area=0.6):
    ms = []
    for p in polys(g):
        if p.area < min_area: continue
        t = trimesh.creation.extrude_polygon(p, z1 - z0)
        t.apply_translation([0, 0, z0])
        ms.append(t)
    return trimesh.util.concatenate(ms) if ms else None

def build(name, m, size_mm, along='h', k=4, stakes=1, stake_inset=7.0, out_dir=OUT):
    m = fill_holes(largest(m))
    ys, xs = np.where(m)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    m = m[y0:y1, x0:x1]
    img = P[y0:y1, x0:x1].copy()
    hpx, wpx = m.shape
    mmpx = size_mm / (hpx if along == 'h' else wpx)

    # ---- renk kumeleme ----
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(float)
    sel = m.reshape(-1)
    km = KMeans(n_clusters=k, n_init=6, random_state=0).fit(lab[sel][::3])
    lbl = km.predict(lab).reshape(hpx, wpx)
    cent = cv2.cvtColor(km.cluster_centers_.reshape(1, -1, 3).astype(np.uint8), cv2.COLOR_LAB2RGB)[0].astype(int)
    lbl = np.where(m, lbl, 255).astype(np.uint8)
    lbl = cv2.medianBlur(lbl, 5)
    lbl = np.where(m, lbl, 255)
    base_c = int(np.argmax(cent.sum(1)))  # en acik renk = govde (beyaz)
    dark_c = int(np.argmin(cent.sum(1)))

    # ---- govde silueti + cubuk ----
    sil = mask_to_geom(m, mmpx, smooth=1.5)
    sil = max(polys(sil), key=lambda p: p.area) if len(polys(sil)) > 1 else sil
    minx, miny, maxx, maxy = sil.bounds
    # alt kenara yakin sutunlar
    bottoms = np.array([np.max(np.where(m[:, c])[0]) if m[:, c].any() else -1 for c in range(wpx)])
    near = np.where(bottoms >= hpx - 1 - 8.0 / mmpx)[0]
    if stakes == 1:
        cxs = [np.median(near)]
    else:
        cxs = [np.percentile(near, 15), np.percentile(near, 85)]
    stake_geoms = []
    for cx in cxs:
        cx_mm = cx * mmpx
        c = int(cx)
        top = -(bottoms[c] * mmpx) + stake_inset
        bot = miny - STAKE_LEN
        hw = STAKE_W / 2
        sg = Polygon([(cx_mm - hw, top), (cx_mm + hw, top), (cx_mm + hw, bot + STAKE_TIP),
                      (cx_mm + 0.6, bot), (cx_mm - 0.6, bot), (cx_mm - hw, bot + STAKE_TIP)])
        stake_geoms.append(sg)
    body = unary_union([sil] + stake_geoms).buffer(0)

    parts = [('Govde_' + cname(cent[base_c]).replace('/', '-').replace(' ', ''), cent[base_c],
              extrude(body, 0, BASE_T))]
    inner = sil.buffer(-0.3)
    for ci in range(k):
        if ci == base_c: continue
        rm = (lbl == ci)
        rm = cv2.morphologyEx(rm.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
        g = mask_to_geom(rm, mmpx, smooth=0.8).intersection(inner).buffer(-0.02)
        top = BASE_T + COLOR_T + (DARK_EXTRA if ci == dark_c else 0)
        mesh = extrude(g, BASE_T, top)
        if mesh is not None:
            parts.append(('Renk_' + cname(cent[ci]).replace('/', '-').replace(' ', ''), cent[ci], mesh))

    # Orta noktaya tasi (x ortala, y>=0)
    allb = trimesh.util.concatenate([p[2] for p in parts]).bounds
    off = [-(allb[0][0] + allb[1][0]) / 2, -allb[0][1], 0]
    for p in parts: p[2].apply_translation(off)
    write_3mf(os.path.join(out_dir, name + '.3mf'), name, parts)
    preview(os.path.join(out_dir, name + '_onizleme.png'), parts)
    sz = trimesh.util.concatenate([p[2] for p in parts]).extents
    print(f'{name}: {sz[0]:.0f} x {sz[1]:.0f} x {sz[2]:.1f} mm, parcalar:',
          [(p[0], p[2].is_watertight) for p in parts])

def write_3mf(path, name, parts):
    def hexc(c): return '#%02X%02X%02XFF' % tuple(int(v) for v in c)
    objs = []
    mats = ''.join(f'<base name="{pn}" displaycolor="{hexc(c)}"/>' for pn, c, _ in parts)
    for i, (pn, c, mesh) in enumerate(parts):
        mesh.merge_vertices()
        v = '\n'.join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{cc:.4f}"/>' for a, b, cc in mesh.vertices)
        t = '\n'.join(f'<triangle v1="{a}" v2="{b}" v3="{cc}"/>' for a, b, cc in mesh.faces)
        objs.append(f'<object id="{i+2}" type="model" name="{pn}" pid="1" pindex="{i}"><mesh><vertices>\n{v}\n</vertices><triangles>\n{t}\n</triangles></mesh></object>')
    comps = ''.join(f'<component objectid="{i+2}"/>' for i in range(len(parts)))
    cid = len(parts) + 2
    model = f'''<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
<metadata name="Title">{name}</metadata>
<resources>
<basematerials id="1">{mats}</basematerials>
{''.join(objs)}
<object id="{cid}" type="model" name="{name}"><components>{comps}</components></object>
</resources>
<build><item objectid="{cid}" transform="1 0 0 0 1 0 0 0 1 120 120 0"/></build>
</model>'''
    ct = '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'''
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ct)
        z.writestr('_rels/.rels', rels)
        z.writestr('3D/3dmodel.model', model)

def preview(path, parts):
    allm = trimesh.util.concatenate([p[2] for p in parts])
    (x0, y0, _), (x1, y1, _) = allm.bounds
    s = 6
    img = np.full((int((y1 - y0) * s) + 20, int((x1 - x0) * s) + 20, 3), 40, np.uint8)
    for pn, c, mesh in sorted(parts, key=lambda p: p[2].bounds[1][2]):
        for f in mesh.faces[mesh.face_normals[:, 2] > 0.9]:
            pts = mesh.vertices[f][:, :2]
            pts = np.stack([(pts[:, 0] - x0) * s + 10, (y1 - pts[:, 1]) * s + 10], 1).astype(np.int32)
            cv2.fillPoly(img, [pts], tuple(int(v) for v in c))
    Image.fromarray(img).save(path)

if __name__ == '__main__':
    build('01_Elsa_HappyBirthday', comp_at(200, 200), 130, along='w', k=4, stakes=2)
    build('02_Buz_Sato', comp_at(640, 500), 140, along='h', k=4, stakes=2)
    build('03_Elsa', comp_at(80, 700), 120, along='h', k=4, stakes=1)
    build('04_Anna', comp_at(80, 1100), 110, along='h', k=4, stakes=1)
    build('05_Olaf', comp_at(320, 1250), 75, along='h', k=4, stakes=1)
    build('06_Kristoff_Sven', comp_at(500, 1000), 140, along='w', k=4, stakes=2)
    build('07_Kar_Tanesi', comp_at(878, 256), 45, along='h', k=3, stakes=1, stake_inset=12)
