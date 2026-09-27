"""Komut satırı: veri-temizle uret | temizle | olc | deney | rapor"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .llm.istemci import VARSAYILAN_MODEL


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="veri-temizle", description="Kirli e-ticaret verisi: üret, temizle, ölç.")
    alt = p.add_subparsers(dest="komut", required=True)

    u = alt.add_parser("uret", help="Sentetik temiz + kirli veri üret")
    u.add_argument("--klasor", default="calisma", type=Path)
    u.add_argument("--satir", default=10_000, type=int, help="Sipariş sayısı")
    u.add_argument("--musteri", default=2_500, type=int)
    u.add_argument("--urun", default=300, type=int)
    u.add_argument("--seed", default=42, type=int)
    u.add_argument("--oran-carpani", default=1.0, type=float, help="Tüm bozma oranlarını çarpar")

    for ad, yardim in (("deney", "Üretir, üç yöntemle temizler, ölçer ve raporlar"),
                       ("temizle", "Tek bir yöntemle temizler ve ölçer")):
        d = alt.add_parser(ad, help=yardim)
        d.add_argument("--klasor", default="calisma", type=Path)
        d.add_argument("--yontem", nargs="+", default=["kural", "hibrit", "llm"],
                       choices=["kural", "hibrit", "llm"])
        d.add_argument("--model", default=VARSAYILAN_MODEL)
        d.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
        d.add_argument("--orneklem", default=1000, type=int, help="LLM yönteminin temizleyeceği sipariş sayısı")
        d.add_argument("--seed", default=42, type=int)
        d.add_argument("--paralel", default=4, type=int)
        d.add_argument("--geri-donus-yok", action="store_true", help="Sunucu tarafı model geri dönüşünü kapat")
        if ad == "deney":
            d.add_argument("--satir", default=10_000, type=int)

    m = alt.add_parser("maliyet", help="Sadece LLM yönteminin kaba maliyet tahmini")
    m.add_argument("--klasor", default="calisma", type=Path)
    m.add_argument("--model", default=VARSAYILAN_MODEL)
    m.add_argument("--orneklem", default=1000, type=int)
    m.add_argument("--seed", default=42, type=int)

    pu = alt.add_parser("puanla", help="Kendi temizlediğin veriyi gerçek doğruyla puanla")
    pu.add_argument("temiz", type=Path, help="musteriler.csv, urunler.csv, siparisler.csv içeren klasör")
    pu.add_argument("--gercek", default=Path("veri_seti/gercek"), type=Path)

    g = alt.add_parser("gorsel", help="sonuclar.json'dan paylaşım görseli (PNG) üret")
    g.add_argument("--klasor", default="calisma", type=Path)
    g.add_argument("--cikti", default=Path("gorseller/tablo.png"), type=Path)

    r = alt.add_parser("rapor", help="sonuclar.json'dan HTML rapor üret")
    r.add_argument("--klasor", default="calisma", type=Path)

    a = p.parse_args(argv)
    if a.komut == "uret":
        from .uretici import uret
        print(json.dumps(uret(a.klasor / "veri", a.seed, a.satir, a.musteri, a.urun, a.oran_carpani)))
        return 0
    if a.komut in ("deney", "temizle"):
        from .deney import deney
        from .rapor import rapor_uret
        if a.komut == "deney" or not (a.klasor / "veri" / "kirli").exists():
            from .uretici import uret
            uret(a.klasor / "veri", a.seed, getattr(a, "satir", 10_000))
        deney(a.klasor, a.yontem, a.model, a.effort, a.orneklem, a.seed, a.paralel, not a.geri_donus_yok)
        print(f"Rapor: {rapor_uret(a.klasor)}")
        return 0
    if a.komut == "maliyet":
        from .llm.yontem import maliyet_tahmini, orneklem_sec
        kirli = a.klasor / "veri" / "kirli"
        print(json.dumps(maliyet_tahmini(kirli, orneklem_sec(kirli / "siparisler.csv", a.orneklem, a.seed), a.model)))
        return 0
    if a.komut == "puanla":
        from .olcum import olc
        print(puan_metni(olc(a.temiz, a.gercek).ozet))
        return 0
    if a.komut == "gorsel":
        from .gorsel import tablo_gorseli
        print(tablo_gorseli(a.klasor, a.cikti))
        return 0
    if a.komut == "rapor":
        from .rapor import rapor_uret
        print(rapor_uret(a.klasor))
        return 0
    return 1


def puan_metni(o: dict) -> str:
    from .uretici.bozma import BOZMA_ADLARI

    y = lambda v: f"%{v * 100:.1f}".replace(".", ",")  # noqa: E731
    satirlar = [
        f"Genel doğru düzeltme      {y(o['genel_dogruluk'])}   (kurtarılabilir {o['kurtarilabilir']['n']} bozuk hücre)",
        f"Uydurma                   {o['uydurma']['n']} / {o['uydurma']['payda']}   ({y(o['uydurma']['oran'])})",
        f"Temiz hücreyi bozma       {y(1 - o['temiz_hucreler']['dogru'])}",
        f"Müşteri eşleştirme F1     {o['tekrar']['f1']:.3f}",
        f"Tekrar sipariş silme      {y(o['satir_bozmalari']['B2']['basari'])}",
        f"Bozuk satır kurtarma      {y(o['satir_bozmalari']['B14']['basari'])}",
        "", "Bozma türüne göre:",
    ]
    for b, d in sorted(o["bozma_turu"].items(), key=lambda x: int(x[0][1:])):
        satirlar.append(f"  {b:<4} {BOZMA_ADLARI[b]:<30} {y(d['dogru']):>7}  (boş {y(d['bos'])}, yanlış {y(d['yanlis'])})")
    return "\n".join(satirlar)


if __name__ == "__main__":
    sys.exit(main())
