"""Ham CSV okuma ve bozuk satır onarımı (ayraç hatası, fazladan alan, yapışmış satırlar)."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from .. import referans as R

_ID = {"siparis_id": re.compile(r"S\d{6}"), "musteri_id": re.compile(r"(?i)#?m?-?\d{1,5}"),
       "urun_id": re.compile(r"(?i)#?u?-?\d{1,4}")}


@dataclass
class OkumaSonucu:
    basliklar: list[str]
    satirlar: list[dict[str, str]]
    karantina: list[dict[str, str]] = field(default_factory=list)
    onarilan: int = 0


def _uygunluk(tablo: str, basliklar: list[str], alanlar: list[str]) -> int:
    """Alanların sütun tiplerine kaba uygunluğu. Onarım adayları arasında seçim için."""
    puan = 0
    for sutun, deger in zip(basliklar, alanlar):
        tip = R.SEMA[tablo].get(sutun)
        d = deger.strip()
        if sutun in _ID:
            puan += bool(_ID[sutun].fullmatch(d))
        elif tip == "tarih":
            puan += bool(re.search(r"\d", d)) or d == ""
        elif tip in ("para", "oran", "adet"):
            puan += bool(re.search(r"\d", d)) or d == ""
        elif tip == "secenek":
            puan += not re.fullmatch(r"[\d.,/\-\s₺]+", d) if d else 1
    return puan


def satir_onar(tablo: str, basliklar: list[str], satir: str) -> list[list[str]] | None:
    """Bir ham satırı bir veya daha fazla kayda çevirir. Onarılamazsa None döner."""
    n = len(basliklar)
    alanlar = next(csv.reader([satir]))
    if len(alanlar) == n:
        return [alanlar]
    if len(alanlar) < n and satir.count(";") >= n - 1:
        noktali = next(csv.reader([satir], delimiter=";"))
        if len(noktali) == n:
            return [noktali]
    if len(alanlar) == n + 1:
        # Fazladan boş alan: çıkarıldığında tiplere en uygun olan konumu seç.
        adaylar = [alanlar[:i] + alanlar[i + 1:] for i, a in enumerate(alanlar) if a == ""]
        if adaylar:
            return [max(adaylar, key=lambda a: _uygunluk(tablo, basliklar, a))]
    if len(alanlar) == 2 * n - 1 and tablo == "siparisler":
        # İki satır yapışmış: ilk satırın son alanı ile ikincinin ilk alanı birleşmiş.
        m = re.fullmatch(r"(.*?)(S\d{6})", alanlar[n - 1])
        if m:
            return [alanlar[:n - 1] + [m[1]], [m[2]] + alanlar[n:]]
    return None


def oku(yol: Path, tablo: str) -> OkumaSonucu:
    metin = Path(yol).read_text(encoding="utf-8-sig")
    satirlar = metin.splitlines()
    basliklar = next(csv.reader([satirlar[0]]))
    sonuc = OkumaSonucu(basliklar, [])
    for satir in satirlar[1:]:
        if not satir.strip():
            continue
        kayitlar = satir_onar(tablo, basliklar, satir)
        if kayitlar is None:
            sonuc.karantina.append({"tablo": tablo, "ham_satir": satir, "sebep": "Alan sayısı uyuşmuyor"})
            continue
        if len(kayitlar) > 1 or len(next(csv.reader([satir]))) != len(basliklar):
            sonuc.onarilan += len(kayitlar)
        sonuc.satirlar.extend(dict(zip(basliklar, k)) for k in kayitlar)
    return sonuc
