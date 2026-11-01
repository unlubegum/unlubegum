"""Ses kaydından formant çıkarma (LPC, yalnızca numpy/scipy)."""
from __future__ import annotations

import numpy as np
from scipy.io import wavfile
from scipy.linalg import solve_toeplitz
from scipy.signal import resample_poly

HEDEF_FS = 10000  # 5 kHz'e kadar formant için yeterli


def wav_oku(yol: str) -> tuple[np.ndarray, int]:
    fs, x = wavfile.read(yol)
    x = x.astype(float)
    if x.ndim > 1:
        x = x.mean(axis=1)
    x = x / (np.abs(x).max() + 1e-12)
    return x, int(fs)


def _lpc(cerceve: np.ndarray, derece: int) -> np.ndarray:
    r = np.correlate(cerceve, cerceve, mode="full")[len(cerceve) - 1:]
    if r[0] <= 0:
        return None
    r[0] *= 1.0 + 1e-9
    a = solve_toeplitz(r[:derece], r[1:derece + 1])
    return np.concatenate(([1.0], -a))


def formant_cikar(x: np.ndarray, fs: int, adet: int = 4, derece: int = 12) -> np.ndarray:
    """Sesli harfin sabit orta kısmından medyan formantları döndürür (Hz)."""
    x = resample_poly(x, HEDEF_FS, fs)
    fs = HEDEF_FS
    # Sessiz baş/son kısımları at: enerjisi yüksek orta %60
    n = len(x)
    x = x[int(n * 0.2): int(n * 0.8)]
    x = np.append(x[0], x[1:] - 0.97 * x[:-1])  # ön vurgu

    cer = int(0.03 * fs)
    adim = int(0.01 * fs)
    pencere = np.hamming(cer)
    enerji_esik = 0.1 * np.max([np.sum(x[i:i + cer] ** 2) for i in range(0, len(x) - cer, adim)] or [0])

    hepsi = []
    for i in range(0, len(x) - cer, adim):
        c = x[i:i + cer]
        if np.sum(c**2) < enerji_esik:
            continue
        a = _lpc(c * pencere, derece)
        if a is None:
            continue
        kokler = np.roots(a)
        kokler = kokler[np.imag(kokler) > 0]
        frek = np.angle(kokler) * fs / (2 * np.pi)
        bant = -fs / np.pi * np.log(np.abs(kokler))
        secim = np.sort(frek[(frek > 150) & (bant < 500)])
        if len(secim) >= adet:
            hepsi.append(secim[:adet])
    if not hepsi:
        raise ValueError("Kayıtta formant bulunamadı: uzun, sabit bir sesli harf kaydedin (2-3 sn).")
    return np.median(np.array(hepsi), axis=0)
