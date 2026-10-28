# ⚽ Pasta Süsü Futbol Topu

![önizleme](onizleme.png)

Siyah-beyaz klasik futbol topu: 12 siyah beşgen, 20 beyaz altıgen, aralarında dikiş oyukları.
Alt kısmı düz kesik; destek gerekmeden basılır ve pastada devrilmez. Altta çubuk ya da kürdan için 4,2 mm delik var.

| Boy | Çap | Yükseklik | Adet |
|---|---|---|---|
| Büyük | 50 mm | 42,5 mm | 3 |
| Orta | 35 mm | 30 mm | 2 |

## Dosyalar (`stl/`)

| Dosya | Ne zaman |
|---|---|
| `top-50mm-iki-renk.3mf`, `top-35mm-iki-renk.3mf` | **Çok renkli yazıcı** (AMS/MMU): siyah ve beyaz parçalar tek nesne olarak gelir, parçalara renk ata |
| `top-XXmm-beyaz.stl` + `top-XXmm-siyah.stl` | Aynısı, ayrı STL olarak (ikisini birlikte "tek nesne, çok parça" diye içe aktar) |
| `top-XXmm-tek-renk.stl` | **Tek renkli yazıcı**: beyaz bas, beşgenleri siyah akrilik boya/kalemle boya. Oyuklar boyama sınırı olur |

## Snapmaker U1 ile baskı

1. **Snapmaker Orca**'da `stl/tabla-3-buyuk-2-orta-iki-renk.3mf` dosyasını aç. "Tek nesne, çok parça olarak yüklensin mi?" diye sorarsa **Evet** de.
2. Kafa 1'e **beyaz**, kafa 2'ye **siyah** PLA tak; Orca'da filamentleri eşleştir.
3. Sol paneldeki nesne listesinde `beyaz` parçaya 1. filamenti, `siyah` parçaya 2. filamenti ata.
4. Doluluk %5–10, destek kapalı, katman 0,16 mm → Dilimle → Yazdır.

## Önerilen dilimleyici ayarları

- Katman: 0,16 mm (yuvarlaklık için), duvar: 3
- Doluluk: **%5–10** (içinin dolu olmasına gerek yok)
- Destek: **kapalı**; alt düz yüzey tablaya oturur
- Tek renkli baskıda: dilimleyicide 3 büyük + 2 orta kopya ekle, hepsini tek seferde bas

## Gıda güvenliği

PLA gıdaya temas için onaylı değildir. Topları doğrudan kremaya değil, şeker hamuru üstüne ya da altına
streç film/kürdan kullanarak koyun.

## Yeniden üretmek

```bash
pip install trimesh manifold3d networkx lxml scipy
python3 futbol_topu.py   # stl/ klasörünü üretir
python3 onizleme.py      # onizleme.png
```
