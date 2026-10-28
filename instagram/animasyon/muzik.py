"""Video için basit, telifsiz müzik ve efektler üretir -> muzik.wav"""
import wave
import numpy as np

SR = 44100
DUR = 42.0
out = np.zeros(int(SR * DUR))


def add(sig, t):
    i = int(t * SR)
    n = min(len(sig), len(out) - i)
    if n > 0:
        out[i:i + n] += sig[:n]


def env(n, a=0.005, r=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / r)


def note(freq, dur, vol=0.2, r=0.15, kind="pluck"):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == "pluck":
        s = np.sin(2 * np.pi * freq * t) + 0.5 * np.sin(4 * np.pi * freq * t) + 0.25 * np.sin(6 * np.pi * freq * t)
    else:
        s = np.sin(2 * np.pi * freq * t)
    return s * env(n, r=r) * vol


def kick():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    f = 120 * np.exp(-t * 18) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 12) * 0.55


def hat():
    n = int(0.05 * SR)
    return np.random.randn(n) * env(n, a=0.001, r=0.012) * 0.06


def clap():
    n = int(0.15 * SR)
    return np.random.randn(n) * env(n, a=0.001, r=0.04) * 0.18


def whoosh(d=0.35):
    n = int(d * SR)
    t = np.linspace(0, 1, n)
    s = np.random.randn(n)
    s = np.convolve(s, np.ones(20) / 20, mode="same")
    return s * np.sin(np.pi * t) ** 2 * 0.35


def clink(t0):
    for f, v in ((2900, .25), (4350, .15), (6100, .08)):
        add(note(f, 0.6, v, r=0.12, kind="sine"), t0)


m = lambda k: 440 * 2 ** ((k - 69) / 12)
# C - G - Am - F
CHORDS = [(48, [60, 64, 67, 72]), (43, [59, 62, 67, 71]), (45, [60, 64, 69, 72]), (41, [60, 65, 69, 72])]
BEAT = 60 / 124


def music(t_start, t_end, vol=1.0, drums=True):
    t, b = t_start, 0
    while t < t_end:
        bass, arp = CHORDS[(b // 4) % 4]
        add(note(m(bass), BEAT * 0.9, 0.22 * vol, r=0.25, kind="sine"), t)
        for i in range(2):
            add(note(m(arp[(b * 2 + i) % 4]), BEAT / 2, 0.09 * vol, r=0.12), t + i * BEAT / 2)
        if drums:
            add(kick() * vol, t)
            if b % 2 == 1:
                add(clap() * vol, t)
            add(hat() * vol, t + BEAT / 2)
        t += BEAT
        b += 1


# Sahneler 1-5: neşeli müzik
music(0, 24)
for ts in (4.5, 9, 13.5, 18):
    add(whoosh(), ts - 0.15)
# Çekiç: iki "tak", üçüncüsü parmağa "bonk" + boing
def knock(vol):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 900 * t) * 0.6 + np.random.randn(n) * 0.4) * np.exp(-t * 45) * vol


add(knock(0.5), 5.4)
add(knock(0.5), 6.1)
add(knock(0.9), 6.9)
n = int(0.6 * SR)
t = np.arange(n) / SR
add(np.sin(2 * np.pi * np.cumsum(300 + 120 * np.sin(t * 40)) / SR) * np.exp(-t * 5) * 0.3, 6.95)
# Hata sesi (mühendis) ve köpek silkinmesi
for i in range(3):
    add(note(220, 0.12, 0.15, r=0.08, kind="pluck"), 1.9 + i * 0.16)
add(note(m(72), 0.15, 0.12), 3.1)
add(note(m(79), 0.3, 0.12), 3.25)
n = int(0.8 * SR)
add(np.convolve(np.random.randn(n), np.ones(8) / 8, mode="same") * np.abs(np.sin(np.arange(n) / SR * 60)) * 0.25, 11.8)

# Spagetti anı: "dıt dıt dııt" (üzgün trombon)
for i, k in enumerate((67, 66, 65)):
    add(note(m(k), 0.35 if i < 2 else 0.8, 0.14, r=0.3), 21.3 + i * 0.38)

# 24 sn: plak çizilir, müzik durur
n = int(0.5 * SR)
t = np.arange(n) / SR
out[int(24 * SR):] = 0
add(np.sin(2 * np.pi * np.cumsum(900 * np.exp(-t * 6) + 80) / SR) * np.exp(-t * 4) * 0.25 + np.random.randn(n) * 0.03 * np.exp(-t * 5), 23.9)
# Sessizlik ve çay kaşığı
clink(24.9)
clink(25.25)
# Çay yudumu (slurp)
n = int(0.7 * SR)
s = np.convolve(np.random.randn(n), np.ones(40) / 40, mode="same") * np.sin(np.linspace(0, np.pi, n)) * 0.5
add(s, 28.4)
clink(30.0)

# Tanıtım: yumuşak müzik geri gelir
add(whoosh(), 30.85)
music(31, 42, vol=0.75, drums=True)
add(whoosh(0.4), 38.85)

# Son 1.5 sn kısılır
fade = int(1.5 * SR)
out[-fade:] *= np.linspace(1, 0, fade)
out = out / max(1e-9, np.abs(out).max()) * 0.85

with wave.open("muzik.wav", "w") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((out * 32767).astype(np.int16).tobytes())
print("muzik.wav hazır")
