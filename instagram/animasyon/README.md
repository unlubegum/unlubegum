# Animasyon videosu

- `kimine-gore-ben.mp4` — Instagram Reels için hazır video (1080x1920, 42 sn, müzikli)
- `video.html` — animasyonun kaynağı; tarayıcıda açınca canlı oynar
- `muzik.py` — müzik ve ses efektlerini üretir (`muzik.wav`)
- `render.js` — `video.html`'i kare kare çeker

Yeniden üretmek için:

```bash
python3 muzik.py
mkdir kareler && node render.js kareler
ffmpeg -framerate 30 -i kareler/f%05d.png -i muzik.wav -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a aac -shortest kimine-gore-ben.mp4
```
