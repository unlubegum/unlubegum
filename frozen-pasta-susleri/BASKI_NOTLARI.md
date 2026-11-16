# Frozen pasta süsleri – renk atamalı, sadeleştirilmiş sürüm

Her 3MF dosyası **tek nesne + ayrı parçalar** içerir ve her parçaya **filament (slot) numarası önceden atanmıştır**.
Görsel rehber: `RENK_REHBERI.png`

## Renk tablosu (Slot = AMS yuvası / filament numarası)

| Model | Slot 1 | Slot 2 | Slot 3 | Slot 4 |
|---|---|---|---|---|
| 01_Elsa_HappyBirthday | Beyaz | Turkuaz | Ten-Bej | Lacivert |
| 02_Buz_Sato | Beyaz | Buz Mavisi | Turkuaz | Lacivert |
| 03_Elsa | Beyaz | Buz Mavisi | Turkuaz | Lacivert |
| 04_Anna | Beyaz | Bordo | Mavi | Siyah |
| 05_Olaf | Beyaz | Siyah | Turuncu | Koyu Kahve |
| 06_Kristoff_Sven | Beyaz | Koyu Gri | Kahverengi | Ten-Bej |
| 07–12_Kar_Tanesi | Beyaz | Buz Mavisi | Lila | – |

Toplam lazım olan filamentler: Beyaz, Buz Mavisi (açık mavi), Turkuaz, Lacivert, Ten/Bej, Bordo, Mavi, Siyah,
Turuncu, Koyu Kahve, Kahverengi, Koyu Gri, Lila. Bire bir aynı tonu bulmak gerekmez, en yakın renk yeterli.

## Slicer'da açma
1. Bambu Studio / OrcaSlicer / PrusaSlicer → Dosya → İçe aktar (veya sürükle-bırak).
2. Soldaki listede nesnenin altında parçalar görünür: `F1_Govde_Beyaz`, `F2_...` – her biri doğru slota atanmış gelir.
3. Sağ üstteki filament listesinde Slot 1–4 renklerini tablodaki gibi ayarla (AMS'e o sırayla tak).
4. Dilimle ve bas. Aynı tabaka üzerine aynı slot düzenine sahip modelleri birlikte koyabilirsin
   (ör. 02_Buz_Sato + 03_Elsa aynı renkleri kullanır; tüm kar taneleri birlikte).

## Yapı
- Arka tamamen düz; tablaya yüzüstü yatar, destek gerekmez.
- Gövde 2.4 mm beyaz; renkler üstte 0.4 / 0.6 / 0.8 mm kabartma (koyu renk daha yüksek).
- 0.8 mm²'den küçük renk adacıkları komşu renge katıldı → daha az renk değişimi, daha hızlı ve temiz baskı.
- Altta 6 mm genişliğinde, 40 mm uzunluğunda sivri çubuk – pastaya dik saplanır.

## Önerilen ayarlar
0.4 mm nozul, 0.16 mm katman, 3–4 duvar, %20+ dolgu, PLA. Çubuğa pastaya koymadan önce pipet/streç film geçir.
