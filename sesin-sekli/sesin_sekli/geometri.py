"""Alan fonksiyonundan basılabilir, su geçirmez (watertight) STL tüp üretimi.

Tüp dik basılır: glottis (kaynak) ucu tablada, dudak ucu yukarıda.
Dış yüzey düz silindir, iç kanal alan fonksiyonunu izler.
"""
from __future__ import annotations

import struct

import numpy as np

from .akustik import formantlar


def baski_profili(alanlar: np.ndarray, uzunluk: float, ornek_kesit: int = 4):
    """Basamaklı alanları kesit merkezleri arasında doğrusal yumuşatır.

    Döndürür: z (mm), iç yarıçap (mm). Boyun (sabit kesitler) korunur.
    """
    n = len(alanlar)
    l = uzunluk / n
    merkez = (np.arange(n) + 0.5) * l
    z = np.linspace(0, uzunluk, n * ornek_kesit + 1)
    r = np.sqrt(np.asarray(alanlar) / np.pi)
    r_z = np.interp(z, merkez, r)
    return z * 1000, r_z * 1000


def profil_formantlari(z_mm, r_mm, adet=4, n=144):
    """Yumuşatılmış baskı profilinin simüle formantları (tutarlılık kontrolü)."""
    zz = np.linspace(0, z_mm[-1], n + 1)
    orta = (zz[:-1] + zz[1:]) / 2
    r = np.interp(orta, z_mm, r_mm) / 1000
    return formantlar(np.pi * r**2, z_mm[-1] / 1000, adet=adet)


def en_buyuk_sarkma_derece(z_mm, r_mm) -> float:
    """Dik baskıda (glottis tablada) iç kanalın yukarı doğru daraldığı en dik açı.

    Kanal daraldıkça duvar boşluğun üstüne sarkar; ~45° üstü destek ister.
    """
    egim = -np.diff(r_mm) / np.diff(z_mm)
    return float(np.degrees(np.arctan(max(0.0, egim.max()))))


def tup_ucgenleri(z_mm, r_mm, duvar_mm=2.4, dilim=96):
    """Kapalı yüzey üçgenleri (N, 3, 3) mm cinsinden."""
    R = float(np.max(r_mm) + duvar_mm)
    t = np.linspace(0, 2 * np.pi, dilim, endpoint=False)
    cs, sn = np.cos(t), np.sin(t)

    def halka(r, z):
        return np.stack([r * cs, r * sn, np.full(dilim, z)], axis=1)

    ic = [halka(r, z) for r, z in zip(r_mm, z_mm)]
    dis_alt, dis_ust = halka(R, z_mm[0]), halka(R, z_mm[-1])
    tri = []

    def serit(alt, ust, disa_bakan: bool):
        for i in range(dilim):
            j = (i + 1) % dilim
            a, b, c, d = alt[i], alt[j], ust[j], ust[i]
            if disa_bakan:
                tri.extend([(a, b, c), (a, c, d)])
            else:
                tri.extend([(a, c, b), (a, d, c)])

    serit(dis_alt, dis_ust, True)               # dış duvar, normal dışa
    for k in range(len(ic) - 1):
        serit(ic[k], ic[k + 1], False)           # iç kanal, normal eksene
    # alt kapak (normal -z): dış halka ile iç halka arası
    for i in range(dilim):
        j = (i + 1) % dilim
        a, b, c, d = dis_alt[i], dis_alt[j], ic[0][j], ic[0][i]
        tri.extend([(a, c, b), (a, d, c)])
    # üst kapak (normal +z)
    for i in range(dilim):
        j = (i + 1) % dilim
        a, b, c, d = dis_ust[i], dis_ust[j], ic[-1][j], ic[-1][i]
        tri.extend([(a, b, c), (a, c, d)])
    return np.array(tri, dtype=np.float64)


def isaretli_hacim(tri: np.ndarray) -> float:
    """Diverjans teoremiyle hacim (mm³); normaller doğruysa pozitif."""
    return float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6)


def stl_yaz(yol: str, tri: np.ndarray, baslik: str = "sesin-sekli") -> None:
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    with open(yol, "wb") as f:
        f.write(baslik.encode()[:80].ljust(80, b"\0"))
        f.write(struct.pack("<I", len(tri)))
        for nn, t in zip(n.astype(np.float32), tri.astype(np.float32)):
            f.write(nn.tobytes() + t.tobytes() + b"\0\0")


def profil_svg(yol: str, z_mm, r_mm, duvar_mm=2.4, baslik="") -> None:
    """Tüpün yandan kesit görünümü (yatay: glottis solda, dudak sağda)."""
    R = float(np.max(r_mm) + duvar_mm)
    olcek = 4.0
    gen, yuk = z_mm[-1] * olcek + 40, 2 * R * olcek + 60
    cy = 30 + R * olcek

    def nokta(z, y):
        return f"{20 + z * olcek:.1f},{cy - y * olcek:.1f}"

    ust = " ".join(nokta(z, r) for z, r in zip(z_mm, r_mm))
    alt = " ".join(nokta(z, -r) for z, r in zip(z_mm[::-1], r_mm[::-1]))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{gen:.0f}" height="{yuk:.0f}" font-family="sans-serif">
<rect width="100%" height="100%" fill="#fff"/>
<rect x="20" y="{cy - R * olcek:.1f}" width="{z_mm[-1] * olcek:.1f}" height="{2 * R * olcek:.1f}" fill="#d9d4cc"/>
<polygon points="{ust} {alt}" fill="#fff" stroke="#b5462e" stroke-width="1.5"/>
<text x="20" y="18" font-size="13">{baslik}</text>
<text x="20" y="{yuk - 8:.0f}" font-size="11">glottis (kaynak) · uzunluk {z_mm[-1]:.0f} mm</text>
<text x="{gen - 20:.0f}" y="{yuk - 8:.0f}" font-size="11" text-anchor="end">dudak (ağız)</text>
</svg>"""
    with open(yol, "w", encoding="utf-8") as f:
        f.write(svg)
