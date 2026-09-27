"""Deney: aynı kirli veriyi üç yöntemle temizler ve hepsini aynı gerçek doğruyla ölçer."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pandas as pd

from .llm.hibrit import hibrit_ile_temizle
from .llm.istemci import VARSAYILAN_MODEL, LLMIstemci
from .llm.yontem import LLMTemizleyici, orneklem_sec
from .olcum import olc
from .temizleme.kural import kural_ile_temizle

YONTEMLER = ("kural", "hibrit", "llm")


def llm_kimligi_var_mi() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _hatalari_yaz(hucreler: pd.DataFrame, gercek: Path, yol: Path, n: int = 500):
    kayit = pd.read_csv(gercek / "bozma_kaydi.csv", dtype=str, keep_default_na=False)
    hatali = hucreler[hucreler.sonuc.isin(["yanlis", "bos"]) & ~((hucreler.sonuc == "bos") & ~hucreler.kurtarilabilir)]
    hatali = hatali.merge(kayit[["tablo", "anahtar", "sutun", "bozuk"]], on=["tablo", "anahtar", "sutun"],
                          how="left")
    hatali.head(n).to_csv(yol, index=False)


def yontem_calistir(yontem: str, kirli: Path, gercek: Path, cikti: Path, kapsam: dict,
                    istemci: LLMIstemci | None = None, paralel: int = 4) -> dict:
    cikti.mkdir(parents=True, exist_ok=True)
    bas = time.monotonic()
    llm_kullanim = None
    if yontem == "kural":
        t = kural_ile_temizle(kirli, cikti)
        istatistik = dict(t.istatistik)
    elif yontem == "hibrit":
        t = hibrit_ile_temizle(kirli, cikti, istemci)
        istatistik = dict(t.istatistik)
        llm_kullanim = istemci.kullanim.sozluk()
    elif yontem == "llm":
        t = LLMTemizleyici(istemci, paralel=paralel)
        tablolar = t.temizle(kirli, kapsam["siparisler"])
        t.yaz(tablolar, cikti)
        istatistik = dict(t.istatistik)
        llm_kullanim = istemci.kullanim.sozluk()
    else:
        raise ValueError(f"Bilinmeyen yöntem: {yontem}")
    sure = time.monotonic() - bas
    orneklem = olc(cikti / "temiz", gercek, kapsam)
    _hatalari_yaz(orneklem.hucreler, gercek, cikti / "hatalar.csv")
    tam = olc(cikti / "temiz", gercek).ozet if yontem != "llm" else None
    return {"sure": sure, "istatistik": istatistik, "llm": llm_kullanim, "orneklem": orneklem.ozet, "tam": tam}


def deney(klasor: Path, yontemler=YONTEMLER, model: str = VARSAYILAN_MODEL, effort: str = "medium",
          orneklem_n: int = 1000, seed: int = 42, paralel: int = 4, geri_donus: bool = True) -> dict:
    klasor = Path(klasor)
    kirli, gercek = klasor / "veri" / "kirli", klasor / "veri" / "gercek"
    kapsam = {"siparisler": orneklem_sec(kirli / "siparisler.csv", orneklem_n, seed)}
    sonuclar = {"ayarlar": {"model": model, "effort": effort, "orneklem": len(kapsam["siparisler"]), "seed": seed},
                "yontemler": {}}
    for yontem in yontemler:
        if yontem != "kural" and not llm_kimligi_var_mi():
            sonuclar["yontemler"][yontem] = {"atlandi": "ANTHROPIC_API_KEY tanımlı değil"}
            print(f"[{yontem}] atlandı: ANTHROPIC_API_KEY tanımlı değil")
            continue
        istemci = None if yontem == "kural" else LLMIstemci(
            model, effort, onbellek=klasor / "llm_onbellek" / yontem, geri_donus=geri_donus)
        print(f"[{yontem}] çalışıyor...")
        sonuclar["yontemler"][yontem] = yontem_calistir(yontem, kirli, gercek, klasor / "cikti" / yontem, kapsam,
                                                        istemci, paralel)
        o = sonuclar["yontemler"][yontem]["orneklem"]
        print(f"[{yontem}] doğruluk %{o['genel_dogruluk'] * 100:.1f}, uydurma {o['uydurma']['n']}, "
              f"süre {sonuclar['yontemler'][yontem]['sure']:.1f} sn")
    (klasor / "sonuclar.json").write_text(json.dumps(sonuclar, ensure_ascii=False, indent=2, default=str),
                                          encoding="utf-8")
    return sonuclar
