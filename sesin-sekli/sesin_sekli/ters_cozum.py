"""Formantlardan tüp şekline ters çözüm (acoustic-to-articulatory inversion).

Alan fonksiyonu, log-alanın birkaç kosinüs (DCT) bileşeni ile ifade edilir;
böylece şekil pürüzsüz ve basılabilir kalır. Uzunluk da serbest parametredir.
Hedef formantlarla simüle edilen formantlar arasındaki göreli fark,
differential evolution ile en aza indirilir.

Bu problem tek çözümlü değildir: aynı sesi veren birden çok şekil vardır.
Amaç anatomik doğruluk değil, aynı tınıyı veren basılabilir bir şekildir.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import differential_evolution

from .akustik import formantlar

N_KESIT = 36
N_KATSAYI = 6
A_MIN = 0.35e-4      # basılabilirlik: en dar kanal çapı ~6.7 mm
A_MAX = 9.0e-4       # en geniş: ~34 mm çap
L_MIN, L_MAX = 0.11, 0.21


@dataclass
class Sonuc:
    alanlar: np.ndarray      # m²
    uzunluk: float           # m
    hedef: np.ndarray        # Hz
    elde: np.ndarray         # Hz
    boyun_kesit: int

    @property
    def hata_yuzde(self) -> np.ndarray:
        return 100 * (self.elde - self.hedef) / self.hedef


def alan_fonksiyonu(katsayilar: np.ndarray, boyun_kesit: int, boyun_alan: float,
                    a_min: float = A_MIN, a_max: float = A_MAX) -> np.ndarray:
    x = (np.arange(N_KESIT) + 0.5) / N_KESIT
    a_notr = np.sqrt(a_min * a_max)
    log_a = np.log(a_notr) + sum(c * np.cos(np.pi * (k + 1) * x) for k, c in enumerate(katsayilar))
    a = np.clip(np.exp(log_a), a_min, a_max)
    a[:boyun_kesit] = boyun_alan
    return a


# Kolye: kanal en fazla ~13 mm; /a/ ve /i/ için dar-geniş oranı (≈16x alan) korunur.
KOLYE_CAP_MM = (3.2, 12.8)


def ters_coz(hedef_formantlar, boyun_mm: float = 12.0, boyun_cap_mm: float = 9.0,
             tohum: int = 0, iterasyon: int = 120, cap_mm: tuple | None = None) -> Sonuc:
    """hedef_formantlar: F1..Fn (Hz). Boyun: kaynağın takıldığı sabit çaplı giriş.

    cap_mm: (en dar, en geniş) kanal iç çapı; verilmezse düz tüp sınırları.
    """
    if cap_mm is None:
        a_min, a_max = A_MIN, A_MAX
    else:
        a_min, a_max = (np.pi * (c / 2000) ** 2 for c in cap_mm)
    hedef = np.asarray(hedef_formantlar, dtype=float)
    n = len(hedef)
    boyun_alan = np.pi * (boyun_cap_mm / 2000) ** 2
    agirlik = np.array([1.0, 1.0, 0.6, 0.3])[:n]

    def boyun_sayisi(L):
        return max(1, int(round(boyun_mm / 1000 / L * N_KESIT)))

    def maliyet(p):
        L, kats = p[0], p[1:]
        bk = boyun_sayisi(L)
        a = alan_fonksiyonu(kats, bk, boyun_alan, a_min, a_max)
        f = formantlar(a, L, adet=n)
        if np.any(np.isnan(f)):
            return 10.0
        hata = np.sum(agirlik * ((f - hedef) / hedef) ** 2)
        return hata + 1e-4 * np.sum(kats**2)

    sinirlar = [(L_MIN, L_MAX)] + [(-1.6, 1.6)] * N_KATSAYI
    r = differential_evolution(maliyet, sinirlar, seed=tohum, maxiter=iterasyon,
                               popsize=18, tol=1e-8, polish=True)
    L, kats = r.x[0], r.x[1:]
    bk = boyun_sayisi(L)
    a = alan_fonksiyonu(kats, bk, boyun_alan, a_min, a_max)
    return Sonuc(alanlar=a, uzunluk=L, hedef=hedef, elde=formantlar(a, L, adet=n), boyun_kesit=bk)
