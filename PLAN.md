# Veri Temizleme Projesi: Kural mı, LLM mi, Hibrit mi?

Dağınık, bozuk ve işe yaramaz haldeki e-ticaret verisini **üç farklı yöntemle** temizleyip hangisinin gerçekten
çalıştığını ölçen bir Python projesi. Amaç X için ölçüme dayalı içerik üretmek: "LLM'e 10 bin kirli satır verdim,
şurada iyi, şurada uydurdu, maliyeti şu."

## Karşılaştırılan yöntemler

| Yöntem | Nasıl çalışır |
|---|---|
| **Kural** | Sadece pandas ve elle yazılmış kurallar. Referans nokta. LLM çağrısı yok |
| **LLM** | Satırlar küçük gruplar halinde Claude'a gider, model temiz satırı JSON şemasıyla döner. Bozma kataloğu modele gösterilmez |
| **Hibrit** | Kurallar önce çalışır. Kuralın güvenle çözemediği hücreler (belirsiz tarih, eşleşmeyen il/kategori, şüpheli müşteri tekrarı) LLM'e gider. İl ve kategori için model, referans listeden çekilen adaylar arasından seçim yapar (RAG) |

Her yöntem aynı gerçek doğruyla şu dört eksende ölçülür:

| Metrik | Anlamı |
|---|---|
| Doğruluk | Bozuk hücrelerin yüzde kaçı gerçek değerine döndü (bozma türü başına) |
| Uydurma | Gerçekte boş/kurtarılamaz olan veya bozulmamış bir hücreye yanlış ama emin görünen değer yazılması |
| Maliyet | Token kullanımından hesaplanan $ |
| Süre | Duvar saati süresi |

LLM yöntemi 10 bin satırın tamamında pahalı olacağı için varsayılan olarak **1.000 satırlık sabit bir örneklem**
üzerinde çalışır. Kural ve hibrit yöntemleri tüm veride çalışır, ama karşılaştırma tablosu aynı örneklemde de verilir.

Bu bir Python projesidir. Veriyi kendimiz **sentetik** olarak üretiriz. Üretici önce temiz veriyi (gerçek doğru) oluşturur,
sonra bilerek bozar. Temizleme hattının başarısı, temiz sonucun bu gerçek doğruyla karşılaştırılmasıyla **sayısal
olarak** ölçülür.

## Kararlar

| Konu | Karar |
|---|---|
| Senaryo | Türk bir e-ticaret sitesinin müşteri, ürün ve sipariş kayıtları |
| Ölçek | **10.000 sipariş satırı** (ek olarak ~2.500 müşteri, ~300 ürün) |
| Dil | Türkçe: veri, sütun adları, rapor ve CLI mesajları |
| Teknoloji | Python 3.11, pandas, rapidfuzz, Anthropic SDK, pytest |
| Arayüz | Komut satırı (CLI) + tek dosyalık HTML karşılaştırma raporu |
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

Her bozma türünün bir **oranı** vardır (ör. `%8`) ve oranlar `uretici/bozma.py` içinde tanımlıdır. `--oran-carpani` hepsini birlikte ölçekler.
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

## 4. Kullanım

```bash
pip install -e .
veri-temizle deney                  # üret + kural/hibrit/LLM ile temizle + ölç + rapor
veri-temizle deney --yontem kural   # API anahtarı olmadan
veri-temizle maliyet                # LLM yönteminin kaba maliyet tahmini
```

## 5. Proje yapısı

Güncel yapı için README'ye bakın.

## 6. Aşamalar

| Aşama | İçerik | Durum |
|---|---|---|
| 1 | Proje iskeleti, referans listeler, temiz veri üretici | Tamam |
| 2 | Bozma motoru ve `bozma_kaydi.csv` | Tamam |
| 3 | Kural hattı: okuma, onarım, standartlaştırma, sözlük | Tamam |
| 4 | Kural hattı: türetme, doğrulama, tekrar birleştirme, çıktı | Tamam |
| 5 | Ölçüm ve HTML rapor | Tamam |
| 6 | CLI, README, testler | Tamam |
| 7 | Sadece LLM ve hibrit yöntemler (sahte istemciyle test edildi) | Kod hazır, gerçek çalıştırma API anahtarı bekliyor |
| 8 | Gerçek karşılaştırma ve X serisi için grafikler | Bekliyor |

**Başarı hedefi:** Genel doğru düzeltme oranı **≥ %95**. Kural yöntemi tüm veride %97,7'ye ulaştı.

## Açık sorular

- Hangi model(ler) karşılaştırılacak? Varsayılan `claude-opus-5`. Aynı deney `--model` ile ucuz bir modelde de
  çalıştırılabilir.
- Kural yöntemi, aynı kişinin hem bozma hem kural yazmasından dolayı avantajlı. Kural yazarının görmediği bir
  "sürpriz bozma" seti eklemek bu yanlılığı ölçmenin yolu olabilir.
