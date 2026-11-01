"""Ses yolu akustiği: birbirine bağlı silindirlerden oluşan tüp modeli.

Glottis (ses kaynağı) ucunda hacim-hızı kaynağı, dudak ucunda bafıllı piston
radyasyon empedansı varsayılır. Her silindir bir 2x2 iletim (chain) matrisi
ile temsil edilir. Sonuç H(f) = U_dudak / U_glottis transfer fonksiyonudur;
bunun tepe noktaları formantlardır.

Tüm birimler SI (metre, m², Hz).
"""
from __future__ import annotations

import numpy as np

RHO = 1.14  # hava yoğunluğu (kg/m³), ~35 °C nemli hava
C = 350.0   # ses hızı (m/s), ağız içi sıcaklığında
KAYIP = 2.0e-4  # duvar/viskoz kayıp katsayısı (bant genişliğini ayarlar)


def transfer(alanlar: np.ndarray, uzunluk: float, frekanslar: np.ndarray) -> np.ndarray:
    """Karmaşık transfer fonksiyonu H(f) = U_dudak / U_glottis.

    alanlar: glottisten dudağa sıralı kesit alanları (m²)
    uzunluk: tüpün toplam uzunluğu (m)
    """
    alanlar = np.asarray(alanlar, dtype=float)
    f = np.asarray(frekanslar, dtype=float)
    w = 2 * np.pi * f
    l = uzunluk / len(alanlar)

    # Chain matris elemanları, frekans vektörü boyunca
    k11 = np.ones_like(f, dtype=complex)
    k12 = np.zeros_like(f, dtype=complex)
    k21 = np.zeros_like(f, dtype=complex)
    k22 = np.ones_like(f, dtype=complex)

    for a in alanlar:
        r = np.sqrt(a / np.pi)
        alfa = KAYIP * np.sqrt(f) / r  # Np/m, frekansla ve dar kesitle artar
        gamma = alfa + 1j * w / C
        z = RHO * C / a
        ch, sh = np.cosh(gamma * l), np.sinh(gamma * l)
        m11, m12, m21, m22 = ch, z * sh, sh / z, ch
        k11, k12, k21, k22 = (
            k11 * m11 + k12 * m21,
            k11 * m12 + k12 * m22,
            k21 * m11 + k22 * m21,
            k21 * m12 + k22 * m22,
        )

    a_dudak = alanlar[-1]
    r_dudak = np.sqrt(a_dudak / np.pi)
    ka = w / C * r_dudak
    z_rad = RHO * C / a_dudak * (ka**2 / 2 + 1j * 8 * ka / (3 * np.pi))
    return 1.0 / (k21 * z_rad + k22)


FREKANS_IZGARASI = np.arange(60.0, 5000.0, 8.0)


def formantlar(alanlar, uzunluk, adet: int = 4, frekanslar=FREKANS_IZGARASI) -> np.ndarray:
    """|H| tepe noktalarını parabolik interpolasyonla bulur. Eksik tepeler NaN."""
    h = np.abs(transfer(alanlar, uzunluk, frekanslar))
    db = 20 * np.log10(h + 1e-12)
    tepe = np.where((db[1:-1] > db[:-2]) & (db[1:-1] >= db[2:]))[0] + 1
    sonuc = []
    adim = frekanslar[1] - frekanslar[0]
    for i in tepe[:adet]:
        y0, y1, y2 = db[i - 1], db[i], db[i + 1]
        payda = y0 - 2 * y1 + y2
        kayma = 0.5 * (y0 - y2) / payda if payda != 0 else 0.0
        sonuc.append(frekanslar[i] + kayma * adim)
    sonuc += [np.nan] * (adet - len(sonuc))
    return np.array(sonuc)
