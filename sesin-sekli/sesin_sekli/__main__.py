"""Sesin Şekli: ses kaydından 3D baskı ses yolu.

Kullanım:
  python3 -m sesin_sekli tasarla --wav kayit.wav -o cikti/
  python3 -m sesin_sekli tasarla --unlu a -o cikti_a/
  python3 -m sesin_sekli tasarla --wav kayit.wav --kolye -o kolye/   (madalyon + gırtlak)
  python3 -m sesin_sekli tasarla --formant 730,1090,2440 -o cikti/
  python3 -m sesin_sekli olc --wav baski_kaydi.wav --tasarim cikti/
  python3 -m sesin_sekli vizilti -o vizilti.wav
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

from .formant import formant_cikar, wav_oku
from .geometri import (baski_profili, en_buyuk_sarkma_derece, isaretli_hacim,
                       profil_formantlari, profil_svg, stl_yaz, tup_ucgenleri)
from .sentez import sesli_harf, vizilti, wav_yaz
from .ters_cozum import KOLYE_CAP_MM, ters_coz

# Yaklaşık yetişkin erkek ortalamaları (F1, F2, F3) Hz. Gerçek kişi için --wav kullanın.
UNLULER = {
    "a": (730, 1090, 2440), "e": (530, 1840, 2480), "ı": (360, 1450, 2400),
    "i": (270, 2290, 3010), "o": (570, 840, 2410), "ö": (430, 1450, 2300),
    "u": (300, 870, 2240), "ü": (300, 1650, 2200),
}


def _tablo(basliklar, satirlar):
    print("  ".join(f"{b:>10}" for b in basliklar))
    for s in satirlar:
        print("  ".join(f"{v:>10}" for v in s))


def tasarla(a):
    if a.wav:
        x, fs = wav_oku(a.wav)
        hedef = formant_cikar(x, fs, adet=a.formant_sayisi)
        kaynak = os.path.basename(a.wav)
    elif a.formant:
        hedef = np.array([float(v) for v in a.formant.split(",")])
        kaynak = "elle girilen formantlar"
    else:
        hedef = np.array(UNLULER[a.unlu], dtype=float)
        kaynak = f"/{a.unlu}/ (ortalama değerler)"

    print(f"Hedef formantlar ({kaynak}): {np.round(hedef).astype(int).tolist()} Hz")
    print("Şekil aranıyor (≈30-60 sn)...")
    if a.kolye:
        # kolyede kanal dar tutulur; gırtlak ağzı 6 mm
        s = ters_coz(hedef, boyun_mm=a.boyun_mm, boyun_cap_mm=6.0, tohum=a.tohum, cap_mm=KOLYE_CAP_MM)
    else:
        s = ters_coz(hedef, boyun_mm=a.boyun_mm, boyun_cap_mm=a.boyun_cap_mm, tohum=a.tohum)

    z, r = baski_profili(s.alanlar, s.uzunluk)
    baski_f = profil_formantlari(z, r, adet=len(hedef))
    tri = tup_ucgenleri(z, r, duvar_mm=a.duvar_mm)

    os.makedirs(a.cikti, exist_ok=True)
    yol = lambda ad: os.path.join(a.cikti, ad)
    stl_yaz(yol("ses_yolu.stl"), tri)
    profil_svg(yol("profil.svg"), z, r, a.duvar_mm, baslik=f"Sesin Şekli · {kaynak}")
    np.savetxt(yol("profil.csv"), np.c_[z, r], delimiter=",", header="z_mm,ic_yaricap_mm", comments="")
    wav_yaz(yol("onizleme.wav"), sesli_harf(s.alanlar, s.uzunluk, f0=a.f0))

    rapor = {
        "kaynak": kaynak,
        "hedef_hz": hedef.round(1).tolist(),
        "model_hz": s.elde.round(1).tolist(),
        "baski_profili_hz": baski_f.round(1).tolist(),
        "uzunluk_mm": round(s.uzunluk * 1000, 1),
        "dis_cap_mm": round(2 * (float(r.max()) + a.duvar_mm), 1),
        "en_dar_kanal_cap_mm": round(2 * float(r.min()), 1),
        "boyun": {"uzunluk_mm": a.boyun_mm, "ic_cap_mm": 6.0 if a.kolye else a.boyun_cap_mm},
        "duvar_mm": a.duvar_mm,
        "malzeme_hacmi_cm3": round(isaretli_hacim(tri) / 1000, 1),
        "en_buyuk_ic_sarkma_derece": round(en_buyuk_sarkma_derece(z, r), 1),
    }
    if a.kolye:
        rapor["kolye"] = _kolye_yaz(yol("kolye.stl"), z, r)
    with open(yol("rapor.json"), "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)

    print()
    _tablo(["", "hedef", "model", "baskı", "hata %"],
           [[f"F{i + 1}", round(h), round(m), round(b), f"{100 * (b - h) / h:+.1f}"]
            for i, (h, m, b) in enumerate(zip(hedef, s.elde, baski_f))])
    print(f"\nUzunluk {rapor['uzunluk_mm']} mm · dış çap {rapor['dis_cap_mm']} mm · "
          f"en dar kanal {rapor['en_dar_kanal_cap_mm']} mm · ~{rapor['malzeme_hacmi_cm3']} cm³ filament")
    sarkma = rapor["en_buyuk_ic_sarkma_derece"]
    print(f"İç kanal en dik sarkma: {sarkma}° " + ("(destek gerekmez)" if sarkma <= 45 else
          "(UYARI: 45° üstü; reçine veya ikiye bölerek basın)"))
    if a.kolye:
        k = rapor["kolye"]
        print(f"Kolye: çap {k['madalyon_cap_mm']} mm · kalınlık {k['kalinlik_mm']} mm · "
              f"{k['spiral_tur']} tur spiral · gırtlak haznesi Ø{k['hazne_dis_cap_mm']} mm")
    dosyalar = "kolye.stl, " if a.kolye else ""
    print(f"Çıktılar: {a.cikti}/  ({dosyalar}ses_yolu.stl, onizleme.wav, profil.svg, profil.csv, rapor.json)")


def _kolye_yaz(yol, z, r):
    from .kolye import kolye_yap, manifold_stl_yaz
    kolye, bilgi = kolye_yap(z, r)
    manifold_stl_yaz(yol, kolye)
    bilgi["malzeme_hacmi_cm3"] = round(kolye.volume() / 1000, 1)
    return {k: (float(v) if isinstance(v, np.floating) else v) for k, v in bilgi.items()}


def olc(a):
    with open(os.path.join(a.tasarim, "rapor.json"), encoding="utf-8") as f:
        rapor = json.load(f)
    hedef = np.array(rapor["hedef_hz"])
    x, fs = wav_oku(a.wav)
    olculen = formant_cikar(x, fs, adet=len(hedef))
    oran = olculen / hedef
    _tablo(["", "hedef", "ölçülen", "fark %"],
           [[f"F{i + 1}", round(h), round(o), f"{100 * (o / h - 1):+.1f}"]
            for i, (h, o) in enumerate(zip(hedef, olculen))])
    # Tüm formantlar ~1/L ile ölçeklenir: ortak sapmayı uzunlukla düzelt (F1-F2 ağırlıklı)
    ortak = float(np.average(oran, weights=[1, 1, 0.5, 0.25][: len(oran)]))
    print(f"\nOrtak sapma: {100 * (ortak - 1):+.1f} %")
    if abs(ortak - 1) < 0.02:
        print("Baskı hedefe yeterince yakın (±%2).")
        return
    data = np.loadtxt(os.path.join(a.tasarim, "profil.csv"), delimiter=",", skiprows=1)
    z, r = data[:, 0] * ortak, data[:, 1]
    yeni = os.path.join(a.tasarim, "ses_yolu_duzeltilmis.stl")
    stl_yaz(yeni, tup_ucgenleri(z, r, duvar_mm=rapor["duvar_mm"]))
    print(f"Uzunluğu {z[-1]:.1f} mm yapan düzeltilmiş model: {yeni}")
    if "kolye" in rapor:
        yeni_k = os.path.join(a.tasarim, "kolye_duzeltilmis.stl")
        _kolye_yaz(yeni_k, z, r)
        print(f"Düzeltilmiş kolye: {yeni_k}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="sesin_sekli", description="Ses kaydından 3D baskı ses yolu")
    alt = p.add_subparsers(dest="komut", required=True)

    t = alt.add_parser("tasarla", help="sesten/formantlardan STL üret")
    g = t.add_mutually_exclusive_group(required=True)
    g.add_argument("--wav", help="2-3 sn sabit sesli harf kaydı (wav)")
    g.add_argument("--formant", help="virgülle F1,F2,F3[,F4] Hz")
    g.add_argument("--unlu", choices=sorted(UNLULER), help="ortalama değerlerle hazır ünlü")
    t.add_argument("-o", "--cikti", default="cikti")
    t.add_argument("--formant-sayisi", type=int, default=3, choices=[2, 3, 4])
    t.add_argument("--duvar-mm", type=float, default=2.4)
    t.add_argument("--boyun-mm", type=float, default=12.0, help="kaynak takılan giriş uzunluğu")
    t.add_argument("--boyun-cap-mm", type=float, default=9.0, help="giriş iç çapı")
    t.add_argument("--f0", type=float, default=120.0, help="önizleme perdesi (Hz)")
    t.add_argument("--tohum", type=int, default=0)
    t.add_argument("--kolye", action="store_true",
                   help="kanalı madalyona spiral sar, gırtlak (balon zarlı) ağızlık ekle")
    t.set_defaults(fn=tasarla)

    o = alt.add_parser("olc", help="basılan tüpün kaydını hedefle karşılaştır, gerekirse düzelt")
    o.add_argument("--wav", required=True)
    o.add_argument("--tasarim", required=True, help="tasarla çıktı klasörü")
    o.set_defaults(fn=olc)

    v = alt.add_parser("vizilti", help="hoparlörle deneme için kaynak sinyali üret")
    v.add_argument("-o", "--cikti", default="vizilti.wav")
    v.add_argument("--f0", type=float, default=120.0)
    v.set_defaults(fn=lambda a: (wav_yaz(a.cikti, vizilti(a.f0)), print(f"Yazıldı: {a.cikti}")))

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
