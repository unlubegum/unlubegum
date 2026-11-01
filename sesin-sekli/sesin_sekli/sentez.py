"""Basmadan önce dinleme: glottal darbe dizisini tüp transfer fonksiyonundan geçirir."""
from __future__ import annotations

import numpy as np
from scipy.io import wavfile

from .akustik import transfer

FS = 16000


def glottal_dizi(f0: float = 120.0, sure: float = 2.0, fs: int = FS, tohum: int = 0) -> np.ndarray:
    """Rosenberg glottal darbeleri; hafif vibrato ve jitter ile doğal tını."""
    rng = np.random.default_rng(tohum)
    n = int(sure * fs)
    x = np.zeros(n)
    t = 0.0
    while t < sure - 0.05:
        f = f0 * (1 + 0.02 * np.sin(2 * np.pi * 5 * t)) * (1 + 0.005 * rng.standard_normal())
        T = 1.0 / f
        tp, tn = 0.4 * T, 0.16 * T
        i0 = int(t * fs)
        k = np.arange(int((tp + tn) * fs))
        tk = k / fs
        g = np.where(tk < tp, 0.5 * (1 - np.cos(np.pi * tk / tp)), np.cos(np.pi * (tk - tp) / (2 * tn)))
        son = min(n, i0 + len(g))
        x[i0:son] += g[: son - i0]
        t += T
    x -= x.mean()
    return x


def _normalize(y):
    kenar = int(0.02 * FS)
    zarf = np.ones_like(y)
    zarf[:kenar] = np.linspace(0, 1, kenar)
    zarf[-kenar:] = np.linspace(1, 0, kenar)
    y = y * zarf
    return y / (np.abs(y).max() + 1e-12) * 0.9


def sesli_harf(alanlar, uzunluk, f0=120.0, sure=2.0) -> np.ndarray:
    u = glottal_dizi(f0, sure)
    U = np.fft.rfft(u)
    f = np.fft.rfftfreq(len(u), 1 / FS)
    f[0] = 1.0
    H = transfer(alanlar, uzunluk, f)
    Y = U * H * (1j * f)  # dudak radyasyonu ≈ türev
    Y[0] = 0
    return _normalize(np.fft.irfft(Y, n=len(u)))


def wav_yaz(yol: str, y: np.ndarray, fs: int = FS) -> None:
    wavfile.write(yol, fs, (np.clip(y, -1, 1) * 32767).astype(np.int16))


def vizilti(f0=120.0, sure=4.0) -> np.ndarray:
    """Basılan tüpü telefon hoparlörüyle denemek için ham kaynak sinyali."""
    return _normalize(np.diff(glottal_dizi(f0, sure), prepend=0))
