"""Tek X gönderisi için iki görsel (7:8, yan yana kırpılmadan görünür): 1. ve 2. bölümün özeti.

Rakamlar ornek_sonuc/ altındaki sonuç dosyalarından okunur. Çalıştırma: python belgeler/x_gorselleri.py
"""

import html
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from veri_temizleme.gorsel import tarayici_bul

KOK = Path(__file__).resolve().parent.parent
SITE_ADI = "veritemizleme.netlify.app"
GENISLIK, YUKSEKLIK = 1200, 1372  # 7:8

b1 = json.loads((KOK / "ornek_sonuc" / "sonuclar.json").read_text(encoding="utf-8"))["yontemler"]["kural"]
b2 = json.loads((KOK / "ornek_sonuc" / "bolum2" / "sonuclar.json").read_text(encoding="utf-8"))["yontemler"]["kural"]
t1, t2 = b1["tam"], b2["tam"]
kayip = t2["satirlar"]["siparisler"]["gercek_satir"] - t2["satirlar"]["siparisler"]["bulunan_satir"]
e = html.escape

AD = {"B1": "Tekrarlanan müşteri", "B2": "Tekrarlanan sipariş", "B3": "Tarih biçimi", "B4": "Türkçe karakter",
      "B5": "Eksik değer", "B6": "Para biçimi", "B7": "Geçersiz değer", "B8": "Kısaltma ve yazım", "B9": "Telefon",
      "B10": "E-posta", "B11": "Görünmez karakter", "B12": "Tutarsız toplam", "B13": "ID biçimi",
      "B14": "Bozuk satır", "B15": "Birim ve tip"}


def y(v: float) -> str:
    if v >= 0.9995:
        return "%100"
    m = f"{v * 100:.1f}"
    return "%" + (m[:-2] if m.endswith(".0") else m.replace(".", ","))


def oranlar(t: dict) -> dict[str, float]:
    d = {b: v["dogru"] for b, v in t["bozma_turu"].items()}
    d.update({b: v["basari"] for b, v in t["satir_bozmalari"].items()})
    return d


O1, O2 = oranlar(t1), oranlar(t2)

CSS = f"""*{{box-sizing:border-box;margin:0}}
body{{width:{GENISLIK}px;height:{YUKSEKLIK}px;background:#fcfcfb;color:#0b0b0b;padding:76px 80px 64px;
font-family:"Inter","Liberation Sans",sans-serif;display:flex;flex-direction:column}}
.ust{{font-size:24px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:#2a78d6}}
h1{{font-size:56px;line-height:1.1;letter-spacing:-.02em;margin:18px 0 0}}
.buyuk{{font-size:150px;font-weight:700;letter-spacing:-.04em;line-height:1;margin-top:44px;color:#0b0b0b}}
.buyuk span{{color:#8a887f;font-weight:500}}
.aciklama{{font-size:28px;color:#52514e;margin-top:10px}}
.kpi{{display:flex;gap:14px;margin-top:40px}}
.kpi div{{flex:1;border:2px solid #e6e4dd;border-radius:16px;padding:18px 22px}}
.kpi b{{display:block;font-size:40px;letter-spacing:-.02em;line-height:1.1}}
.kpi span{{font-size:21px;color:#52514e}}
.liste{{margin-top:44px}}
.baslik{{font-size:21px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#8a887f;margin-bottom:6px;
display:flex;justify-content:space-between}}
.sira{{display:grid;grid-template-columns:300px 1fr 130px;align-items:center;gap:22px;padding:13px 0;
border-top:2px solid #efede7}}
.ad{{font-size:27px}}.d{{font-size:27px;font-weight:650;text-align:right;font-variant-numeric:tabular-nums}}
.iz{{position:relative;height:26px}}
.iz::before{{content:"";position:absolute;left:0;right:0;top:11px;height:4px;background:#efede7;border-radius:2px}}
.cubuk{{position:absolute;left:0;top:3px;height:20px;background:#2a78d6;border-radius:0 5px 5px 0}}
.cizgi{{position:absolute;top:11px;height:4px;background:#a9c8ef}}
.nokta{{position:absolute;top:1px;width:24px;height:24px;margin-left:-12px;border-radius:50%;border:3px solid #fcfcfb}}
.once{{background:#a9c8ef}}.sonra{{background:#2a78d6}}
.alt{{margin-top:auto;display:flex;justify-content:space-between;font-size:24px;color:#8a887f}}
.alt b{{color:#0b0b0b;font-weight:600}}"""


def gorsel(dosya: str, govde: str):
    metin = (f"<!doctype html><html lang='tr'><head><meta charset='utf-8'><link rel='stylesheet' "
             f"href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=block'>"
             f"<style>{CSS}</style></head><body>{govde}<div class='alt'><span>Sentetik veri · açık veri seti</span>"
             f"<b>{SITE_ADI}</b></div></body></html>")
    cikti = KOK / "gorseller" / dosya
    with tempfile.TemporaryDirectory() as gecici:
        yol = Path(gecici) / "x.html"
        yol.write_text(metin, encoding="utf-8")
        # Başsız pencerede görünür alan kısa kalıyor: büyük çekilip tam boyuta kırpılır.
        subprocess.run([tarayici_bul(), "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={GENISLIK},{YUKSEKLIK + 200}",
                        "--virtual-time-budget=5000", f"--screenshot={cikti}", f"file://{yol}"],
                       check=True, capture_output=True)
    with Image.open(cikti) as resim:
        resim.crop((0, 0, GENISLIK * 2, YUKSEKLIK * 2)).save(cikti)
    return cikti


# 1. görsel: bilinen hatalar. En zayıf dört tür ve kalanların en düşüğü.
sirali1 = sorted(O1, key=O1.get)
satirlar1 = "".join(
    f"<div class='sira'><div class='ad'>{e(AD[b])}</div><div class='iz'><div class='cubuk' "
    f"style='width:{O1[b] * 100:.2f}%'></div></div><div class='d'>{y(O1[b])}</div></div>" for b in sirali1[:4])
kalan = sirali1[4:]
satirlar1 += (f"<div class='sira'><div class='ad'>Diğer {len(kalan)} tür</div><div class='iz'><div class='cubuk' "
              f"style='width:{min(O1[b] for b in kalan) * 100:.2f}%'></div></div>"
              f"<div class='d'>{y(min(O1[b] for b in kalan))}+</div></div>")
gorsel("x_1_bilinen_hatalar.png", f"""
<div class="ust">1. bölüm · bilinen hatalar</div>
<h1>10.000 satır kirli veri,<br>LLM yok, sadece kurallar</h1>
<div class="buyuk">{y(t1['genel_dogruluk'])}</div>
<div class="aciklama">bozuk hücreler doğru düzeltildi</div>
<div class="kpi"><div><b>{t1['uydurma']['n']}</b><span>uydurma</span></div>
<div><b>{b1['sure']:.0f} sn</b><span>süre</span></div><div><b>$0</b><span>maliyet</span></div></div>
<div class="liste"><div class="baslik"><span>En çok zorlandığı yerler</span><span>doğru</span></div>{satirlar1}</div>""")

# 2. görsel: görmediği hatalar. En sert düşen beş tür, önce → sonra.
sirali2 = sorted(O2, key=O2.get)[:5]
satirlar2 = ""
for b in sirali2:
    once, sonra = O1[b], O2[b]
    satirlar2 += (f"<div class='sira'><div class='ad'>{e(AD[b])}</div><div class='iz'><div class='cizgi' "
                  f"style='left:{sonra * 100:.2f}%;width:{(once - sonra) * 100:.2f}%'></div>"
                  f"<div class='nokta once' style='left:{once * 100:.2f}%'></div>"
                  f"<div class='nokta sonra' style='left:{sonra * 100:.2f}%'></div></div>"
                  f"<div class='d'>{y(sonra)}</div></div>")
gorsel("x_2_gormedigi_hatalar.png", f"""
<div class="ust">2. bölüm · görmediği hatalar</div>
<h1>Aynı kod, tek satır değişmedi.<br>Sadece hataların biçimi değişti.</h1>
<div class="buyuk">{y(t2['genel_dogruluk'])} <span>← {y(t1['genel_dogruluk'])}</span></div>
<div class="aciklama">bozuk hücreler doğru düzeltildi</div>
<div class="kpi"><div><b>{t2['uydurma']['n']}</b><span>uydurma (önce {t1['uydurma']['n']})</span></div>
<div><b>{kayip}</b><span>sipariş kayboldu</span></div>
<div><b>{y(t2['kurtarilabilir']['bos'])}</b><span>sessizce boş kaldı</span></div></div>
<div class="liste"><div class="baslik"><span>En sert düşüşler · <span style="color:#a9c8ef">●</span> önce
<span style="color:#2a78d6">●</span> sonra</span><span>sonra</span></div>{satirlar2}</div>""")
print("tamam")
