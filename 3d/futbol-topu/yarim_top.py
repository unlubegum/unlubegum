"""Tam yuvarlak futbol topu: iki yarım küre olarak basılıp yapıştırılır.

Her iki yarım da düz yüzü tablada, desteksiz basılır. İki yarımın düz yüzünde
3'er hizalama deliği var; deliklere 1,75 mm filament parçası (yaklaşık 5,5 mm)
takılır. Deliklerden biri farklı mesafede olduğu için yarımlar yalnızca doğru
açıda birleşir ve desen tam oturur.
Alt yarımın kutbunda kürdan/çubuk deliği var.
"""
import numpy as np
import trimesh
import manifold3d as mf
from futbol_topu import SIZES, HOLE_D, grooved_sphere, pent_shell, to_trimesh

PIN_HOLE_D, PIN_HOLE_H = 2.1, 3.0  # 1,75 mm filament pim için delik (mm)
TILT = np.radians(12)              # desen ek yerine daha dengeli dağılsın diye topu hafif döndür


def pin_spots(R):
    return [(0.5 * R, 0), (0.5 * R, 120), (0.33 * R, 240)]


def halves(diam):
    R = diam / 2
    body = grooved_sphere(diam)
    shell = pent_shell(R)
    body = body.rotate([np.degrees(TILT), 0, 0])
    shell = shell.rotate([np.degrees(TILT), 0, 0])
    big = 4 * R
    upper_box = mf.Manifold.cube([big, big, big], center=True).translate([0, 0, big / 2])
    lower_box = mf.Manifold.cube([big, big, big], center=True).translate([0, 0, -big / 2])
    out = {}
    for name, box in (("ust", upper_box), ("alt", lower_box)):
        b = body ^ box
        for r, a in pin_spots(R):
            x, y = r * np.cos(np.radians(a)), r * np.sin(np.radians(a))
            c = mf.Manifold.cylinder(2 * PIN_HOLE_H, PIN_HOLE_D / 2, PIN_HOLE_D / 2, 24).translate([x, y, -PIN_HOLE_H])
            b = b - c
        if name == "alt":
            b = b - mf.Manifold.cylinder(R * 0.6, HOLE_D / 2, HOLE_D / 2, 32).translate([0, 0, -R - 0.1])
        black = b ^ shell
        white = b - shell
        # Düz yüz tablaya: üst yarım zaten öyle; alt yarımı ters çevir
        parts = [x.rotate([180, 0, 0]) if name == "alt" else x for x in (b, white, black)]
        tm = [to_trimesh(x) for x in parts]
        z0 = tm[0].bounds[0][2]
        out[name] = [t.apply_translation([0, 0, -z0]) for t in tm]
    return out


def main():
    import os
    os.makedirs("stl/yarim", exist_ok=True)
    made = {}
    for name, d in SIZES.items():
        tag = f"{int(d)}mm"
        h = halves(d)
        for side, (one, white, black) in h.items():
            one.export(f"stl/yarim/yarim-{tag}-{side}-tek-renk.stl")
            print(tag, side, one.is_watertight, white.is_watertight, black.is_watertight, np.round(one.extents, 1))
        made[tag] = h
    # Snapmaker U1 tablası: 3 büyük + 2 orta top = 10 yarım, 2 parça (beyaz/siyah)
    yer = [("50mm", "ust", -84, 70), ("50mm", "alt", -28, 70), ("50mm", "ust", 28, 70), ("50mm", "alt", 84, 70),
           ("50mm", "ust", -84, 12), ("50mm", "alt", -28, 12),
           ("35mm", "ust", 22, 12), ("35mm", "alt", 66, 12), ("35mm", "ust", 22, -36), ("35mm", "alt", 66, -36)]
    whites, blacks = [], []
    for tag, side, x, y in yer:
        _, w, b = made[tag][side]
        whites.append(w.copy().apply_translation([x, y, 0]))
        blacks.append(b.copy().apply_translation([x, y, 0]))
    sc = trimesh.Scene()
    W, B = trimesh.util.concatenate(whites), trimesh.util.concatenate(blacks)
    sc.add_geometry(W, node_name="beyaz", geom_name="beyaz")
    sc.add_geometry(B, node_name="siyah", geom_name="siyah")
    sc.export("stl/yarim/tabla-yarim-3-buyuk-2-orta-iki-renk.3mf")
    allb = trimesh.util.concatenate([W, B]).bounds
    print("tabla boyutu:", np.round(allb[1] - allb[0], 1))


if __name__ == "__main__":
    main()
