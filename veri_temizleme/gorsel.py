"""Paylaşım görselleri: sonuclar.json'dan bozma türü tablosu (PNG). Chromium ile ekran görüntüsü alınır."""

from __future__ import annotations

import html
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .rapor import YONTEM_ADLARI
from .uretici.bozma import BOZMA_ADLARI

KISA_ADLAR = {**BOZMA_ADLARI, "B2": "Tekrarlanan sipariş", "B5": "Eksik değer", "B6": "Sayı ve para formatı",
              "B7": "Geçersiz değer", "B11": "Boşluk / görünmez karakter", "B14": "Kaymış / bozuk satır"}

FONT = "<link rel='stylesheet' href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=block'>"

CSS = """
*{box-sizing:border-box;margin:0}body{width:1200px;background:#faf8f3;color:#1c1b19;
font-family:"Inter","Liberation Sans","DejaVu Sans",sans-serif;padding:64px 64px 48px}
h1{font-size:42px;line-height:1.15;letter-spacing:-.01em;font-weight:700}
.alt{font-size:22px;color:#6d6a63;margin:14px 0 36px}
.satir{display:grid;align-items:center;gap:20px;padding:11px 0;border-bottom:1px solid #e7e3da}
.satir.baslik{border-bottom:2px solid #1c1b19;padding:0 0 10px;font-size:16px;color:#6d6a63;font-weight:600;
text-transform:uppercase;letter-spacing:.04em}
.ad{font-size:22px;font-weight:560}.kod{color:#9a968d;font-weight:500;font-size:17px;margin-left:6px}
.n{font-size:18px;color:#6d6a63;text-align:right;font-variant-numeric:tabular-nums}
.bar{display:grid;grid-template-columns:1fr 78px;align-items:center;gap:12px}
.bar s{display:block;position:relative;height:26px;background:#ece8df;border-radius:6px;overflow:hidden}
.bar i{position:absolute;inset:0 auto 0 0;border-radius:6px}
.bar b{font-size:20px;text-align:right;font-variant-numeric:tabular-nums}
.iyi i{background:#2f8a5b}.orta i{background:#d59a2c}.kotu i{background:#c44b3f}
.alt-bilgi{display:flex;gap:44px;margin-top:34px}.kutu .d{font-size:40px;font-weight:750;letter-spacing:-.02em}
.kutu .e{font-size:17px;color:#6d6a63;margin-top:2px}
.kaynak{margin-top:34px;font-size:17px;color:#6d6a63;display:flex;justify-content:space-between}
"""


def _yuzde(v: float) -> str:
    if v >= 1:
        return "%100"
    metin = f"{v * 100:.1f}"
    return "%" + (metin[:-2] if metin.endswith(".0") else metin.replace(".", ","))


def _sayi(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def tablo_html(sonuclar: dict, baslik: str | None = None) -> str:
    calisan = {y: v for y, v in sonuclar["yontemler"].items() if "atlandi" not in v}
    kapsam = "tam" if all(v.get("tam") for v in calisan.values()) else "orneklem"
    turler = {}
    for v in calisan.values():
        o = v[kapsam]
        for b, d in o["bozma_turu"].items():
            turler.setdefault(b, {"n": d["n"]})[id(v)] = d["dogru"]
        for b, d in o["satir_bozmalari"].items():
            turler.setdefault(b, {"n": d["n"]})[id(v)] = d["basari"]
    sirali = sorted(turler, key=lambda b: (min(turler[b][id(v)] for v in calisan.values()), -turler[b]["n"]))
    kolon = f"minmax(0,1.25fr) 90px {' '.join(['minmax(0,1fr)'] * len(calisan))}"
    satirlar = [f"<div class='satir baslik' style='grid-template-columns:{kolon}'><div>Hata türü</div>"
                f"<div class='n'>Hücre</div>" + "".join(f"<div>{YONTEM_ADLARI[y]}</div>" for y in calisan) + "</div>"]
    for b in sirali:
        cubuklar = ""
        for v in calisan.values():
            oran = turler[b][id(v)]
            sinif = "iyi" if oran >= 0.97 else "orta" if oran >= 0.85 else "kotu"
            cubuklar += f"<div class='bar {sinif}'><s><i style='width:{oran * 100:.1f}%'></i></s><b>{_yuzde(oran)}</b></div>"
        satirlar.append(f"<div class='satir' style='grid-template-columns:{kolon}'><div class='ad'>"
                        f"{html.escape(KISA_ADLAR[b])}<span class='kod'>{b}</span></div>"
                        f"<div class='n'>{_sayi(turler[b]['n'])}</div>{cubuklar}</div>")
    ilk = next(iter(calisan.values()))[kapsam]
    kutular = ""
    if len(calisan) == 1:
        v = next(iter(calisan.values()))
        llm = v.get("llm") or {}
        kutular = "<div class='alt-bilgi'>" + "".join(
            f"<div class='kutu'><div class='d'>{d}</div><div class='e'>{e}</div></div>" for d, e in [
                (_yuzde(ilk["genel_dogruluk"]), "genel doğru düzeltme"),
                (_yuzde(ilk["uydurma"]["oran"]), "uydurma"),
                (f"{v['sure']:.0f} sn", "süre"),
                (f"${llm.get('maliyet', 0):.0f}", "maliyet")]) + "</div>"
    satir_sayisi = ilk["satirlar"]["siparisler"]["gercek_satir"]
    baslik = baslik or ("LLM olmadan, sadece kurallarla: hangi hata ne kadar düzeldi?" if len(calisan) == 1
                        else "Kirli veri temizleme: kural, LLM ve hibrit")
    return (f"<!doctype html><html lang='tr'><head><meta charset='utf-8'><style>{CSS}</style></head><body>"
            f"{FONT}<h1>{html.escape(baslik)}</h1><p class='alt'>{_sayi(satir_sayisi)} sipariş" +
            " · 15 bozma türü · doğru düzeltilen bozuk hücre oranı</p>" + "".join(satirlar) + kutular +
            "<div class='kaynak'><span>Sentetik veri, seed 42</span>"
            "<span>github.com/sefa05/Claude-veri-temizleme-</span></div></body></html>")


def tarayici_bul() -> str:
    tarayici = shutil.which("chromium") or shutil.which("google-chrome") or next(
        (str(p) for p in Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome")), None)
    if not tarayici:
        raise RuntimeError("Chromium bulunamadı")
    return tarayici


def ekran_goruntusu(html_metni: str, cikti: Path, genislik: int = 1200) -> Path:
    tarayici = tarayici_bul()
    with tempfile.TemporaryDirectory() as gecici:
        sayfa = Path(gecici) / "sayfa.html"
        sayfa.write_text(html_metni, encoding="utf-8")
        # Önce sayfa yüksekliği ölçülür, sonra tam boyda çekilir.
        yukseklik = _yukseklik_olc(tarayici, sayfa, genislik)
        subprocess.run([tarayici, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={genislik},{yukseklik}",
                        "--virtual-time-budget=5000",
                        f"--screenshot={Path(cikti).resolve()}", f"file://{sayfa}"],
                       capture_output=True, check=True)
    return Path(cikti)


def _yukseklik_olc(tarayici: str, sayfa: Path, genislik: int) -> int:
    olcum = sayfa.with_name("olcum.html")
    olcum.write_text(sayfa.read_text(encoding="utf-8").replace(
        "</body>", "<script>document.title=document.body.scrollHeight</script></body>"), encoding="utf-8")
    dom = subprocess.run([tarayici, "--headless", "--no-sandbox", "--disable-gpu", "--dump-dom",
                          f"--window-size={genislik},800", "--virtual-time-budget=5000", f"file://{olcum}"], capture_output=True, text=True).stdout
    try:
        return int(dom.split("<title>")[1].split("</title>")[0]) + 140  # Headless pencere yüksekliği sayfadan kısa kalıyor.
    except (IndexError, ValueError):
        return 1500


def tablo_gorseli(klasor: Path, cikti: Path) -> Path:
    sonuclar = json.loads((Path(klasor) / "sonuclar.json").read_text(encoding="utf-8"))
    return ekran_goruntusu(tablo_html(sonuclar), cikti)
