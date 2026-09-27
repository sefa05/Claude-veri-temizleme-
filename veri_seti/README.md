# Kirli E-Ticaret Veri Seti: Sen de Dene

10.000 sipariş, 2.639 müşteri satırı ve 300 ürünlük, bilerek bozulmuş sentetik bir Türk e-ticaret veri seti. Her
bozuk hücrenin doğru değeri biliniyor, böylece temizleme yönteminin gerçekte ne kadar iyi çalıştığını
**sayıyla** görebilirsin. Kural, pandas, LLM, ajan ya da elle: hangi yöntemi istersen kullan.

## Dosyalar

```
kirli/     musteriler.csv, urunler.csv, siparisler.csv    <- temizleyeceğin veri
gercek/    temiz veri + bozma_kaydi.csv                   <- cevap anahtarı, temizlerken bakma
```

`gercek/` klasörü yalnızca puanlama içindir. İçine bakarak temizlersen skorun bir şey ifade etmez.

## Görev

Üç tabloyu temizle ve aynı sütunlarla bir klasöre yaz:

| Tip | Beklenen biçim | Örnek |
|---|---|---|
| Tarih | `YYYY-AA-GG` | `2024-03-05` |
| Para, oran | nokta ondalıklı sayı | `1250.50`, `0.10` |
| Adet | tam sayı | `3` |
| Telefon | `+90 5XX XXX XX XX` | `+90 532 123 45 67` |
| ID | önek + sıfır dolgulu sayı | `M00042`, `U0007`, `S000123` |
| İl, ilçe, ad | resmi Türkçe yazım | `İstanbul`, `Şişli`, `Ayşe` |
| Seçenekli sütunlar | sabit listeden biri | `Trendyol Express`, `Dijital Cüzdan`, `Teslim Edildi` |
| Bilinmeyen değer | boş hücre | |

Seçenek listeleri ve iş kuralları (veri 2025-01-01'de çekildi, teslim en fazla 30 gün sürer, toplam = adet × fiyat
× (1 − indirim)) `veri_temizleme/referans.py` ve ana README'de.

Aynı müşterinin tekrarlanan kayıtlarını birleştirirsen, küçük ID'yi koru, birleştirdiklerini
`musteri_eslesme.csv` dosyasına `eski_id,yeni_id` olarak yaz ve siparişlerdeki `musteri_id`'yi yeni ID'ye çevir.

## Puanlama

```bash
pip install -e .
veri-temizle puanla benim_ciktim/
```

Çıktı: genel doğru düzeltme oranı, uydurma sayısı (bilinmeyen bir değere yanlış değer yazmak), temiz hücreyi bozma
oranı, müşteri eşleştirme F1 ve 15 bozma türünün her biri için ayrı skor.

## Referans skor: sadece kurallar, LLM yok

| Metrik | Skor |
|---|---|
| Genel doğru düzeltme | %97,6 |
| Uydurma | 11 / 1.617 |
| Müşteri eşleştirme F1 | 0,990 |
| En zayıf tür | Yazım tutarsızlığı (%89,5): `TEX`, `Papara`, `Tamamlandı` |

Bu skor avantajlı: kuralları, bozmaları da yazan kişi yazdı. Onu geçen bir yöntemin var mı?

Veri tamamen sentetiktir, gerçek kişilere ait değildir. Aynı veriyi `veri-temizle uret --seed 42` ile yeniden
üretebilirsin. Farklı bir seed ile yeni bir test seti oluşturabilirsin.
