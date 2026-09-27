"""Paylaşım PDF'i: 1. bölüm, kural yönteminin sonuçları.

Rakamlar ornek_sonuc/sonuclar.json dosyasından okunur. Çalıştırma: python belgeler/pdf_uret.py
"""

import json
import subprocess
import tempfile
from pathlib import Path

from veri_temizleme.gorsel import FONT, _sayi, _yuzde, tarayici_bul

KOK = Path(__file__).resolve().parent.parent
s = json.loads((KOK / "ornek_sonuc" / "sonuclar.json").read_text(encoding="utf-8"))["yontemler"]["kural"]
t = s["tam"]
b8 = t["bozma_turu"]["B8"]["dogru"]
b3 = t["bozma_turu"]["B3"]["dogru"]
kz = t["kurtarilamaz"]
tk = t["tekrar"]
bozuk_hucre = sum(1 for satir in (KOK / "veri_seti" / "gercek" / "bozma_kaydi.csv").read_text(encoding="utf-8")
                  .splitlines()[1:] if ",*satir*," not in satir)
REPO = "github.com/sefa05/Claude-veri-temizleme-"

CSS = """
@page{size:A4;margin:16mm 16mm 18mm}
*{box-sizing:border-box}body{margin:0;color:#1c1b19;font:10.5pt/1.55 "Inter","Liberation Sans","DejaVu Sans",sans-serif}
h1{font-size:25pt;line-height:1.15;margin:0 0 6px;letter-spacing:-.01em}
h2{font-size:15pt;margin:0 0 8px}h3{font-size:11.5pt;margin:16px 0 4px}
.ust{font-size:9pt;text-transform:uppercase;letter-spacing:.08em;color:#8a867d;margin-bottom:10px}
.alt{font-size:12pt;color:#5f5c55;margin:0 0 18px}
.kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0 18px}
.kpi div{border:1px solid #e2ded4;border-radius:8px;padding:10px 12px;background:#faf8f3}
.kpi b{display:block;font-size:20pt;line-height:1.1}.kpi span{font-size:9pt;color:#6d6a63}
.sayfa{page-break-after:always}.sayfa:last-child{page-break-after:auto}
img{width:100%;display:block;border:1px solid #e2ded4;border-radius:6px}
.not{background:#f7efdc;border-left:3px solid #d59a2c;padding:9px 12px;border-radius:4px;margin:14px 0}
table{border-collapse:collapse;width:100%;font-size:9.8pt;margin:6px 0 4px}
th,td{text-align:left;padding:5px 8px;border-bottom:1px solid #e7e3da;vertical-align:top}th{color:#6d6a63;font-weight:600}
td.s{text-align:right;white-space:nowrap}code{font:9.5pt "Liberation Mono","DejaVu Sans Mono",monospace;
background:#f1eee7;padding:1px 4px;border-radius:3px}
pre{font:9pt "Liberation Mono","DejaVu Sans Mono",monospace;background:#f1eee7;padding:9px 12px;border-radius:6px;
white-space:pre-wrap;margin:6px 0}
ul{margin:4px 0 8px;padding-left:18px}li{margin:2px 0}.kaynak{color:#6d6a63;font-size:9pt;margin-top:10px}
"""

govde = f"""
<section class="sayfa">
<div class="ust">Kirli veri deneyi · 1. bölüm</div>
<h1>Kirli veriyi temizlemek için LLM mi lazım, yoksa kurallar yeter mi?</h1>
<p class="alt">10.000 sipariş, 15 bozma türü, hücre hücre ölçüm. Bu bölümde yalnızca LLM kullanmayan kural yöntemi var.</p>
<div class="kpi">
<div><b>{_yuzde(t['genel_dogruluk'])}</b><span>bozuk hücrelerde doğru düzeltme</span></div>
<div><b>{t['uydurma']['n']} / {_sayi(t['uydurma']['payda'])}</b><span>uydurma (bilinmeyen değere değer yazma)</span></div>
<div><b>{tk['f1']:.3f}</b><span>müşteri eşleştirme F1</span></div>
<div><b>{s['sure']:.0f} sn · $0</b><span>süre ve maliyet</span></div>
</div>
<h2>Deney nasıl kuruldu?</h2>
<p>Bir Türk e-ticaret sitesini taklit eden sentetik veri ürettim: 2.500 müşteri, 300 ürün, 10.000 sipariş. Önce veri
temiz üretildi ve saklandı. Sonra bilerek bozuldu: tarihler beş ayrı biçimde yazıldı, Türkçe karakterler bozuldu,
fiyatlara TL ve ₺ işaretleri eklendi, müşteriler farklı yazımlarla tekrarlandı, kargo firmaları kısaltıldı, bazı
satırlar birbirine yapıştı. Toplam {_sayi(bozuk_hucre)} hücre bozuldu ve her bozma kaydedildi.</p>
<p>Temizleme sonucu saklanan temiz veriyle karşılaştırıldı. Bu yüzden "iyi görünüyor" demek yerine her hata türü için
kesin bir oran verebiliyorum.</p>
<h3>Neyi ölçtüm?</h3>
<ul>
<li><b>Doğru düzeltme:</b> Kurtarılabilir bozuk hücrelerin ({_sayi(t['kurtarilabilir']['n'])} hücre) yüzde kaçı gerçek değerine döndü.</li>
<li><b>Uydurma:</b> Gerçek değeri bilinemeyen hücreler var. Örneğin 2036 tarihli bir siparişin gerçek tarihi veriden çıkarılamaz. Doğru davranış bu hücreyi boş bırakmaktır. Oraya yazılan her yanlış değer uydurma sayıldı.</li>
<li><b>Temiz hücreyi bozma:</b> Zaten doğru olan {_sayi(t['temiz_hucreler']['n'])} hücreden kaçı temizlik sırasında bozuldu. Sonuç: {_yuzde(1 - t['temiz_hucreler']['dogru'])}.</li>
<li><b>Müşteri eşleştirme:</b> Aynı kişinin tekrarlanan kayıtları bulunup birleştirildi mi?</li>
</ul>
<div class="not"><b>Bu sonucu okurken:</b> Bozmaları da kuralları da aynı kişi yazdı. Bu yüzden kural yöntemi burada
gerçek hayatta olacağından daha iyi görünüyor. Gerçekte kural yazan kişi hataların hepsini önceden görmez. Asıl
soru, LLM'in kuralın takıldığı yerleri değer uydurmadan kapatıp kapatamayacağı. Bu, 2. bölümün konusu.</div>
</section>

<section class="sayfa">
<h2>Hangi hata ne kadar düzeldi?</h2>
<img src="file://{KOK / 'gorseller' / 'kural_tablosu.png'}">
</section>

<section class="sayfa">
<h2>Gerçek örnekler</h2>
<img src="file://{KOK / 'gorseller' / 'kirli_temiz_ornekler.png'}">
</section>

<section class="sayfa">
<h2>Kural nerede takıldı?</h2>
<table>
<tr><th>Sorun</th><th>Örnek</th><th class="s">Sonuç</th></tr>
<tr><td>Sözlükte olmayan kısaltma ve eş anlamlılar</td><td><code>TEX</code>, <code>YK</code>, <code>Papara</code>, <code>Tamamlandı</code></td><td class="s">{_yuzde(b8)} doğru, kalanı boş</td></tr>
<tr><td>Gün/ay sırası belirsiz tarih</td><td><code>06/01/1967</code>: 6 Ocak mı, 1 Haziran mı?</td><td class="s">{_yuzde(b3)} doğru</td></tr>
<tr><td>Kanıtı zayıf müşteri çiftleri</td><td>Doğum tarihi bozuk, telefon yok, sadece ilçe ve e-posta benziyor</td><td class="s">{tk['gercek_cift']} çiftten {tk['dogru_cift']}'sı bulundu</td></tr>
</table>
<p>Kural bilmediği bir değerle karşılaşınca tahmin etmiyor, hücreyi boş bırakıyor. Bu yüzden hata yaptığı yerlerin
çoğunda yanlış değer değil boşluk üretiyor. Müşteri eşleştirmede de hiç yanlış eşleşme yapmadı.</p>
<h3>Gerçeği bilinemeyen hücrelerde ne yaptı?</h3>
<p>{_sayi(kz['n'])} kurtarılamaz hücrenin {_yuzde(kz['bos'])}'ini boş bıraktı, {_yuzde(kz['yanlis'])}'ine yanlış değer yazdı,
{_yuzde(kz['dogru'])}'inde tahmini tuttu.</p>
<h3>Yapısal işler</h3>
<ul>
<li>{s['istatistik']['onarilan_satir']} bozuk satırın hepsi kurtarıldı (<code>;</code> ayraçlı, fazladan alanlı, birbirine yapışmış satırlar).</li>
<li>{s['istatistik']['silinen_tekrar_siparis']} tekrar sipariş satırı silindi, {s['istatistik']['birlesen_musteri']} tekrar müşteri kaydı birleştirildi.</li>
</ul>

<h2 style="margin-top:22px">Veri seti açık: sen de dene</h2>
<p>Kirli veri, cevap anahtarı ve puanlama aracı repoda. Veriyi istediğin yöntemle (kural, LLM, ajan ya da elle)
temizle, tek komutla skorunu al:</p>
<pre>git clone https://{REPO}
pip install -e .
veri-temizle puanla benim_ciktim/</pre>
<p>Her hata türü için ayrı puan, uydurma sayısı ve müşteri eşleştirme skoru çıkar. Beklenen çıktı biçimi
<code>veri_seti/README.md</code> dosyasında. Kural yöntemi {_yuzde(t['genel_dogruluk'])} yaptı. Geçebilir misin?</p>

<h2 style="margin-top:22px">Sıradaki: 2. bölüm</h2>
<p>Aynı veri iki yöntemle daha temizlenecek:</p>
<ul>
<li><b>Sadece LLM:</b> Ham satırlar Claude'a gidiyor, model temiz kaydı döndürüyor.</li>
<li><b>Hibrit:</b> Önce kural çalışıyor, çözemediği hücreler LLM'e soruluyor. Model il ve seçenek alanlarında
serbest yazmıyor, referans listeden çekilen adaylar arasından seçiyor.</li>
</ul>
<p>Doğruluk, uydurma, maliyet ve süre yan yana karşılaştırılacak.</p>
<p class="kaynak">Kod, veri ve yöntem: {REPO} · Veri tamamen sentetiktir, gerçek kişilere ait değildir.</p>
</section>
"""

html = f"<!doctype html><html lang='tr'><head><meta charset='utf-8'><title>Kirli Veri Deneyi, 1. Bölüm</title>{FONT}<style>{CSS}</style></head><body>{govde}</body></html>"
cikti = KOK / "belgeler" / "kirli_veri_deneyi_bolum1.pdf"
with tempfile.TemporaryDirectory() as gecici:
    sayfa = Path(gecici) / "rapor.html"
    sayfa.write_text(html, encoding="utf-8")
    subprocess.run([tarayici_bul(), "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=5000", f"--print-to-pdf={cikti}", f"file://{sayfa}"],
                   check=True, capture_output=True)
print(cikti)
