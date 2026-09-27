"""Temizlenmiş çıktıyı gerçek doğruyla karşılaştırır.

Her gerçek hücre için bir sonuç üretilir:
- dogru:  temiz değer gerçek değere eşit
- bos:    temiz değer boş, gerçek değer dolu (güvenli ıskalama)
- yanlis: temiz değer dolu ama gerçek değerden farklı (güvenle yanlış)

Kurtarılamaz hücrelerde doğru davranış boş bırakmaktır. Oraya yazılan yanlış değer ve gerçekte boş olan bir hücreye
yazılan her değer **uydurma** sayılır.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from itertools import combinations
from pathlib import Path

import pandas as pd

from . import referans as R


def normalize(tip: str, v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        if tip in ("para", "oran"):
            return round(float(s), 2)
        if tip == "adet":
            f = float(s)
            return int(f) if f == int(f) else f
        if tip == "tarih":
            return date.fromisoformat(s[:10]).isoformat() if len(s) >= 10 and s[4] == "-" else s
    except ValueError:
        return s
    return s


def _oku(yol: Path) -> pd.DataFrame:
    return pd.read_csv(yol, dtype=str, keep_default_na=False, encoding="utf-8")


@dataclass
class OlcumSonucu:
    hucreler: pd.DataFrame  # Hücre bazlı sonuçlar.
    ozet: dict


def olc(temiz_klasor: Path, gercek_klasor: Path, kapsam: dict[str, set[str]] | None = None) -> OlcumSonucu:
    temiz_klasor, gercek_klasor = Path(temiz_klasor), Path(gercek_klasor)
    kayit = _oku(gercek_klasor / "bozma_kaydi.csv")
    kayit_idx = {(r.tablo, r.anahtar, r.sutun): (r.bozma, r.kurtarilabilir == "True")
                 for r in kayit.itertuples() if r.sutun != "*satir*"}
    satirlar = []
    satir_ozeti = {}
    for tablo, sema in R.SEMA.items():
        anahtar = R.ANAHTARLAR[tablo]
        gercek = _oku(gercek_klasor / f"{tablo}.csv")
        temiz = _oku(temiz_klasor / f"{tablo}.csv") if (temiz_klasor / f"{tablo}.csv").exists() else \
            pd.DataFrame(columns=list(sema))
        if kapsam and tablo in kapsam:
            gercek = gercek[gercek[anahtar].isin(kapsam[tablo])]
        gercek_anahtarlar = set(gercek[anahtar])
        sayim = temiz[anahtar].value_counts()
        temiz_tekil = temiz.drop_duplicates(anahtar).set_index(anahtar)
        fazla = temiz[~temiz[anahtar].isin(set(_oku(gercek_klasor / f"{tablo}.csv")[anahtar]))]
        satir_ozeti[tablo] = {
            "gercek_satir": len(gercek),
            "bulunan_satir": int(sum(k in temiz_tekil.index for k in gercek_anahtarlar)),
            "tekrar_kalan": int(sum(sayim.get(k, 0) - 1 for k in gercek_anahtarlar if sayim.get(k, 0) > 1)),
            "fazla_satir": len(fazla) if not kapsam else None,
        }
        for g in gercek.itertuples(index=False):
            k = getattr(g, anahtar)
            var = k in temiz_tekil.index
            for sutun, tip in sema.items():
                if sutun == anahtar:
                    continue
                gv = normalize(tip, getattr(g, sutun))
                tv = normalize(tip, temiz_tekil.at[k, sutun]) if var and sutun in temiz_tekil.columns else None
                bozma, kurtarilabilir = kayit_idx.get((tablo, k, sutun), ("temiz", True))
                if not var:
                    sonuc = "satir_yok"
                elif tv == gv:
                    sonuc = "dogru"
                elif tv is None:
                    sonuc = "bos"
                else:
                    sonuc = "yanlis"
                satirlar.append((tablo, k, sutun, bozma, kurtarilabilir, gv is None, sonuc,
                                 getattr(g, sutun), None if not var else temiz_tekil.at[k, sutun]))
    hucreler = pd.DataFrame(satirlar, columns=["tablo", "anahtar", "sutun", "bozma", "kurtarilabilir",
                                               "gercek_bos", "sonuc", "gercek", "temiz"])
    ozet = {"satirlar": satir_ozeti, **_hucre_ozeti(hucreler),
            "tekrar": _tekrar_olc(temiz_klasor, gercek_klasor, kapsam),
            "satir_bozmalari": _satir_bozmalari(kayit, temiz_klasor, kapsam)}
    return OlcumSonucu(hucreler, ozet)


def _oranlar(df: pd.DataFrame) -> dict:
    n = len(df)
    c = df["sonuc"].value_counts()
    return {"n": n, **{s: (float(c.get(s, 0)) / n if n else 0.0) for s in ("dogru", "bos", "yanlis", "satir_yok")}}


def _hucre_ozeti(h: pd.DataFrame) -> dict:
    bozuk = h[h.bozma != "temiz"]
    kurtarilir = bozuk[bozuk.kurtarilabilir]
    kurtarilamaz = bozuk[~bozuk.kurtarilabilir]
    temiz = h[h.bozma == "temiz"]
    gercek_bos = h[h.gercek_bos]
    uydurma_n = int((kurtarilamaz.sonuc == "yanlis").sum() + (gercek_bos.sonuc == "yanlis").sum())
    uydurma_payda = len(kurtarilamaz) + len(gercek_bos)
    return {
        "genel_dogruluk": _oranlar(kurtarilir)["dogru"],
        "kurtarilabilir": _oranlar(kurtarilir),
        "kurtarilamaz": _oranlar(kurtarilamaz),
        "temiz_hucreler": _oranlar(temiz),
        "uydurma": {"n": uydurma_n, "payda": uydurma_payda,
                    "oran": uydurma_n / uydurma_payda if uydurma_payda else 0.0},
        "bozma_turu": {b: _oranlar(g) for b, g in kurtarilir.groupby("bozma")},
        "bozma_turu_kurtarilamaz": {b: _oranlar(g) for b, g in kurtarilamaz.groupby("bozma")},
        "sutun": {f"{t}.{s}": _oranlar(g) for (t, s), g in h.groupby(["tablo", "sutun"])},
    }


def _kume_ciftleri(eslesme: dict[str, str]) -> set[frozenset]:
    kumeler: dict[str, set[str]] = {}
    for eski, yeni in eslesme.items():
        kumeler.setdefault(yeni, {yeni}).add(eski)
    return {frozenset(c) for k in kumeler.values() for c in combinations(sorted(k), 2)}


def _tekrar_olc(temiz_klasor: Path, gercek_klasor: Path, kapsam) -> dict:
    gercek = _oku(gercek_klasor / "tekrar_eslesme.csv")
    yol = temiz_klasor / "musteri_eslesme.csv"
    tahmin = _oku(yol) if yol.exists() else pd.DataFrame(columns=["eski_id", "yeni_id"])
    if kapsam and "musteriler" in kapsam:
        gercek = gercek[gercek.asil_id.isin(kapsam["musteriler"])]
        ilgili = set(gercek.tekrar_id) | kapsam["musteriler"]
        tahmin = tahmin[tahmin.eski_id.isin(ilgili) | tahmin.yeni_id.isin(ilgili)]
    g = _kume_ciftleri(dict(zip(gercek.tekrar_id, gercek.asil_id)))
    t = _kume_ciftleri(dict(zip(tahmin.eski_id, tahmin.yeni_id)))
    dogru = len(g & t)
    kesinlik = dogru / len(t) if t else 0.0
    duyarlilik = dogru / len(g) if g else 0.0
    f1 = 2 * kesinlik * duyarlilik / (kesinlik + duyarlilik) if kesinlik + duyarlilik else 0.0
    return {"gercek_cift": len(g), "tahmin_cift": len(t), "dogru_cift": dogru,
            "kesinlik": kesinlik, "duyarlilik": duyarlilik, "f1": f1}


def _satir_bozmalari(kayit: pd.DataFrame, temiz_klasor: Path, kapsam) -> dict:
    siparis = _oku(temiz_klasor / "siparisler.csv") if (temiz_klasor / "siparisler.csv").exists() else \
        pd.DataFrame(columns=["siparis_id"])
    sayim = siparis["siparis_id"].value_counts()
    sonuc = {}
    for bozma in ("B2", "B14"):
        anahtarlar = set(kayit[(kayit.bozma == bozma) & (kayit.sutun == "*satir*") & (kayit.tablo == "siparisler")]
                         .anahtar)
        if kapsam and "siparisler" in kapsam:
            anahtarlar &= kapsam["siparisler"]
        if bozma == "B2":
            basari = sum(sayim.get(a, 0) == 1 for a in anahtarlar)
        else:
            basari = sum(sayim.get(a, 0) >= 1 for a in anahtarlar)
        sonuc[bozma] = {"n": len(anahtarlar), "basari": basari / len(anahtarlar) if anahtarlar else 0.0}
    return sonuc
