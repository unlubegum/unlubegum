"""Çalıştırma: cd sesin-sekli && python3 -m pytest -q   (veya: python3 tests/test_sesin_sekli.py)"""
import collections
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sesin_sekli.akustik import C, formantlar
from sesin_sekli.formant import formant_cikar
from sesin_sekli.geometri import baski_profili, isaretli_hacim, profil_formantlari, tup_ucgenleri
from sesin_sekli.sentez import FS, sesli_harf
from sesin_sekli.ters_cozum import ters_coz


def test_duzgun_tup_ceyrek_dalga():
    """Düzgün tüp ≈ (2n-1)c/4L; dudak uç düzeltmesi formantları biraz düşürür."""
    L = 0.17
    f = formantlar(np.full(36, 3e-4), L)
    teori = np.array([(2 * n - 1) * C / (4 * L) for n in range(1, 5)])
    oran = f / teori
    assert np.all((oran > 0.92) & (oran < 1.0)), oran


def test_ters_cozum_a_i_u():
    for hedef in ([730, 1090, 2440], [270, 2290, 3010], [300, 870, 2240]):
        s = ters_coz(hedef, iterasyon=60)
        assert np.all(np.abs(s.hata_yuzde) < 1.0), (hedef, s.elde)


def test_formant_cikarma_sentetik_kayit():
    a = np.full(36, 3e-4)
    gercek = formantlar(a, 0.17, adet=3)
    y = sesli_harf(a, 0.17, f0=120, sure=2.0)
    olcum = formant_cikar(y, FS, adet=3)
    assert np.all(np.abs(olcum / gercek - 1) < 0.05), (gercek, olcum)


def test_stl_su_gecirmez_ve_baski_tutarli():
    s = ters_coz([730, 1090, 2440], iterasyon=60)
    z, r = baski_profili(s.alanlar, s.uzunluk)
    assert np.all(np.abs(profil_formantlari(z, r, 3) / s.hedef - 1) < 0.02)
    tri = tup_ucgenleri(z, r, dilim=48)
    anahtar = {}
    ids = np.array([anahtar.setdefault(tuple(v), len(anahtar))
                    for v in np.round(tri.reshape(-1, 3), 5)]).reshape(-1, 3)
    kenar = collections.Counter((t[i], t[(i + 1) % 3]) for t in ids for i in range(3))
    assert all(c == 1 and kenar.get((b, a), 0) == 1 for (a, b), c in kenar.items())
    assert isaretli_hacim(tri) > 0


if __name__ == "__main__":
    for ad, fn in list(globals().items()):
        if ad.startswith("test_"):
            fn()
            print("geçti:", ad)
