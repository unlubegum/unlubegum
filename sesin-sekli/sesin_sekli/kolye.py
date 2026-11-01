"""Kolye: ses yolunu düz bir madalyonun içine spiral olarak sarar.

Yerleşim (madalyon tablaya yatık basılır, z yukarı):

    üfleme borusu
         │
    ┌────┴────┐                ┌──────────────┐
    │ gırtlak │==== kanal ====►│   spiral     │◄ ip halkası
    └─────────┘  (düz kısım)   │   (içe)  ●───┼── ağız: ön yüzde delik
    balon zarı                 └──────────────┘
    kanal ağzına yaslanır

- Gırtlak: kanalın girişi (glottis) bir "dudak" kenarıyla biter. Etrafındaki
  halka şeklindeki haznenin ağzına balon zarı gerilir; zar bu kenara hafifçe
  yaslanır. Yan borudan üflenince zar kenardan kalkar, hava kanala kaçar,
  basınç düşer, zar geri çarpar: vızıltı. (Dudak-dili / vuvuzela ilkesi.)
- Kanal kesiti damla biçimlidir (tepesi 45°), böylece FDM'de destek gerekmez;
  alan, damla biçimine rağmen akustik modeldeki alana eşit tutulur.
- Akustik uzunluk = düz kısım + spiral + ağız deliği (dikey).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import manifold3d as m3
import numpy as np

KOK2 = np.sqrt(2.0)


@dataclass
class KolyeAyar:
    duvar: float = 1.6          # genel duvar (mm)
    tur_arasi: float = 1.8      # spiral turları arası duvar (mm)
    kenar: float = 2.4          # madalyon dış kenar duvarı (mm)
    hazne_uzunluk: float = 11.0 # gırtlak haznesi (mm)
    hazne_aralik: float = 2.2   # zar altındaki hava halkası kalınlığı (mm)
    dudak_cikinti: float = 0.8  # kanal ağzının hazne kenarından çıkıntısı (mm)
    dilim: int = 40             # kesit çözünürlüğü
    adim: float = 0.6           # yol boyunca örnekleme (mm)


# --- kesit ------------------------------------------------------------------

def _damla_birim(t: float, n: int) -> np.ndarray:
    """r=1 için damla kesiti (u, v), v yukarı. t=0 daire, t=1 45° damla. CCW."""
    H = 1.0 + (KOK2 - 1.0) * t
    phi = np.arccos(1.0 / H)
    a = 2 * np.pi * np.arange(n) / n
    teta = np.pi / 2 - a                       # +v ekseninden ölçülen açı
    teta = (teta + np.pi) % (2 * np.pi) - np.pi
    rho = np.ones(n)
    if phi > 1e-6:
        tp = np.array([np.sin(phi), np.cos(phi)])
        A = np.array([0.0, H])
        d = tp - A
        nrm = np.array([-d[1], d[0]])
        c = nrm @ A
        ic = np.abs(teta) < phi
        yon = np.stack([np.sin(np.abs(teta[ic])), np.cos(teta[ic])], axis=1)
        rho[ic] = c / (yon @ nrm)
    pts = np.stack([rho * np.cos(a), rho * np.sin(a)], axis=1)
    return pts


def _alan(p: np.ndarray) -> float:
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def damla_kesit(r: float, t: float, n: int) -> np.ndarray:
    """Alanı πr² olan damla kesit noktaları."""
    b = _damla_birim(t, n)
    return b * r * np.sqrt(np.pi / _alan(b))


def damla_olcek(t: float, n: int = 64) -> float:
    b = _damla_birim(t, n)
    return float(np.sqrt(np.pi / _alan(b)))


# --- süpürme (sweep) --------------------------------------------------------

def _rmf(P: np.ndarray, T: np.ndarray, v0: np.ndarray):
    """Dönme-minimize çerçeveler (double reflection, Wang 2008)."""
    V = [v0 / np.linalg.norm(v0)]
    for i in range(len(P) - 1):
        v1 = P[i + 1] - P[i]
        c1 = v1 @ v1
        rL = V[i] - (2 / c1) * (v1 @ V[i]) * v1
        tL = T[i] - (2 / c1) * (v1 @ T[i]) * v1
        v2 = T[i + 1] - tL
        c2 = v2 @ v2
        V.append(rL - (2 / c2) * (v2 @ rL) * v2 if c2 > 1e-14 else rL)
    V = np.array(V)
    U = np.cross(V, T)                         # u = v × T  (u × v = T)
    return U, V


def supur(P: np.ndarray, r: np.ndarray, damla: np.ndarray, n: int) -> m3.Manifold:
    """Yol P (K,3) boyunca yarıçap r ve damla oranı ile kapalı katı kanal."""
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    v0 = np.array([0.0, 0.0, 1.0])
    v0 = v0 - (v0 @ T[0]) * T[0]
    if np.linalg.norm(v0) < 1e-6:
        v0 = np.array([1.0, 0.0, 0.0]) - T[0, 0] * T[0]
    U, V = _rmf(P, T, v0)
    K = len(P)
    halkalar = []
    for k in range(K):
        q = damla_kesit(r[k], damla[k], n)
        halkalar.append(P[k] + q[:, :1] * U[k] + q[:, 1:] * V[k])
    verts = np.concatenate(halkalar + [P[:1], P[-1:]])
    c0, c1 = K * n, K * n + 1
    tri = []
    j = np.arange(n)
    jn = (j + 1) % n
    for k in range(K - 1):
        a, b = k * n + j, k * n + jn
        c, d = (k + 1) * n + jn, (k + 1) * n + j
        tri.append(np.stack([a, b, c], 1))
        tri.append(np.stack([a, c, d], 1))
    tri.append(np.stack([np.full(n, c0), jn, j], 1))                       # başlangıç kapağı (-T)
    tri.append(np.stack([np.full(n, c1), (K - 1) * n + j, (K - 1) * n + jn], 1))  # bitiş (+T)
    mesh = m3.Mesh(vert_properties=verts.astype(np.float32),
                   tri_verts=np.concatenate(tri).astype(np.uint32))
    s = m3.Manifold(mesh)
    if s.is_empty():
        raise RuntimeError(f"kanal katısı oluşturulamadı: {s.status()}")
    return s


# --- yerleşim ---------------------------------------------------------------

def _hizala(solid: m3.Manifold, merkez, yon) -> m3.Manifold:
    """+z eksenli katıyı yon eksenine çevirip merkeze taşır."""
    z = np.array([0.0, 0.0, 1.0])
    yon = np.asarray(yon, float) / np.linalg.norm(yon)
    ax = np.cross(z, yon)
    s = np.linalg.norm(ax)
    c = z @ yon
    if s < 1e-9:
        R = np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    else:
        k = ax / s
        Kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
        R = np.eye(3) + s * Kx + (1 - c) * Kx @ Kx
    M = np.concatenate([R, np.asarray(merkez, float).reshape(3, 1)], axis=1)
    return solid.transform(M.tolist())


def _silindir(r, h, yon, bas, n=48, r_ust=None):
    c = m3.Manifold.cylinder(h, r, r if r_ust is None else r_ust, n)
    return _hizala(c, bas, yon)


def _spiral(rho0, rho_e, b, adim):
    """İçe doğru saat yönü Arşimet spirali; başlangıç tepede (θ=π/2)."""
    tau_son = (rho0 - rho_e) / b
    tau = np.linspace(0, tau_son, max(50, int(tau_son * rho0 / adim * 2)))
    rho = rho0 - b * tau
    th = np.pi / 2 - tau
    return np.stack([rho * np.cos(th), rho * np.sin(th)], axis=1)


def _uzunluk(p):
    return float(np.sum(np.linalg.norm(np.diff(p, axis=0), axis=1)))


def _yeniden_ornekle(p, adim):
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
    yeni = np.linspace(0, s[-1], max(3, int(np.ceil(s[-1] / adim)) + 1))
    return np.stack([np.interp(yeni, s, p[:, i]) for i in range(p.shape[1])], axis=1), yeni


def kolye_yap(z_mm: np.ndarray, r_mm: np.ndarray, ayar: KolyeAyar | None = None):
    """Akustik profil (z: yol boyu mm, r: iç yarıçap mm) → (kolye Manifold, bilgi dict)."""
    a = ayar or KolyeAyar()
    L = float(z_mm[-1])
    r_of = lambda s: np.interp(s, z_mm, r_mm)
    k_damla = damla_olcek(1.0)                 # damla genişlik ölçeği (≈0.97)
    r_max = float(r_mm.max())
    yari_gen = r_max * k_damla                 # yatay yarı genişlik
    tepe = r_max * k_damla * KOK2              # merkezden damla tepesine

    r_n = float(r_mm[0])                       # boyun (glottis) yarıçapı
    tup_dis = r_n * k_damla * KOK2 + 1.2       # kanal ağzı dudağının dış yarıçapı
    hazne_ic = tup_dis + a.hazne_aralik
    hazne_dis = hazne_ic + a.duvar

    z_c = max(a.duvar + yari_gen, hazne_dis)   # kanal merkezinin tabladan yüksekliği
    kalinlik = z_c + tepe + a.duvar
    h_agiz = kalinlik - z_c                    # dikey ağız deliği uzunluğu

    hatve = 2 * yari_gen + a.tur_arasi
    b = hatve / (2 * np.pi)
    rho_e = yari_gen + 3.5

    # düz kısım = dudak çıkıntısı + hazne + bağlantı + madalyon kenarına mesafe
    s_duz = a.dudak_cikinti + a.hazne_uzunluk + 4.0 + 20.0
    for _ in range(30):
        S_sp = L - s_duz - h_agiz
        if S_sp < 30:
            raise ValueError(f"Ses yolu kolye için çok kısa ({L:.0f} mm).")
        lo, hi = rho_e + 1, rho_e + 200
        for _ in range(50):
            mid = (lo + hi) / 2
            if _uzunluk(_spiral(mid, rho_e, b, a.adim)) < S_sp:
                lo = mid
            else:
                hi = mid
        rho0 = (lo + hi) / 2
        R = rho0 + yari_gen + a.kenar
        kenar_mesafe = np.sqrt(max(R**2 - rho0**2, 0.0))
        yeni = a.dudak_cikinti + a.hazne_uzunluk + 4.0 + kenar_mesafe
        if abs(yeni - s_duz) < 0.05:
            break
        s_duz = yeni

    sp = _spiral(rho0, rho_e, b, a.adim)
    S = sp[0]
    d = np.array([rho0, -b]) / np.hypot(rho0, b)        # başlangıç teğeti
    G = S - d * s_duz                                    # glottis (kanal ağzı)
    duz = G + np.outer(np.linspace(0, 1, 60), S - G)
    yatay2, s_yatay = _yeniden_ornekle(np.concatenate([duz, sp[1:]]), a.adim)
    P = np.c_[yatay2, np.full(len(yatay2), z_c)]
    E = P[-1]

    kanal_yatay = supur(P, r_of(s_yatay), np.ones(len(P)), a.dilim)
    s_d = np.linspace(s_yatay[-1], L, max(3, int(h_agiz / a.adim) + 1))
    Pd = np.c_[np.repeat(E[None, :2], len(s_d), 0), z_c + (s_d - s_d[0])]
    Pd[-1, 2] += 0.6                                     # yüzeyi temiz delsin
    kanal_dikey = supur(Pd, r_of(s_d), np.zeros(len(Pd)), a.dilim)
    dirsek = m3.Manifold.sphere(float(r_of(s_yatay[-1]) * k_damla), a.dilim).translate(E.tolist())

    # --- gövde ---
    govde = m3.Manifold.cylinder(kalinlik, R, R, 160)
    d3 = np.array([d[0], d[1], 0.0])
    G3 = np.array([G[0], G[1], z_c])
    hazne_bas = G3 + d3 * a.dudak_cikinti
    hazne_son = hazne_bas + d3 * a.hazne_uzunluk
    govde += _silindir(hazne_dis, a.hazne_uzunluk, d3, hazne_bas)
    # hazneden madalyona sap
    sap_r = max(tepe, r_n * k_damla * KOK2) + a.duvar
    govde += _silindir(min(sap_r, hazne_dis), s_duz - a.dudak_cikinti - a.hazne_uzunluk + 2,
                       d3, hazne_son - d3 * 0.5)
    # kanal ağzı dudağı (zarın yaslandığı çıkıntı)
    govde += _silindir(tup_dis, a.dudak_cikinti + 0.5, d3, G3)
    # zarı bağlamak için hazne dışında oluk bırakılacak; üfleme borusu
    yan = np.cross(np.array([0, 0, 1.0]), d3)
    if yan @ np.array([G[0], G[1], 0]) < 0:
        yan = -yan                                       # madalyondan dışa baksın
    port_merkez = hazne_bas + d3 * (a.hazne_uzunluk * 0.55)
    port_dis, port_ic, port_boy = 3.6, 2.1, 14.0
    govde += _silindir(port_dis, port_boy, yan, port_merkez)
    # ip halkası (madalyonun tepesinde, ağızlığın karşı tarafına yakın)
    aci = np.radians(60.0)
    hm = np.array([np.cos(aci), np.sin(aci), 0.0]) * (R + 2.5)
    halka = (m3.Manifold.cylinder(4.0, 5.0, 5.0, 48) - m3.Manifold.cylinder(4.0, 2.5, 2.5, 48)
             ).translate(hm.tolist())
    govde += halka

    # --- boşluklar ---
    bosluk = kanal_yatay + kanal_dikey + dirsek
    # hava halkası: zarın altındaki halka hazne (ağzı açık)
    halka_bos = (_silindir(hazne_ic, a.hazne_uzunluk - a.duvar + 0.01, d3, hazne_bas - d3 * 0.01)
                 - _silindir(tup_dis, a.hazne_uzunluk + 1, d3, hazne_bas - d3 * 0.5))
    bosluk += halka_bos
    # üfleme borusu deliği (yalnızca hava halkasına kadar)
    bosluk += _silindir(port_ic, port_boy - (hazne_ic - 0.6) + 0.5, yan,
                        port_merkez + yan * (hazne_ic - 0.6))
    # zarı bağlamak için oluk (hazne dışında, ağza yakın)
    oluk_r = hazne_dis - 0.7
    bosluk += (_silindir(hazne_dis + 2, 1.4, d3, hazne_bas + d3 * 2.0)
               - _silindir(oluk_r, 1.6, d3, hazne_bas + d3 * 1.9))
    # kanal ağzını temiz aç
    bosluk += _silindir(r_n, 2.0, d3, G3 - d3 * 1.5)

    kolye = govde - bosluk
    kolye = kolye.trim_by_plane([0.0, 0.0, 1.0], 0.0)    # tabla altını kes

    bilgi = {
        "madalyon_cap_mm": round(2 * R, 1),
        "kalinlik_mm": round(kalinlik, 1),
        "spiral_tur": round((rho0 - rho_e) / hatve, 2),
        "duz_kisim_mm": round(s_duz, 1),
        "spiral_mm": round(_uzunluk(sp), 1),
        "agiz_deligi_mm": round(h_agiz, 1),
        "kanal_agzi_cap_mm": round(2 * r_n, 1),
        "hazne_dis_cap_mm": round(2 * hazne_dis, 1),
        "ayar": asdict(a),
    }
    return kolye, bilgi


def manifold_stl_yaz(yol: str, solid: m3.Manifold) -> np.ndarray:
    from .geometri import stl_yaz
    mesh = solid.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    t = np.asarray(mesh.tri_verts)
    tri = v[t].astype(np.float64)
    stl_yaz(yol, tri, baslik="sesin-sekli kolye")
    return tri
