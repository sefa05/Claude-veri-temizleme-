"""Netlify'a yüklenecek statik site: ana sayfa + 1. bölüm + 2. bölüm.

Rakamlar ornek_sonuc/ altındaki sonuç dosyalarından okunur. Çıktı site/ klasörüne yazılır.
Çalıştırma: python belgeler/site_uret.py [--site-url https://alan-adin.netlify.app]
"""

import argparse
import html
import json
import subprocess
import tempfile
from pathlib import Path

from veri_temizleme.gorsel import tarayici_bul
from veri_temizleme.uretici.bozma import BOZMA_ADLARI

KOK = Path(__file__).resolve().parent.parent
SITE = KOK / "site"
REPO = "https://github.com/sefa05/Claude-veri-temizleme-"
DONDURULAN_COMMIT = "60d97ad"

p = argparse.ArgumentParser()
p.add_argument("--site-url", default="https://raw.githubusercontent.com/sefa05/Claude-veri-temizleme-/"
               "claude/selam-2d3yw9/site", help="Önizleme görselleri için mutlak adres (Netlify alan adı)")
SITE_URL = p.parse_args().site_url.rstrip("/")

b1 = json.loads((KOK / "ornek_sonuc" / "sonuclar.json").read_text(encoding="utf-8"))["yontemler"]["kural"]
b2 = json.loads((KOK / "ornek_sonuc" / "bolum2" / "sonuclar.json").read_text(encoding="utf-8"))["yontemler"]["kural"]
t1, t2 = b1["tam"], b2["tam"]
kayip = t2["satirlar"]["siparisler"]["gercek_satir"] - t2["satirlar"]["siparisler"]["bulunan_satir"]
e = html.escape

KISA = {**BOZMA_ADLARI, "B2": "Tekrarlanan sipariş", "B5": "Eksik değer", "B6": "Sayı ve para formatı",
        "B7": "Geçersiz değer", "B11": "Görünmez karakter", "B14": "Kaymış / bozuk satır"}


def y(v: float, basamak: int = 1) -> str:
    if v >= 0.9995:
        return "%100"
    m = f"{v * 100:.{basamak}f}"
    return "%" + (m[:-2] if m.endswith(".0") else m.replace(".", ","))


def sayi(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def turler(t: dict) -> dict[str, tuple[int, float]]:
    d = {b: (v["n"], v["dogru"]) for b, v in t["bozma_turu"].items()}
    d.update({b: (v["n"], v["basari"]) for b, v in t["satir_bozmalari"].items()})
    return d


T1, T2 = turler(t1), turler(t2)

# --- Ortak parçalar -------------------------------------------------------------------------------------------

CSS = """
:root{color-scheme:light;--bg:#fcfcfb;--kart:#ffffff;--yazi:#0b0b0b;--ikincil:#52514e;--soluk:#8a887f;
--cizgi:#e6e4dd;--iz:#efede7;--seri:#2a78d6;--seri-acik:#a9c8ef;--iyi:#1f7a4d;--kotu:#b83232;
--kirli-bg:#fbe9e6;--kirli:#8f2f25;--temiz-bg:#e3f1e8;--temiz:#1f6b44;--notr-bg:#eeece6;--notr:#4d4a44;
--kayip-bg:#262523;--kayip:#f3efe6;--not-bg:#fbf3e1;--not-cizgi:#d59a2c}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])){color-scheme:dark;--bg:#141413;
--kart:#1a1a19;--yazi:#ffffff;--ikincil:#c3c2b7;--soluk:#8f8d85;--cizgi:#2e2d2a;--iz:#262523;--seri:#3987e5;
--seri-acik:#5d82b3;--iyi:#5cc28f;--kotu:#ec7272;--kirli-bg:#3a201c;--kirli:#f2a79c;--temiz-bg:#16301f;
--temiz:#8fd9ae;--notr-bg:#2a2926;--notr:#d6d3ca;--kayip-bg:#f3efe6;--kayip:#1a1a19;--not-bg:#2d2616;
--not-cizgi:#c98500}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#141413;--kart:#1a1a19;--yazi:#ffffff;--ikincil:#c3c2b7;
--soluk:#8f8d85;--cizgi:#2e2d2a;--iz:#262523;--seri:#3987e5;--seri-acik:#5d82b3;--iyi:#5cc28f;--kotu:#ec7272;
--kirli-bg:#3a201c;--kirli:#f2a79c;--temiz-bg:#16301f;--temiz:#8fd9ae;--notr-bg:#2a2926;--notr:#d6d3ca;
--kayip-bg:#f3efe6;--kayip:#1a1a19;--not-bg:#2d2616;--not-cizgi:#c98500}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--yazi);font:17px/1.65 "Inter",system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--seri);text-underline-offset:3px}
main{max-width:760px;margin:0 auto;padding:28px 16px 80px}
nav{display:flex;gap:18px;flex-wrap:wrap;font-size:15px;margin-bottom:40px}
nav a{color:var(--ikincil);text-decoration:none}nav a[aria-current]{color:var(--yazi);font-weight:600}
.ust{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--soluk);margin:0 0 10px}
h1{font-size:clamp(30px,6vw,46px);line-height:1.1;letter-spacing:-.02em;margin:0 0 14px}
h2{font-size:24px;line-height:1.25;letter-spacing:-.01em;margin:56px 0 12px}
h3{font-size:18px;margin:28px 0 6px}
.giris{font-size:20px;color:var(--ikincil);margin:0 0 28px}
p{margin:0 0 14px}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:28px 0}
.kpi div{background:var(--kart);border:1px solid var(--cizgi);border-radius:12px;padding:14px 16px}
.kpi b{display:block;font-size:24px;line-height:1.1;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.kpi span{display:block;font-size:14px;color:var(--ikincil);margin-top:4px;line-height:1.35}
.not{background:var(--not-bg);border-left:3px solid var(--not-cizgi);border-radius:6px;padding:14px 16px;margin:24px 0;font-size:16px}
code{font:0.88em ui-monospace,"SF Mono",Menlo,Consolas,monospace;background:var(--iz);padding:1px 5px;border-radius:4px;overflow-wrap:anywhere}
pre{font:14px/1.6 ui-monospace,"SF Mono",Menlo,Consolas,monospace;background:var(--iz);padding:14px 16px;border-radius:10px;overflow-x:auto;margin:10px 0 16px}
ol,ul{padding-left:22px;margin:0 0 16px}li{margin:8px 0}
.grafik{background:var(--kart);border:1px solid var(--cizgi);border-radius:14px;padding:18px 18px 10px;margin:20px 0 8px;position:relative}
.grafik-baslik{font-weight:650;font-size:16px;margin:0 0 2px}.grafik-alt{font-size:14px;color:var(--ikincil);margin:0 0 14px}
.lejant{display:flex;gap:18px;flex-wrap:wrap;font-size:14px;color:var(--ikincil);margin:0 0 10px}
.lejant i{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:6px;vertical-align:-1px}
.sira{display:grid;grid-template-columns:minmax(0,190px) minmax(0,1fr) 62px;align-items:center;gap:12px;padding:7px 0;border-top:1px solid var(--cizgi);cursor:default}
.sira:first-of-type{border-top:0}
.sira .ad{font-size:15px;line-height:1.3}.sira .ad small{color:var(--soluk);margin-left:4px}
.sira .d{font-size:15px;text-align:right;font-variant-numeric:tabular-nums;color:var(--yazi)}
.iz{position:relative;height:22px}
.iz::before{content:"";position:absolute;left:0;right:0;top:10px;height:2px;background:var(--iz);border-radius:2px}
.cubuk{position:absolute;left:0;top:4px;height:14px;background:var(--seri);border-radius:0 4px 4px 0}
.cizgi{position:absolute;top:10px;height:2px;background:var(--seri-acik)}
.nokta{position:absolute;top:3px;width:16px;height:16px;margin-left:-8px;border-radius:50%;border:2px solid var(--kart)}
.nokta.once{background:var(--seri-acik)}.nokta.sonra{background:var(--seri)}
.sira:hover .ad,.sira:focus-visible .ad{color:var(--seri)}
.ipucu{position:absolute;pointer-events:none;background:var(--yazi);color:var(--bg);font-size:13px;line-height:1.45;padding:8px 10px;border-radius:8px;white-space:nowrap;opacity:0;transition:opacity .1s;z-index:2}
details{margin:6px 0 0;font-size:14px}summary{cursor:pointer;color:var(--ikincil);padding:6px 0}
table{border-collapse:collapse;width:100%;font-size:14px;margin:6px 0}
th,td{padding:6px 8px;border-bottom:1px solid var(--cizgi);text-align:right}th:first-child,td:first-child{text-align:left}
th{color:var(--ikincil);font-weight:600}
.ornekler{margin:16px 0}
.grup{font-size:14px;font-weight:650;text-transform:uppercase;letter-spacing:.05em;margin:22px 0 8px;display:flex;align-items:center;gap:8px}
.grup small{text-transform:none;letter-spacing:0;font-weight:400;color:var(--ikincil)}
.isaret{display:inline-grid;place-items:center;width:22px;height:22px;border-radius:50%;font-size:13px;color:#fff}
.ornek{display:grid;grid-template-columns:minmax(0,1fr) 20px minmax(0,1fr);gap:8px;align-items:center;margin:6px 0}
.ornek .s{grid-column:1/-1;font:12px ui-monospace,Menlo,monospace;color:var(--soluk);margin:6px 0 -4px}
.deger{font:14px/1.4 ui-monospace,"SF Mono",Menlo,Consolas,monospace;padding:7px 10px;border-radius:8px;overflow-wrap:anywhere}
.deger small{display:block;font-size:12px;opacity:.8;margin-top:2px}
.kirli{background:var(--kirli-bg);color:var(--kirli)}.temiz{background:var(--temiz-bg);color:var(--temiz)}
.bos{background:var(--notr-bg);color:var(--notr)}.yanlis{background:var(--kirli-bg);color:var(--kirli);outline:1.5px solid var(--kotu)}
.kayip{background:var(--kayip-bg);color:var(--kayip)}.ok{color:var(--soluk);text-align:center}
.bolumler{display:grid;gap:14px;margin:28px 0}
.bolum-kart{display:block;background:var(--kart);border:1px solid var(--cizgi);border-radius:14px;padding:20px;color:inherit;text-decoration:none;transition:border-color .15s}
.bolum-kart:hover{border-color:var(--seri)}.bolum-kart h2{margin:4px 0 6px;font-size:22px}
.bolum-kart .buyuk{font-size:34px;font-weight:700;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.bolum-kart p{color:var(--ikincil);margin:6px 0 0;font-size:16px}
.sonraki{display:block;margin-top:48px;padding:18px 20px;border:1px solid var(--cizgi);border-radius:14px;text-decoration:none;color:inherit;background:var(--kart)}
.sonraki span{font-size:13px;color:var(--soluk);text-transform:uppercase;letter-spacing:.06em}.sonraki b{display:block;font-size:19px;margin-top:4px;color:var(--seri)}
footer{margin-top:56px;padding-top:18px;border-top:1px solid var(--cizgi);font-size:14px;color:var(--ikincil)}
@media (max-width:560px){body{font-size:16px}.sira{grid-template-columns:minmax(0,1fr) 56px;row-gap:4px}
.sira .ad{grid-column:1/-1}.ornek{grid-template-columns:minmax(0,1fr)}.ornek .ok{display:none}
.giris{font-size:18px}}
"""

JS = """
document.querySelectorAll('.grafik').forEach(function(g){
  var ipucu=g.querySelector('.ipucu');
  g.querySelectorAll('.sira').forEach(function(s){
    function goster(){ipucu.innerHTML=s.dataset.ipucu;ipucu.style.opacity=1;
      var r=s.getBoundingClientRect(),gr=g.getBoundingClientRect();
      var x=Math.min(Math.max(8,r.left-gr.left+r.width/2-ipucu.offsetWidth/2),gr.width-ipucu.offsetWidth-8);
      ipucu.style.left=x+'px';ipucu.style.top=(r.top-gr.top-ipucu.offsetHeight-6)+'px';}
    function gizle(){ipucu.style.opacity=0;}
    s.addEventListener('mouseenter',goster);s.addEventListener('mouseleave',gizle);
    s.addEventListener('focus',goster);s.addEventListener('blur',gizle);
    s.addEventListener('touchstart',goster,{passive:true});
  });
});
"""


def sayfa(dosya: str, baslik: str, aciklama: str, og: str, govde: str, aktif: str) -> None:
    menu = "".join(f"<a href='{h}'{' aria-current=page' if k == aktif else ''}>{e(a)}</a>"
                   for k, h, a in (("ana", "/", "Deney"), ("b1", "/bolum-1", "1. bölüm"),
                                   ("b2", "/bolum-2", "2. bölüm"), ("repo", REPO, "Kod ve veri")))
    metin = f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(baslik)}</title><meta name="description" content="{e(aciklama)}">
<meta property="og:type" content="article"><meta property="og:title" content="{e(baslik)}">
<meta property="og:description" content="{e(aciklama)}"><meta property="og:image" content="{SITE_URL}/{og}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{SITE_URL}/{og}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="/stil.css"></head>
<body><main><nav>{menu}</nav>{govde}
<footer>Veri tamamen sentetiktir, gerçek kişilere ait değildir. Kod, veri seti ve ölçüm betikleri açık:
<a href="{REPO}">{REPO.removeprefix('https://')}</a></footer></main><script src="/grafik.js"></script></body></html>"""
    (SITE / dosya).write_text(metin, encoding="utf-8")


def kpi(ogeler) -> str:
    return "<div class='kpi'>" + "".join(f"<div><b>{e(d)}</b><span>{e(a)}</span></div>" for d, a in ogeler) + "</div>"


def cubuk_grafik(baslik: str, alt: str) -> str:
    sirali = sorted(T1, key=lambda b: (T1[b][1], -T1[b][0]))
    satirlar = []
    for b in sirali:
        n, v = T1[b]
        ipucu = f"<b>{e(KISA[b])}</b> ({b})<br>{sayi(n)} {'satır' if b in ('B2', 'B14') else 'hücre'} · doğru: {y(v)}"
        satirlar.append(f"<div class='sira' tabindex='0' data-ipucu='{e(ipucu)}'><div class='ad'>{e(KISA[b])}"
                        f"<small>{b}</small></div><div class='iz'><div class='cubuk' style='width:{v * 100:.2f}%'>"
                        f"</div></div><div class='d'>{y(v)}</div></div>")
    tablo = "".join(f"<tr><td>{e(KISA[b])} ({b})</td><td>{sayi(T1[b][0])}</td><td>{y(T1[b][1])}</td></tr>"
                    for b in sirali)
    return (f"<figure class='grafik' role='group' aria-label='{e(baslik)}'><div class='ipucu' role='status'></div>"
            f"<p class='grafik-baslik'>{e(baslik)}</p><p class='grafik-alt'>{e(alt)}</p>{''.join(satirlar)}"
            f"<details><summary>Tablo olarak göster</summary><table><tr><th>Hata türü</th><th>Adet</th>"
            f"<th>Doğru</th></tr>{tablo}</table></details></figure>")


def dumbbell(baslik: str, alt: str) -> str:
    sirali = sorted(T2, key=lambda b: (T2[b][1], -T2[b][0]))
    satirlar = []
    for b in sirali:
        v1, v2 = T1[b][1], T2[b][1]
        sol, sag = min(v1, v2), max(v1, v2)
        ipucu = (f"<b>{e(KISA[b])}</b> ({b})<br>Bilinen hatalar: {y(v1)}<br>Görmediği hatalar: {y(v2)}")
        satirlar.append(
            f"<div class='sira' tabindex='0' data-ipucu='{e(ipucu)}'><div class='ad'>{e(KISA[b])}<small>{b}</small>"
            f"</div><div class='iz'><div class='cizgi' style='left:{sol * 100:.2f}%;width:{(sag - sol) * 100:.2f}%'>"
            f"</div><div class='nokta once' style='left:{v1 * 100:.2f}%'></div>"
            f"<div class='nokta sonra' style='left:{v2 * 100:.2f}%'></div></div><div class='d'>{y(v2)}</div></div>")
    tablo = "".join(f"<tr><td>{e(KISA[b])} ({b})</td><td>{y(T1[b][1])}</td><td>{y(T2[b][1])}</td></tr>"
                    for b in sirali)
    return (f"<figure class='grafik' role='group' aria-label='{e(baslik)}'><div class='ipucu' role='status'></div>"
            f"<p class='grafik-baslik'>{e(baslik)}</p><p class='grafik-alt'>{e(alt)}</p>"
            "<div class='lejant'><span><i style='background:var(--seri-acik)'></i>Bilinen hatalar (1. bölüm)</span>"
            "<span><i style='background:var(--seri)'></i>Görmediği hatalar (2. bölüm)</span></div>"
            f"{''.join(satirlar)}<details><summary>Tablo olarak göster</summary><table><tr><th>Hata türü</th>"
            f"<th>Bilinen</th><th>Görmediği</th></tr>{tablo}</table></details></figure>")


def ornek(s, kirli, temiz, sinif, gercek=""):
    ek = f"<small>gerçek: {e(gercek)}</small>" if gercek else ""
    return (f"<div class='ornek'><div class='s'>{e(s)}</div><div class='deger kirli'>{e(kirli)}</div>"
            f"<div class='ok' aria-hidden='true'>→</div><div class='deger {sinif}'>{e(temiz)}{ek}</div></div>")


def grup(isaret, renk, baslik, alt=""):
    return (f"<div class='grup'><span class='isaret' style='background:{renk}' aria-hidden='true'>{isaret}</span>"
            f"{e(baslik)}{f' <small>{e(alt)}</small>' if alt else ''}</div>")


# --- Sayfalar -------------------------------------------------------------------------------------------------

def ana_sayfa():
    govde = f"""
<p class="ust">Açık veri deneyi</p>
<h1>Kirli veriyi kurallarla temizledim. Sonra kurallara görmedikleri hataları verdim.</h1>
<p class="giris">10.000 siparişlik bir e-ticaret verisini bilerek 15 farklı şekilde bozdum ve temiz halini sakladım.
Böylece her düzeltmeyi hücre hücre ölçebildim. İki bölümlük bir deney.</p>
<div class="bolumler">
<a class="bolum-kart" href="/bolum-1"><span class="ust">1. bölüm</span><h2>Kurallar ne kadar temizler?</h2>
<div class="buyuk">{y(t1['genel_dogruluk'])}</div><p>Bilinen hatalarda doğru düzeltme. {t1['uydurma']['n']} uydurma, 8 saniye, $0.</p></a>
<a class="bolum-kart" href="/bolum-2"><span class="ust">2. bölüm</span><h2>Görmediği hatalarda ne olur?</h2>
<div class="buyuk">{y(t1['genel_dogruluk'])} → {y(t2['genel_dogruluk'])}</div><p>Kod değişmedi. {kayip} sipariş kayboldu,
hücrelerin {y(t2['kurtarilabilir']['bos'])} kadarı sessizce boş kaldı.</p></a>
</div>
<h2>Sen de dene</h2>
<p>İki veri seti de açık. Kendi yönteminle (kural, LLM, ajan ya da elle) temizle, tek komutla skorunu al.
15 hata türünün her biri için ayrı puan çıkar.</p>
<pre>git clone {REPO}
pip install -e .
veri-temizle puanla benim_ciktim/</pre>
<p><a href="{REPO}/tree/claude/selam-2d3yw9/veri_seti">Veri setine git →</a></p>"""
    sayfa("index.html", "Kirli Veri Deneyi", "Kirli e-ticaret verisini kurallarla temizleyip her düzeltmeyi ölçen iki "
          "bölümlük açık deney.", "og-ana.png", govde, "ana")


def bolum1():
    govde = f"""
<p class="ust">Kirli veri deneyi · 1. bölüm</p>
<h1>Kirli veriyi temizlemek için LLM mi lazım, yoksa kurallar yeter mi?</h1>
<p class="giris">10.000 sipariş, 15 hata türü, hücre hücre ölçüm. Bu bölümde LLM yok, sadece pandas ve kurallar var.</p>
{kpi([(y(t1['genel_dogruluk']), 'bozuk hücrelerde doğru düzeltme'),
      (f"{t1['uydurma']['n']} / {sayi(t1['uydurma']['payda'])}", 'uydurma: bilinmeyen değere değer yazma'),
      (f"{t1['tekrar']['f1']:.3f}".replace('.', ','), 'müşteri eşleştirme F1, sıfır yanlış eşleşme'),
      (f"{b1['sure']:.0f} sn · $0", 'süre ve maliyet')])}
<h2>Deney nasıl kuruldu?</h2>
<p>Bir Türk e-ticaret sitesini taklit eden sentetik veri ürettim: 2.500 müşteri, 300 ürün, 10.000 sipariş. Önce veri
temiz üretildi ve saklandı. Sonra bilerek bozuldu. Tarihler beş ayrı biçimde yazıldı, Türkçe karakterler bozuldu,
fiyatlara TL ve ₺ işaretleri eklendi, aynı müşteri farklı yazımlarla tekrarlandı, kargo firmaları kısaltıldı, bazı
satırlar birbirine yapıştı. Toplam {sayi(t1['kurtarilabilir']['n'] + t1['kurtarilamaz']['n'])} hücre bozuldu ve her
bozma kaydedildi.</p>
<p>Temizlenen veri saklanan temiz halle karşılaştırıldı. Bu yüzden "iyi görünüyor" demek yerine her hata türü için
kesin bir oran verebiliyorum.</p>
{cubuk_grafik('Hangi hata ne kadar düzeldi?', 'Doğru düzeltilen bozuk hücre oranı · satır hatalarında kurtarılan satır oranı')}
<h2>Gerçek örnekler</h2>
<div class="ornekler">
{grup('✓', 'var(--iyi)', 'Düzeltti')}
{ornek('dogum_tarihi', '24-Oct-1959', '1959-10-24', 'temiz')}
{ornek('soyad', 'YÄ±ldÄ±z', 'Yıldız', 'temiz')}
{ornek('ad', 'Ay?e', 'Ayşe', 'temiz')}
{ornek('birim_fiyat', '₺4,851.99', '4851.99', 'temiz')}
{ornek('eposta', 'orhan.isikgmail.com', 'orhan.isik@gmail.com', 'temiz')}
{ornek('adet', '-3', '3  (toplamdan doğrulandı)', 'temiz')}
{grup('–', 'var(--soluk)', 'Uydurmadı', 'gerçek değer bilinemez, boş bırakmak doğru davranış')}
{ornek('siparis_tarihi', '2036-01-11', 'boş bıraktı', 'bos')}
{grup('✗', 'var(--kotu)', 'Yapamadı')}
{ornek('kargo_firmasi', 'TEX', 'boş', 'bos', 'Trendyol Express')}
{ornek('odeme_yontemi', 'Papara', 'boş', 'bos', 'Dijital Cüzdan')}
{ornek('dogum_tarihi', '06/01/1967', '1967-01-06', 'yanlis', '1967-06-01')}
</div>
<h2>Kural nerede takıldı?</h2>
<ul>
<li><b>Sözlükte olmayan kısaltmalar:</b> <code>TEX</code>, <code>YK</code>, <code>Papara</code>, <code>Tamamlandı</code>.
Yazım tutarsızlığında doğruluk {y(t1['bozma_turu']['B8']['dogru'])}. Kalanı boş kaldı.</li>
<li><b>Gün/ay sırası belirsiz tarihler:</b> <code>06/01/1967</code> 6 Ocak mı, 1 Haziran mı? Kural Türkiye biçimini
varsaydı, kaynak ay/gün yazdıysa yanıldı.</li>
<li><b>Kanıtı zayıf müşteri çiftleri:</b> {t1['tekrar']['gercek_cift']} tekrar çiftinden {t1['tekrar']['dogru_cift']}
tanesi bulundu, hiç yanlış eşleşme yapılmadı.</li>
</ul>
<p>Kural bilmediği bir değerle karşılaşınca tahmin etmedi, boş bıraktı. Gerçeği bilinemeyen
{sayi(t1['kurtarilamaz']['n'])} hücrenin {y(t1['kurtarilamaz']['bos'])} kadarını boş bıraktı.</p>
<div class="not"><b>Dürüst olayım:</b> Bozmaları da kuralları da ben yazdım. Kural hangi hatayla karşılaşacağını önceden
biliyordu. Gerçek hayatta böyle olmaz. Bu yüzden 2. bölümde kodu dondurup kurallara hiç görmedikleri hatalar verdim.</div>
<a class="sonraki" href="/bolum-2"><span>Sonraki bölüm</span><b>Aynı kurallar, görmediği hatalar: {y(t1['genel_dogruluk'])} → {y(t2['genel_dogruluk'])} →</b></a>"""
    sayfa("bolum-1.html", f"LLM olmadan kirli veri temizliği: {y(t1['genel_dogruluk'])} doğru · Kirli Veri Deneyi 1",
          f"10.000 siparişlik kirli e-ticaret verisini LLM kullanmadan temizledim: {y(t1['genel_dogruluk'])} doğru "
          f"düzeltme, {t1['uydurma']['n']} uydurma, 8 saniye.", "og-bolum1.png", govde, "b1")


CR_NOTU = "gizli \\r satırı ikiye böldü"


def bolum2():
    b13, b10, b3 = (t2["bozma_turu"][b]["dogru"] for b in ("B13", "B10", "B3"))
    govde = f"""
<p class="ust">Kirli veri deneyi · 2. bölüm</p>
<h1>Kurallarım {y(t1['genel_dogruluk'])} yaptı. Görmediği hatalarla test edince ne oldu?</h1>
<p class="giris">Aynı veri, aynı kod, yeni hata biçimleri. Kod <code>{DONDURULAN_COMMIT}</code> commit'inde donduruldu,
tek satırına dokunulmadı.</p>
{kpi([(f"{y(t1['genel_dogruluk'])} → {y(t2['genel_dogruluk'])}", 'bozuk hücrelerde doğru düzeltme'),
      (f"{t1['uydurma']['n']} → {t2['uydurma']['n']}", 'uydurma'),
      (f"0 → {kayip}", 'kaybolan sipariş'),
      ('0', 'değişen kod satırı')])}
<h2>Neden bu test?</h2>
<p>1. bölümde kurallar {y(t1['genel_dogruluk'])} yaptı. Ama hataları da kuralları da aynı kişi yazdı. Gerçek hayatta
veri, kural yazılırken hiç görülmemiş biçimlerle gelir. Bu yüzden aynı temiz veriyi aynı 15 hata türüyle ama yeni
yazımlarla yeniden bozdum: <code>27 Şubat 1987 Cuma</code>, Unix zamanı, Excel tarih numarası,
<code>ayse[at]gmail.com</code>, <code>MUS-00211</code>, <code>81 TL 62 kr</code>, HTML karakter kodları, sekmeyle
ayrılmış satırlar, görünmez <code>\\r</code> karakteri. Hepsinin gerçek değeri kirli metinden kesin olarak
çıkarılabiliyor.</p>
{dumbbell('Hangi hata türünde ne kadar düştü?', 'Doğru düzeltme oranı · üzerine gel ya da dokun')}
<h2>Gerçek örnekler</h2>
<div class="ornekler">
{grup('✓', 'var(--iyi)', 'Hâlâ düzeltti')}
{ornek('kargo_firmasi', 'Yurtici Krg', 'Yurtiçi Kargo', 'temiz')}
{ornek('durum', 'Delivered', 'Teslim Edildi', 'temiz')}
{ornek('birim_fiyat', '81 TL 62 kr', '81.62', 'temiz')}
{grup('–', 'var(--soluk)', 'Sessizce boş bıraktı', 'gerçek değer belliydi')}
{ornek('dogum_tarihi', '27 Şubat 1987 Cuma', 'boş', 'bos', '1987-02-27')}
{ornek('dogum_tarihi', '1105920000', 'boş', 'bos', '2005-01-17 (Unix zamanı)')}
{ornek('musteri_id', 'MUS-00211', 'boş', 'bos', 'M00211')}
{ornek('kargo_firmasi', 'TY Express', 'boş', 'bos', 'Trendyol Express')}
{grup('✗', 'var(--kotu)', 'Güvenle yanlış yazdı')}
{ornek('ad', 'Ya&#287;mur', 'Ya&#287;mur', 'yanlis', 'Yağmur')}
{ornek('ad', 'Ã…Å¾eyma', 'Åžeyma', 'yanlis', 'Şeyma')}
{grup('!', 'var(--yazi)', 'Satırı kaybetti', f'toplam {kayip} sipariş')}
{ornek('satır', 'S000015⇥M01692⇥U0206⇥…', 'satır kayboldu', 'kayip', 'sekmeyle ayrılmış satır')}
{ornek('durum', 'Teslim Edildi␍', 'satır kayboldu', 'kayip', CR_NOTU)}
</div>
<h2>Dersler</h2>
<ol>
<li><b>Kurallar bilinen dünyada çok iyi, yeni biçimde kırılgan.</b> En sert düşüşler ID biçimi (%100 → {y(b13)}),
e-posta (%100 → {y(b10)}) ve tarihlerde (→ {y(b3)}) oldu.</li>
<li><b>Kırılma çoğunlukla sessiz.</b> Kurtarılabilir hücrelerde boş kalma oranı {y(t2['kurtarilabilir']['bos'])}. Kod ne
hata verdi ne de uyardı. İzlenmezse temiz görünen ama delik deşik bir tablo çıkar.</li>
<li><b>Bazen güvenle yanlış yazıyor.</b> Uydurma sayısı {t1['uydurma']['n']} → {t2['uydurma']['n']}. Çift bozulmuş
<code>Ã…Å¾eyma</code> yarım onarılıp <code>Åžeyma</code> oldu.</li>
<li><b>Tek bir görünmez karakter veri kaybettirir.</b> Hücre sonundaki <code>\\r</code> satırları ikiye böldü. Sekme ve
<code>|</code> ayraçlı satırlarla birlikte {kayip} sipariş tamamen kayboldu.</li>
<li><b>Genel kurallar dayandı, özel kurallar kırıldı.</b> Önek eşleşmesi (<code>Yurtici Krg</code>) ve sadece rakam
ayıklayan telefon kuralı yeni biçimlerde de çalıştı.</li>
</ol>
<h3>Pratik sonuç</h3>
<p>Kural tabanlı bir veri hattında doğruluk kadar <b>boş hücre oranını, karantinaya düşen satır sayısını ve satır
sayısı farkını</b> da izleyin. Bu üç sayı sessiz kırılmanın ilk işareti.</p>
<div class="not"><b>Dürüstlük notu:</b> Yeni biçimleri de ben seçtim ve kural kodunu biliyordum. Bu bir stres testi.
Gerçek bir veri kaynağındaki düşüş daha az ya da daha fazla olabilir.</div>
<h2>Sen de dene</h2>
<p>Yöntemini iki veri setinde de çalıştır. Bilinen hatalarda da görmediği hatalarda da iyiyse gerçekten genelleşiyor
demektir.</p>
<pre># 1. bölüm: bilinen hatalar
veri-temizle puanla benim_ciktim/
# 2. bölüm: görmediği hatalar
veri-temizle puanla benim_ciktim2/ --gercek veri_seti_surpriz/gercek</pre>
<a class="sonraki" href="/bolum-1"><span>Önceki bölüm</span><b>← Kurallar bilinen hatalarda: {y(t1['genel_dogruluk'])} doğru düzeltme</b></a>"""
    sayfa("bolum-2.html", f"Aynı kurallar, görmediği hatalar: {y(t1['genel_dogruluk'])} → {y(t2['genel_dogruluk'])} · Kirli Veri Deneyi 2",
          f"Kodu dondurdum ve kurallara hiç görmedikleri hata biçimleri verdim. Doğruluk {y(t1['genel_dogruluk'])} → "
          f"{y(t2['genel_dogruluk'])}, {kayip} sipariş kayboldu.", "og-bolum2.png", govde, "b2")


# --- Önizleme görselleri (1200x630) ---------------------------------------------------------------------------

OG_CSS = """*{box-sizing:border-box;margin:0}body{width:1200px;height:630px;background:#fcfcfb;color:#0b0b0b;
font-family:"Inter","Liberation Sans",sans-serif;padding:64px 72px;display:flex;flex-direction:column}
.ust{font-size:22px;text-transform:uppercase;letter-spacing:.08em;color:#8a887f}
h1{font-size:58px;line-height:1.08;letter-spacing:-.02em;margin:18px 0 0;max-width:1000px}
.alt{margin-top:auto;display:flex;align-items:flex-end;justify-content:space-between}
.buyuk{font-size:96px;font-weight:700;letter-spacing:-.03em;color:#2a78d6;line-height:1}
.kucuk{font-size:24px;color:#52514e;margin-top:8px}.site{font-size:22px;color:#8a887f;text-align:right}"""


def og(dosya: str, ust: str, baslik: str, buyuk: str, kucuk: str):
    metin = (f"<!doctype html><html lang='tr'><head><meta charset='utf-8'><link rel='stylesheet' "
             f"href='https://fonts.googleapis.com/css2?family=Inter:wght@500;700&display=block'><style>{OG_CSS}</style>"
             f"</head><body><div class='ust'>{e(ust)}</div><h1>{e(baslik)}</h1><div class='alt'><div>"
             f"<div class='buyuk'>{e(buyuk)}</div><div class='kucuk'>{e(kucuk)}</div></div>"
             "<div class='site'>Açık veri seti<br>kod ve ölçüm</div></div></body></html>")
    with tempfile.TemporaryDirectory() as gecici:
        yol = Path(gecici) / "og.html"
        yol.write_text(metin, encoding="utf-8")
        subprocess.run([tarayici_bul(), "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                        "--window-size=1200,800", "--virtual-time-budget=5000",
                        f"--screenshot={SITE / dosya}", f"file://{yol}"], check=True, capture_output=True)
    # Başsız pencerede görünür alan pencereden kısa kalıyor: büyük çekip tam 1200x630'a kırpılır.
    from PIL import Image
    with Image.open(SITE / dosya) as resim:
        resim.crop((0, 0, 1200, 630)).save(SITE / dosya)


SITE.mkdir(exist_ok=True)
(SITE / "stil.css").write_text(CSS.strip() + "\n", encoding="utf-8")
(SITE / "grafik.js").write_text(JS.strip() + "\n", encoding="utf-8")
# Netlify: kısa adresler (/bolum-1) .html dosyalarına yönlenir.
(SITE / "_redirects").write_text("/bolum-1  /bolum-1.html  200\n/bolum-2  /bolum-2.html  200\n", encoding="utf-8")
ana_sayfa()
bolum1()
bolum2()
og("og-ana.png", "Kirli veri deneyi", "Kirli veriyi kurallarla temizledim, sonra görmedikleri hataları verdim",
   f"{y(t1['genel_dogruluk'])} → {y(t2['genel_dogruluk'])}", "aynı kod, iki bölüm")
og("og-bolum1.png", "Kirli veri deneyi · 1. bölüm", "LLM olmadan, sadece kurallarla kirli veri temizliği",
   y(t1["genel_dogruluk"]), f"doğru düzeltme · {t1['uydurma']['n']} uydurma · 8 saniye · $0")
og("og-bolum2.png", "Kirli veri deneyi · 2. bölüm", "Aynı kurallar, görmediği hatalar",
   f"{y(t1['genel_dogruluk'])} → {y(t2['genel_dogruluk'])}", f"kod değişmedi · {kayip} sipariş kayboldu")
print(SITE)
