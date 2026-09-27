# Veri Temizleme Projesi: Kirli E-Ticaret Verisinden Temiz Çıktıya

Dağınık, bozuk ve işe yaramaz haldeki e-ticaret verisini adım adım temizleyip analize hazır bir çıktıya dönüştüren
bir Python projesi. Veriyi kendimiz **sentetik** olarak üretiriz. Üretici önce temiz veriyi (gerçek doğru) oluşturur,
sonra bilerek bozar. Temizleme hattının başarısı, temiz sonucun bu gerçek doğruyla karşılaştırılmasıyla **sayısal
olarak** ölçülür.

## Kararlar

| Konu | Karar |
|---|---|
| Senaryo | Türk bir e-ticaret sitesinin müşteri, ürün ve sipariş kayıtları |
| Ölçek | **10.000 sipariş satırı** (ek olarak ~2.500 müşteri, ~300 ürün) |
| Dil | Türkçe: veri, sütun adları, rapor ve CLI mesajları |
| Teknoloji | Python 3.11, pandas, pytest |
| Arayüz | Komut satırı (CLI) + tek dosyalık HTML temizlik raporu (sonra değiştirilebilir) |
| Tekrarlanabilirlik | Sabit `seed`. Aynı seed her seferinde birebir aynı kirli veriyi üretir |

## Genel akış

```
[1. Üretici]                    [2. Temizleme hattı]                  [3. Çıktılar]
temiz veri (gerçek doğru) ─┐
                           ├─► kirli CSV'ler ─► oku → onar → standartlaştır ─► temiz CSV / Excel
bozma kuralları ───────────┘                   → doğrula → tekrarları birleştir   temizlik raporu (HTML)
                                                                                  doğruluk skoru
                                                    gerçek doğru ile karşılaştır ◄┘
```

## 1. Sentetik veri üretici

### Tablolar (temiz hal)

**musteriler**: `musteri_id, ad, soyad, eposta, telefon, dogum_tarihi, cinsiyet, il, ilce, kayit_tarihi`

**urunler**: `urun_id, urun_adi, kategori, marka, birim_fiyat`

**siparisler**: `siparis_id, musteri_id, urun_id, siparis_tarihi, adet, birim_fiyat, indirim_orani, toplam_tutar,
odeme_yontemi, kargo_firmasi, teslim_tarihi, durum`

Temiz veri gerçekçi dağılımlara uyar: Türk ad-soyad listeleri, gerçek il ve ilçe adları, kategoriye göre makul fiyat
aralıkları, hafta sonu ve Kasım (indirim dönemi) yoğunluğu, `teslim_tarihi > siparis_tarihi` gibi kurallar.

### Bozma kataloğu

Her bozma türünün bir **oranı** vardır (ör. `%8`) ve oranlar tek bir ayar dosyasından (`config.yaml`) değiştirilebilir.
Üretici hangi hücreye ne yaptığını `bozma_kaydi.csv` dosyasına yazar. Bu dosya ölçümde kullanılır.

| # | Bozma | Örnek |
|---|---|---|
| B1 | Tekrarlanan müşteri (farklı yazımla) | `Ayşe Yılmaz`, `AYSE YILMAZ `, `Yılmaz, Ayşe` |
| B2 | Birebir tekrar eden sipariş satırı | Aynı satır 2-3 kez |
| B3 | Karışık tarih formatı | `2024-03-05`, `05/03/2024`, `5 Mart 2024`, `20240305`, `05.03.24` |
| B4 | Encoding bozulması | `Ä°stanbul`, `Ã‡ankaya`, `Å?ahin` |
| B5 | Eksik değer ve yer tutucu | boş, `NULL`, `-`, `yok`, `N/A`, `?`, `0000-00-00` |
| B6 | Para formatı karmaşası | `1.250,50 TL`, `1250.5`, `₺1,250.50`, `1250,5 tl` |
| B7 | Geçersiz ve aykırı değer | negatif adet, 250 yaşında müşteri, gelecek tarihli sipariş, `adet = 9999` |
| B8 | Kategori ve il yazım tutarsızlığı | `istanbul`, `İST`, `Istanbul`, `İstanbul (Avrupa)`. `Elektronik`, `elektronık`, `ELEKTRONİK` |
| B9 | Telefon formatı | `0532 123 45 67`, `+90(532)1234567`, `5321234567`, `532-123-4567` |
| B10 | Bozuk e-posta | `ayse@@gmail.com`, `ayse@gmail,com`, `AYSE@GMAIL.COM `, `ayse@gmial.com` |
| B11 | Boşluk ve görünmez karakter | Baş ve sondaki boşluklar, çift boşluk, `\t`, sıfır genişlikli boşluk |
| B12 | Tutarsız hesap | `toplam_tutar ≠ adet × birim_fiyat × (1 − indirim)` |
| B13 | Yetim kayıt | Siparişteki `musteri_id` veya `urun_id` diğer tabloda yok |
| B14 | Kaymış ve bozuk satır | Fazla ya da eksik ayraç, sütunlara kaymış değerler, tırnak hatası |
| B15 | Karışık birim ve tip | `adet` sütununda `"3 adet"`, `"üç"`, `3.0` |

## 2. Temizleme hattı

Her adım ayrı bir modüldür, tek başına test edilir ve raporda kendi bölümünü alır.

| Adım | Modül | Yaptığı iş |
|---|---|---|
| 1 | `okuma` | Encoding tespiti, bozuk satırları yakalayıp karantinaya alma (B14) |
| 2 | `onarim` | Mojibake düzeltme (B4), görünmez karakter ve boşluk temizliği (B11), yer tutucuları `NaN` yapma (B5) |
| 3 | `standart` | Tarih (B3), para (B6), telefon `+90 5XX XXX XX XX` (B9), e-posta (B10), sayı ve birim (B15) dönüşümü |
| 4 | `sozluk` | İl, ilçe ve kategori adlarını referans listeye eşleme, yakın eşleşme ile (B8) |
| 5 | `dogrulama` | İş kuralları: yaş aralığı, tarih sırası, pozitif adet, tutar hesabı (B7, B12), referans bütünlüğü (B13) |
| 6 | `tekrar` | Birebir tekrarları silme (B2), bulanık eşleşme ile müşteri birleştirme (B1), eski ID'leri yeni ID'ye yönlendirme |
| 7 | `cikti` | Temiz CSV ve Excel, karantina dosyası, rapor |

**Düzeltilemeyen değer ne olur?** Hat tahmin uydurmaz. Değer güvenle düzeltilemiyorsa boş bırakılır ve
`sorunlar.csv` dosyasına satır, sütun, orijinal değer ve sebep ile yazılır. Hesaplanabilen alanlar
(ör. `toplam_tutar`) diğer sütunlardan yeniden hesaplanır.

## 3. Çıktılar

```
cikti/
  temiz/musteriler.csv, urunler.csv, siparisler.csv
  temiz/veri.xlsx            # üç tablo ayrı sayfalarda
  karantina.csv              # okunamayan ve kurtarılamayan satırlar
  sorunlar.csv               # hücre bazlı: ne bulundu, ne yapıldı
  rapor.html                 # tek dosya, tarayıcıda açılır
```

**Temizlik raporu (Türkçe)** şunları gösterir:
- Önce/sonra özet: satır sayısı, eksik değer oranı, tekrar sayısı
- Her adımda kaç hücrenin değiştiği, örnek önce → sonra dönüşümleri
- Sütun bazlı kalite puanı
- **Doğruluk skoru:** gerçek doğruyla karşılaştırma. Bozma türü başına yakalama ve doğru düzeltme oranı
  (ör. "B3 tarih: 1.214 bozuk hücrenin %99,2'si doğru düzeltildi")

## 4. Kullanım (hedef)

```bash
pip install -e .
veri-temizle uret --satir 10000 --seed 42          # veri/kirli/ ve veri/gercek/ oluşur
veri-temizle temizle veri/kirli/ --cikti cikti/    # temizleme hattı
veri-temizle olc cikti/temiz/ veri/gercek/         # doğruluk skoru
veri-temizle hepsi --seed 42                       # üçü birden
```

## 5. Proje yapısı

```
veri_temizleme/
  uretici/     temiz.py, bozma.py, referans/ (iller, ilçeler, adlar, kategoriler)
  temizleme/   okuma.py, onarim.py, standart.py, sozluk.py, dogrulama.py, tekrar.py, cikti.py
  olcum.py
  rapor/       sablon.html
  cli.py
tests/
config.yaml
```

## 6. Aşamalar

| Aşama | İçerik | Bitti sayılır |
|---|---|---|
| 1 | Proje iskeleti, referans listeler, temiz veri üretici | 10.000 geçerli sipariş, tüm iş kuralları sağlanıyor |
| 2 | Bozma motoru ve `bozma_kaydi.csv` | B1–B15 ayarlanan oranlarda uygulanıyor |
| 3 | Temizleme hattı adım 1–4 | Her modülün birim testi var |
| 4 | Temizleme hattı adım 5–7 | Temiz CSV/Excel, karantina ve sorunlar dosyası üretiliyor |
| 5 | Ölçüm ve HTML rapor | Bozma türü başına doğruluk skoru |
| 6 | CLI, README, uçtan uca test | `veri-temizle hepsi` tek komutla çalışıyor |

**Başarı hedefi:** Genel doğru düzeltme oranı **≥ %95**. Temizlenen veride tekrar ve referans hatası kalmaması.

## Açık sorular

- Rapor HTML dışında bir dashboard veya web arayüzü olarak da istenir mi?
- Bozma oranları ne kadar sert olsun? Varsayılan: hücrelerin yaklaşık %5–10'u bozuk.
