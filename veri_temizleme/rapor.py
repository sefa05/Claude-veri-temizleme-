"""Tek dosyalık Türkçe HTML rapor: yöntem karşılaştırması, bozma türü tablosu, örnek hatalar."""

from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd

from .uretici.bozma import BOZMA_ADLARI

YONTEM_ADLARI = {"kural": "Kural", "hibrit": "Hibrit (kural + LLM)", "llm": "Sadece LLM"}

CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--soluk:#6b6a66;--cizgi:#e4e1d9;--kart:#fff;--iyi:#1f7a4d;--orta:#b7791f;
--kotu:#b83232;--vurgu:#3553a8}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#161615;--fg:#ecebe7;--soluk:#a3a19b;
--cizgi:#34332f;--kart:#1f1f1d;--iyi:#5cc28f;--orta:#e0a84c;--kotu:#ec7272;--vurgu:#8ea6f0}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1100px;margin:0 auto;padding:32px 16px 64px}h1{font-size:28px;margin:0 0 4px}
h2{font-size:19px;margin:40px 0 12px}.alt{color:var(--soluk);margin:0 0 24px}
.kartlar{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.kart{min-width:0;overflow-wrap:anywhere;background:var(--kart);border:1px solid var(--cizgi);border-radius:10px;padding:14px 16px}
.kart h3{margin:0 0 8px;font-size:15px}.buyuk{font-size:30px;font-weight:650;font-variant-numeric:tabular-nums}
.kart dl{display:grid;grid-template-columns:1fr auto;gap:2px 12px;margin:8px 0 0;font-size:13.5px}
.kart dt{color:var(--soluk)}.kart dd{margin:0;text-align:right;font-variant-numeric:tabular-nums}
.tablo{overflow-x:auto;border:1px solid var(--cizgi);border-radius:10px;background:var(--kart)}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{padding:7px 10px;border-bottom:1px solid var(--cizgi);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}th{color:var(--soluk);font-weight:600}
tr:last-child td{border-bottom:none}td.iyi{color:var(--iyi)}td.orta{color:var(--orta)}td.kotu{color:var(--kotu)}
td.kod{font-family:ui-monospace,monospace;font-size:12.5px;text-align:left;white-space:normal;word-break:break-all}
.not{color:var(--soluk);font-size:13.5px}.not li{margin:4px 0}.atlandi{color:var(--soluk);font-style:italic}
"""


def _yuzde(v, basamak=1):
    return "–" if v is None else f"%{v * 100:.{basamak}f}".replace(".", ",")


def _sayi(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _sinif(v, iyi=0.97, orta=0.85):
    return "" if v is None else ("iyi" if v >= iyi else "orta" if v >= orta else "kotu")


def _e(s) -> str:
    return html.escape("" if s is None or (isinstance(s, float) and s != s) else str(s))


def rapor_uret(klasor: Path) -> Path:
    klasor = Path(klasor)
    sonuc = json.loads((klasor / "sonuclar.json").read_text(encoding="utf-8"))
    ayar = sonuc["ayarlar"]
    yontemler = {y: v for y, v in sonuc["yontemler"].items()}
    calisan = {y: v for y, v in yontemler.items() if "atlandi" not in v}
    parcalar = [f"<h1>Kirli veri temizleme: kural mı, LLM mi, hibrit mi?</h1>"
                f"<p class='alt'>Model: {_e(ayar['model'])} (effort: {_e(ayar['effort'])}) · Karşılaştırma kapsamı: "
                f"tüm müşteri ve ürünler + {_sayi(ayar['orneklem'])} siparişlik örneklem · seed {ayar['seed']}</p>"]

    # Özet kartları.
    kartlar = []
    for y, v in yontemler.items():
        if "atlandi" in v:
            kartlar.append(f"<div class='kart'><h3>{YONTEM_ADLARI[y]}</h3><p class='atlandi'>Çalıştırılmadı: "
                           f"{_e(v['atlandi'])}</p></div>")
            continue
        o = v["orneklem"]
        llm = v.get("llm") or {}
        kartlar.append(
            f"<div class='kart'><h3>{YONTEM_ADLARI[y]}</h3><div class='buyuk'>{_yuzde(o['genel_dogruluk'])}</div>"
            f"<div class='not'>kurtarılabilir bozuk hücrelerde doğru düzeltme</div><dl>"
            f"<dt>Uydurma</dt><dd>{o['uydurma']['n']} / {o['uydurma']['payda']}</dd>"
            f"<dt>Temiz hücreyi bozma</dt><dd>{_yuzde(1 - o['temiz_hucreler']['dogru'], 2)}</dd>"
            f"<dt>Müşteri eşleştirme F1</dt><dd>{o['tekrar']['f1']:.3f}</dd>"
            f"<dt>Maliyet</dt><dd>${llm.get('maliyet', 0):.2f}</dd>"
            f"<dt>Süre</dt><dd>{v['sure']:.0f} sn</dd>"
            f"<dt>LLM çağrısı</dt><dd>{llm.get('cagri', 0)}</dd></dl></div>")
    parcalar.append("<div class='kartlar'>" + "".join(kartlar) + "</div>")

    # Bozma türü tablosu.
    if calisan:
        satirlar = []
        turler = sorted({b for v in calisan.values() for b in v["orneklem"]["bozma_turu"]}, key=lambda b: int(b[1:]))
        for b in turler:
            hucreler = [f"<td>{BOZMA_ADLARI.get(b, b)} <span class='not'>({b})</span></td>"]
            n = next(v["orneklem"]["bozma_turu"][b]["n"] for v in calisan.values() if b in v["orneklem"]["bozma_turu"])
            hucreler.append(f"<td>{_sayi(n)}</td>")
            for v in calisan.values():
                d = v["orneklem"]["bozma_turu"].get(b)
                oran = d["dogru"] if d else None
                hucreler.append(f"<td class='{_sinif(oran)}'>{_yuzde(oran)}</td>")
            satirlar.append("<tr>" + "".join(hucreler) + "</tr>")
        for b in ("B2", "B14"):
            hucreler = [f"<td>{BOZMA_ADLARI[b]} <span class='not'>({b})</span></td>"]
            hucreler.append(f"<td>{next(iter(calisan.values()))['orneklem']['satir_bozmalari'][b]['n']}</td>")
            for v in calisan.values():
                oran = v["orneklem"]["satir_bozmalari"][b]["basari"]
                hucreler.append(f"<td class='{_sinif(oran)}'>{_yuzde(oran)}</td>")
            satirlar.append("<tr>" + "".join(hucreler) + "</tr>")
        baslik = "".join(f"<th>{YONTEM_ADLARI[y]}</th>" for y in calisan)
        parcalar.append("<h2>Bozma türüne göre doğru düzeltme oranı</h2><div class='tablo'><table><thead><tr>"
                        f"<th>Bozma</th><th>Hücre</th>{baslik}</tr></thead><tbody>{''.join(satirlar)}</tbody>"
                        "</table></div><p class='not'>B2 ve B14 satır bazlıdır: tekrar satırın silinme ve bozuk "
                        "satırın kurtarılma oranı.</p>")

        # Kurtarılamaz hücreler.
        satirlar = []
        for y, v in calisan.items():
            k = v["orneklem"]["kurtarilamaz"]
            satirlar.append(f"<tr><td>{YONTEM_ADLARI[y]}</td><td>{_sayi(k['n'])}</td>"
                            f"<td class='{_sinif(k['bos'], 0.95, 0.8)}'>{_yuzde(k['bos'])}</td>"
                            f"<td class='{'kotu' if k['yanlis'] > 0.02 else ''}'>{_yuzde(k['yanlis'])}</td>"
                            f"<td>{_yuzde(k['dogru'])}</td></tr>")
        parcalar.append(
            "<h2>Kurtarılamaz hücrelerde davranış</h2><p class='not'>Gerçek değer kirli veriden çıkarılamıyor "
            "(ör. silinmiş telefon, 2038 yılında sipariş). Doğru davranış hücreyi boş bırakmaktır.</p>"
            "<div class='tablo'><table><thead><tr><th>Yöntem</th><th>Hücre</th><th>Boş bıraktı</th>"
            "<th>Uydurdu</th><th>Tahmini tuttu</th></tr></thead><tbody>" + "".join(satirlar) +
            "</tbody></table></div>")

        # Sütun bazlı.
        sutunlar = sorted({s for v in calisan.values() for s in v["orneklem"]["sutun"]})
        satirlar = []
        for s in sutunlar:
            hucreler = [f"<td>{s}</td>"]
            for v in calisan.values():
                d = v["orneklem"]["sutun"].get(s)
                oran = d["dogru"] if d else None
                hucreler.append(f"<td class='{_sinif(oran, 0.99, 0.95)}'>{_yuzde(oran, 2)}</td>")
            satirlar.append("<tr>" + "".join(hucreler) + "</tr>")
        parcalar.append("<h2>Sütun bazlı hücre doğruluğu</h2><p class='not'>Bozuk ve temiz tüm hücreler dahil.</p>"
                        f"<div class='tablo'><table><thead><tr><th>Sütun</th>{baslik}</tr></thead><tbody>"
                        f"{''.join(satirlar)}</tbody></table></div>")

        # Örnek hatalar.
        for y in calisan:
            yol = klasor / "cikti" / y / "hatalar.csv"
            if not yol.exists():
                continue
            df = pd.read_csv(yol, dtype=str, keep_default_na=False)
            df = df[df.sonuc == "yanlis"].head(12)
            if df.empty:
                continue
            satirlar = "".join(
                f"<tr><td>{_e(r.tablo)}.{_e(r.sutun)}</td><td class='kod'>{_e(r.bozuk)}</td>"
                f"<td class='kod'>{_e(r.temiz)}</td><td class='kod'>{_e(r.gercek)}</td>"
                f"<td>{_e(r.bozma)}</td></tr>" for r in df.itertuples())
            parcalar.append(f"<h2>{YONTEM_ADLARI[y]}: güvenle yanlış yazdığı örnekler</h2><div class='tablo'><table>"
                            "<thead><tr><th>Hücre</th><th>Kirli</th><th>Temizlenen</th><th>Gerçek</th>"
                            f"<th>Bozma</th></tr></thead><tbody>{satirlar}</tbody></table></div>")

    parcalar.append(
        "<h2>Okurken bilinmesi gerekenler</h2><ul class='not'>"
        "<li>Veri sentetiktir. Bozma kataloğunu ve kural yöntemini aynı kişi yazdı. Bu, kural yöntemini gerçek "
        "hayattakinden daha iyi gösterir: gerçekte kural yazarı hataların hepsini önceden görmez.</li>"
        "<li>LLM ve hibrit yöntemlere bozma kataloğu gösterilmedi. Üç yöntem de aynı iş kurallarını ve aynı "
        "referans listeleri (il, kategori, kargo firmaları) aldı.</li>"
        "<li>Doğruluk, kurtarılabilir bozuk hücreler üzerinden hesaplanır. Uydurma: kurtarılamaz ya da gerçekte "
        "boş olan hücreye yanlış değer yazmak.</li>"
        "<li>Maliyet, token kullanımından liste fiyatıyla hesaplanır. Önbellekten tekrar okunan çağrılar ilk "
        "çalıştırmadaki maliyetle sayılır.</li></ul>")
    sayfa = ("<!doctype html><html lang='tr'><head><meta charset='utf-8'>"
             "<meta name='viewport' content='width=device-width,initial-scale=1'>"
             f"<title>Veri Temizleme Karşılaştırması</title><style>{CSS}</style></head><body><main>"
             + "".join(parcalar) + "</main></body></html>")
    yol = klasor / "rapor.html"
    yol.write_text(sayfa, encoding="utf-8")
    return yol
