"""2. bölüm: aynı kurallar, görmediği hatalar. Görselleri ve PDF'i üretir.

Rakamlar ornek_sonuc/sonuclar.json (1. bölüm) ve ornek_sonuc/bolum2/sonuclar.json dosyalarından okunur.
Örnek kartındaki satırlar veri_seti_surpriz/ ve kural çıktısından tek tek doğrulanarak seçildi.
Çalıştırma: python belgeler/bolum2_uret.py
"""

import html
import json
import subprocess
import tempfile
from pathlib import Path

from veri_temizleme.gorsel import FONT, _sayi, _yuzde, ekran_goruntusu, tablo_html, tarayici_bul

KOK = Path(__file__).resolve().parent.parent
REPO = "github.com/sefa05/Claude-veri-temizleme-"
DONDURULAN_COMMIT = "60d97ad"  # Kural kodunun son değiştiği commit. 2. bölümde hiç değiştirilmedi.

b1 = json.loads((KOK / "ornek_sonuc" / "sonuclar.json").read_text(encoding="utf-8"))["yontemler"]["kural"]
b2 = json.loads((KOK / "ornek_sonuc" / "bolum2" / "sonuclar.json").read_text(encoding="utf-8"))["yontemler"]["kural"]
t1, t2 = b1["tam"], b2["tam"]
kayip_satir = t2["satirlar"]["siparisler"]["gercek_satir"] - t2["satirlar"]["siparisler"]["bulunan_satir"]


def ok(a: float, b: float) -> str:
    return f"{_yuzde(a)} → {_yuzde(b)}"


# --- Karşılaştırma görseli ------------------------------------------------------------------------------------

karsilastirma = tablo_html(
    {"yontemler": {"bolum1": b1, "bolum2": b2}},
    baslik="Aynı kurallar, görmediği hatalar",
    etiketler={"bolum1": "Bilinen hatalar", "bolum2": "Görmediği hatalar"},
    alt_baslik="kod değişmedi · doğru düzeltilen bozuk hücre oranı",
    kutular=[(ok(t1["genel_dogruluk"], t2["genel_dogruluk"]), "genel doğru düzeltme"),
             (f"{t1['uydurma']['n']} → {t2['uydurma']['n']}", "uydurma"),
             (ok(t1["satir_bozmalari"]["B14"]["basari"], t2["satir_bozmalari"]["B14"]["basari"]),
              "bozuk satır kurtarma"),
             ("0", "değişen kod satırı")])
ekran_goruntusu(karsilastirma, KOK / "gorseller" / "bolum2_karsilastirma.png")

# --- Örnek kartı ----------------------------------------------------------------------------------------------

duzeltti = [("kargo_firmasi", "Yurtici Krg", "Yurtiçi Kargo"), ("durum", "Delivered", "Teslim Edildi"),
            ("birim_fiyat", "81 TL 62 kr", "81.62"), ("il", "İstanbul/Sarıyer", "İstanbul")]
bos = [("dogum_tarihi", "27 Şubat 1987 Cuma", "boş", "1987-02-27"),
       ("dogum_tarihi", "1105920000", "boş", "2005-01-17  (Unix zamanı)"),
       ("musteri_id", "MUS-00211", "boş", "M00211"), ("kargo_firmasi", "TY Express", "boş", "Trendyol Express")]
yanlis = [("ad", "Ya&#287;mur", "Ya&#287;mur", "Yağmur"), ("ad", "Ã…Å¾eyma", "Åžeyma", "Şeyma"),
          ("ad", "Ba_ak", "Ba_ak", "Başak")]
satir = [("satır", "S000015⇥M01692⇥U0206⇥…", "satır kayboldu", "sekmeyle ayrılmış satır"),
         ("durum", "Teslim Edildi␍", "satır kayboldu", "gizli \\r satırı ikiye böldü")]
e = html.escape


def kart_satiri(s, k, t, sinif, g=""):
    ek = f"<span class=g>gerçek: {e(g)}</span>" if g else ""
    return (f"<div class='r'><div class='s'>{e(s)}</div><div class='v kirli'>{e(k)}</div><div class='ok'>→</div>"
            f"<div class='v {sinif}'>{e(t)}{ek}</div></div>")


KART_CSS = """*{box-sizing:border-box;margin:0}body{width:1200px;background:#faf8f3;color:#1c1b19;
font-family:"Inter","Liberation Sans","DejaVu Sans",sans-serif;padding:60px 64px 44px}
h1{font-size:42px;line-height:1.15;font-weight:700}.alt{font-size:21px;color:#6d6a63;margin:12px 0 22px}
h2{font-size:20px;text-transform:uppercase;letter-spacing:.05em;margin:26px 0 8px;display:flex;align-items:center;gap:10px}
h2 .n{display:inline-grid;place-items:center;width:30px;height:30px;border-radius:50%;color:#fff;font-size:17px}
h2 small{font-size:15px;text-transform:none;letter-spacing:0;color:#6d6a63;font-weight:400}
.y h2 .n{background:#2f8a5b}.b h2 .n{background:#6d6a63}.x h2 .n{background:#c44b3f}.z h2 .n{background:#1c1b19}
.r{display:grid;grid-template-columns:170px minmax(0,1fr) 34px minmax(0,1.1fr);align-items:center;gap:12px;
padding:8px 0;border-bottom:1px solid #e7e3da}
.s{font-size:16px;color:#8a867d;font-family:"Liberation Mono","DejaVu Sans Mono",monospace}
.v{font-family:"Liberation Mono","DejaVu Sans Mono",monospace;font-size:20px;padding:6px 10px;border-radius:6px;
overflow-wrap:anywhere}
.kirli{background:#f3e3df;color:#8f2f25}.dogru{background:#e1efe6;color:#1f6b44}.notr{background:#ebe8e1;color:#4d4a44}
.yanlis{background:#f6dcd7;color:#9b2c21}.kayip{background:#2b2a27;color:#f3efe6}
.ok{font-size:22px;color:#9a968d;text-align:center}.g{display:block;font-size:15px;opacity:.75;margin-top:3px}
.kaynak{margin-top:28px;font-size:17px;color:#6d6a63;display:flex;justify-content:space-between}"""
kart = (f"<!doctype html><html lang='tr'><head><meta charset='utf-8'>{FONT}<style>{KART_CSS}</style></head><body>"
        "<h1>Kurallar görmediği hatayla karşılaşınca</h1>"
        "<p class='alt'>Gerçek örnekler · kural kodu değişmedi · sentetik e-ticaret verisi</p>"
        "<div class='y'><h2><span class='n'>✓</span>Hâlâ düzeltti</h2>"
        + "".join(kart_satiri(*x, "dogru") for x in duzeltti) + "</div>"
        "<div class='b'><h2><span class='n'>–</span>Sessizce boş bıraktı <small>gerçek değer belliydi</small></h2>"
        + "".join(kart_satiri(s, k, t, "notr", g) for s, k, t, g in bos) + "</div>"
        "<div class='x'><h2><span class='n'>✗</span>Güvenle yanlış yazdı</h2>"
        + "".join(kart_satiri(s, k, t, "yanlis", g) for s, k, t, g in yanlis) + "</div>"
        f"<div class='z'><h2><span class='n'>!</span>Satırı kaybetti <small>toplam {kayip_satir} sipariş</small></h2>"
        + "".join(kart_satiri(s, k, t, "kayip", g) for s, k, t, g in satir) + "</div>"
        f"<div class='kaynak'><span>Veri seti açık: sen de dene</span><span>{REPO}</span></div></body></html>")
ekran_goruntusu(kart, KOK / "gorseller" / "bolum2_ornekler.png")

# --- PDF ------------------------------------------------------------------------------------------------------

kz2 = t2["kurtarilabilir"]
b4 = t2["bozma_turu"]["B4"]
PDF_CSS = """
@page{size:A4;margin:16mm 16mm 18mm}
*{box-sizing:border-box}body{margin:0;color:#1c1b19;font:10.5pt/1.55 "Inter","Liberation Sans","DejaVu Sans",sans-serif}
h1{font-size:25pt;line-height:1.15;margin:0 0 6px;letter-spacing:-.01em}
h2{font-size:15pt;margin:0 0 8px}h3{font-size:11.5pt;margin:16px 0 4px}
.ust{font-size:9pt;text-transform:uppercase;letter-spacing:.08em;color:#8a867d;margin-bottom:10px}
.alt{font-size:12pt;color:#5f5c55;margin:0 0 18px}
.kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0 18px}
.kpi div{border:1px solid #e2ded4;border-radius:8px;padding:10px 12px;background:#faf8f3}
.kpi b{display:block;font-size:14pt;line-height:1.2;white-space:nowrap}.kpi span{font-size:9pt;color:#6d6a63}
.sayfa{page-break-after:always}.sayfa:last-child{page-break-after:auto}
img{width:100%;display:block;border:1px solid #e2ded4;border-radius:6px}
.not{background:#f7efdc;border-left:3px solid #d59a2c;padding:9px 12px;border-radius:4px;margin:14px 0}
code{font:9.5pt "Liberation Mono","DejaVu Sans Mono",monospace;background:#f1eee7;padding:1px 4px;border-radius:3px}
pre{font:9pt "Liberation Mono","DejaVu Sans Mono",monospace;background:#f1eee7;padding:9px 12px;border-radius:6px;
white-space:pre-wrap;margin:6px 0}
ol,ul{margin:4px 0 8px;padding-left:20px}li{margin:4px 0}.kaynak{color:#6d6a63;font-size:9pt;margin-top:10px}
"""
govde = f"""
<section class="sayfa">
<div class="ust">Kirli veri deneyi · 2. bölüm</div>
<h1>Kurallarım {_yuzde(t1['genel_dogruluk'])} yaptı. Görmediği hatalarla test edince ne oldu?</h1>
<p class="alt">Aynı veri, aynı kod, yeni hata biçimleri. Kural yöntemi {ok(t1['genel_dogruluk'], t2['genel_dogruluk'])}.</p>
<div class="kpi">
<div><b>{ok(t1['genel_dogruluk'], t2['genel_dogruluk'])}</b><span>bozuk hücrelerde doğru düzeltme</span></div>
<div><b>{t1['uydurma']['n']} → {t2['uydurma']['n']}</b><span>uydurma (bilinmeyen değere değer yazma)</span></div>
<div><b>0 → {kayip_satir}</b><span>kaybolan sipariş</span></div>
<div><b>0</b><span>değişen kod satırı</span></div>
</div>
<h2>1. bölümün açığı</h2>
<p>1. bölümde kural tabanlı temizleyici 10.000 siparişlik kirli verinin bozuk hücrelerini
{_yuzde(t1['genel_dogruluk'])} oranında doğru düzeltti. Ama bir sorun vardı: hataları da kuralları da aynı kişi yazdı.
Kural, hangi hatayla karşılaşacağını önceden biliyordu. Gerçek hayatta böyle olmaz.</p>
<h2>Bu bölümde ne değişti?</h2>
<ul>
<li><b>Kural kodu donduruldu.</b> Temizleme kodu <code>{DONDURULAN_COMMIT}</code> commit'indeki haliyle kaldı, tek satırına dokunulmadı.</li>
<li><b>Temiz veri aynı.</b> Aynı 2.500 müşteri, 300 ürün, 10.000 sipariş.</li>
<li><b>Hata türleri aynı, biçimleri yeni.</b> 15 hata türünün her biri gerçek hayatta görülen başka biçimlerle geldi:
<code>27 Şubat 1987 Cuma</code>, Unix zamanı, Excel tarih numarası, <code>ayse[at]gmail.com</code>,
<code>MUS-00211</code>, <code>81 TL 62 kr</code>, HTML karakter kodları, sekmeyle ayrılmış satırlar, görünmez
<code>\\r</code> karakteri.</li>
<li><b>Hepsi kurtarılabilir.</b> Yalnızca gerçek değeri kirli metinden kesin olarak çıkarılabilen biçimler seçildi.
Sonuç düşsün diye bilerek belirsiz veri üretilmedi.</li>
</ul>
<div class="not"><b>Dürüstlük notu:</b> Yeni biçimleri de ben seçtim ve kural kodunu biliyordum. Bu test kuralı
zorlamaya yönelik bir stres testidir. Gerçek bir veri kaynağındaki düşüş daha az ya da daha fazla olabilir.
Ölçülen şey şu: kurallar yazıldıkları dünyanın dışına çıkınca ne kadar ve nasıl kırılıyor?</div>
</section>

<section class="sayfa">
<h2>Hangi hata türünde ne kadar düştü?</h2>
<img src="file://{KOK / 'gorseller' / 'bolum2_karsilastirma.png'}">
</section>

<section class="sayfa">
<h2>Gerçek örnekler</h2>
<img src="file://{KOK / 'gorseller' / 'bolum2_ornekler.png'}">
</section>

<section class="sayfa">
<h2>Dersler</h2>
<ol>
<li><b>Kurallar bilinen dünyada çok iyi, yeni biçimde kırılgan.</b> Aynı kod, aynı hata türlerinin başka
yazımlarında {ok(t1['genel_dogruluk'], t2['genel_dogruluk'])} düştü. En sert düşüşler ID biçimi
({ok(t1['bozma_turu']['B13']['dogru'], t2['bozma_turu']['B13']['dogru'])}), e-posta
({ok(t1['bozma_turu']['B10']['dogru'], t2['bozma_turu']['B10']['dogru'])}) ve tarihlerde
({ok(t1['bozma_turu']['B3']['dogru'], t2['bozma_turu']['B3']['dogru'])}) oldu.</li>
<li><b>Kırılma çoğunlukla sessiz.</b> Kurtarılabilir hücrelerde boş kalma oranı {_yuzde(kz2['bos'])}. Kural hata vermedi,
uyarmadı, sadece boşluk üretti. İzlenmezse temiz görünen ama delik deşik bir tablo çıkar.</li>
<li><b>Bazen güvenle yanlış yazıyor.</b> Uydurma sayısı {t1['uydurma']['n']} → {t2['uydurma']['n']}. Bozuk Türkçe
karakterli hücrelerde yanlış değer oranı {_yuzde(b4['yanlis'])}: <code>Ya&amp;#287;mur</code> olduğu gibi
geçti, çift bozulmuş <code>Ã…Å¾eyma</code> yarım onarılıp <code>Åžeyma</code> oldu.</li>
<li><b>Tek bir görünmez karakter veri kaybettirir.</b> Hücre sonundaki <code>\\r</code> satırları ikiye böldü.
Sekme ve <code>|</code> ayraçlı satırlarla birlikte {kayip_satir} sipariş tamamen kayboldu.</li>
<li><b>Hâlâ çalışanlar da var.</b> Önek eşleşmesi yapan kurallar (<code>Yurtici Krg</code>,
<code>İstanbul/Sarıyer</code>) ve sadece rakamları ayıklayan telefon kuralı yeni biçimlere de dayandı. Genel kurallar dayanıklı, özel kurallar kırılgan.</li>
</ol>
<h3>Pratik sonuç</h3>
<p>Kural tabanlı bir hat kurduysanız doğruluğu kadar <b>boş hücre oranını, karantinaya düşen satır sayısını ve
satır sayısı farkını</b> da izleyin. Bu üç sayı sessiz kırılmanın ilk işareti. Kuralın tanımadığı değerleri boş
bırakmak yerine ayrıca raporlamak, yeni biçimleri erkenden görmenin en ucuz yolu.</p>

<h2 style="margin-top:20px">Sen de dene</h2>
<p>Her iki veri seti de açık. Kendi yöntemini iki sette de çalıştır ve düşüşü karşılaştır:</p>
<pre># 1. bölüm: bilinen hatalar
veri-temizle puanla benim_ciktim/
# 2. bölüm: sürpriz hatalar
veri-temizle puanla benim_ciktim2/ --gercek veri_seti_surpriz/gercek</pre>
<p>Yöntemin bilinen hatalarda iyi, sürpriz hatalarda da iyiyse gerçekten genelleşiyor demektir.</p>
<p class="kaynak">Kod, veri ve yöntem: {REPO} · Veri tamamen sentetiktir, gerçek kişilere ait değildir.</p>
</section>
"""
sayfa_html = (f"<!doctype html><html lang='tr'><head><meta charset='utf-8'><title>Kirli Veri Deneyi, 2. Bölüm</title>"
              f"{FONT}<style>{PDF_CSS}</style></head><body>{govde}</body></html>")
cikti = KOK / "belgeler" / "kirli_veri_deneyi_bolum2.pdf"
with tempfile.TemporaryDirectory() as gecici:
    yol = Path(gecici) / "bolum2.html"
    yol.write_text(sayfa_html, encoding="utf-8")
    subprocess.run([tarayici_bul(), "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=5000", f"--print-to-pdf={cikti}", f"file://{yol}"],
                   check=True, capture_output=True)
print(cikti)
