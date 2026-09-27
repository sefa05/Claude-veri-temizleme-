"""Serbest yazılmış değerleri kanonik seçeneklere eşleme (il, ilçe, kategori, kargo...)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from .. import referans as R
from ..metin import anahtar, ascii_fold, tr_lower

# Kural yazarı kirli verinin sık görülen değerlerine bakarak bu kısa listeyi yazdı. Bozma kataloğu kullanılmadı.
KURAL_ES_ANLAMLILARI: dict[str, dict[str, str]] = {
    "cinsiyet": {"k": "Kadın", "bayan": "Kadın", "f": "Kadın", "e": "Erkek", "bay": "Erkek", "m": "Erkek"},
    "durum": {"teslim": "Teslim Edildi", "iptal": "İptal Edildi", "iade": "İade Edildi",
              "delivered": "Teslim Edildi", "cancelled": "İptal Edildi", "returned": "İade Edildi",
              "shipped": "Kargoda"},
    "odeme_yontemi": {"kk": "Kredi Kartı", "havale": "Havale/EFT", "eft": "Havale/EFT", "kapida": "Kapıda Ödeme"},
    "kategori": {"market": "Süpermarket"},
}


@dataclass
class Eslesme:
    deger: str | None
    skor: float
    adaylar: list[str]


class Eslestirici:
    def __init__(self, secenekler: list[str], es_anlamlilar: dict[str, str] | None = None, esik: float = 85):
        self.secenekler = list(secenekler)
        self.anahtarlar = {anahtar(s): s for s in self.secenekler}
        self.es = {anahtar(k): v for k, v in (es_anlamlilar or {}).items()}
        self.esik = esik

    def adaylar(self, s: str, n: int = 5) -> list[str]:
        if len(self.secenekler) <= 10:
            return list(self.secenekler)
        k = anahtar(s.replace("?", ""))
        return [self.anahtarlar[m[0]] for m in process.extract(k, list(self.anahtarlar), scorer=fuzz.WRatio,
                                                                 limit=n)]

    def eslestir(self, s: str) -> Eslesme:
        k = anahtar(s)
        if k in self.anahtarlar:
            return Eslesme(self.anahtarlar[k], 100, [])
        if k in self.es:
            return Eslesme(self.es[k], 100, [])
        if "?" in s:
            # '?' Türkçe karakterin yerini tutar: aynı uzunlukta, joker karakterli eşleşme.
            desen = re.compile("".join("." if c == "?" else re.escape(c) for c in anahtar_joker(s)) + "$")
            bulunan = [v for a, v in self.anahtarlar.items() if desen.match(a)]
            if len(bulunan) == 1:
                return Eslesme(bulunan[0], 95, [])
        if len(k) >= 3:
            onek = [v for a, v in self.anahtarlar.items() if a.startswith(k)]
            if len(onek) == 1:
                return Eslesme(onek[0], 90, [])
            ters = [v for a, v in self.anahtarlar.items() if len(a) >= 4 and k.startswith(a)]
            if len(ters) == 1:
                return Eslesme(ters[0], 86, [])
        if k:
            sonuc = process.extract(k, list(self.anahtarlar), scorer=fuzz.ratio, limit=2)
            if sonuc and sonuc[0][1] >= self.esik and (len(sonuc) == 1 or sonuc[0][1] - sonuc[1][1] >= 5):
                return Eslesme(self.anahtarlar[sonuc[0][0]], sonuc[0][1], [])
        return Eslesme(None, 0, self.adaylar(s))


def anahtar_joker(s: str) -> str:
    """anahtar() gibi, ama '?' karakterlerini korur."""
    return re.sub(r"[^a-z0-9?]", "", ascii_fold(tr_lower(s)))


class IlEslestirici(Eslestirici):
    def __init__(self):
        super().__init__(list(R.ILLER.values()), esik=85)
        self.plaka = {str(k): v for k, v in R.ILLER.items()} | {f"{k:02d}": v for k, v in R.ILLER.items()}

    def eslestir(self, s: str) -> Eslesme:
        t = s.strip().rstrip(".")
        if t in self.plaka:
            return Eslesme(self.plaka[t], 100, [])
        t = re.sub(r"\(.*?\)", "", t).strip()
        return super().eslestir(t)


def secenek_eslestirici(sutun: str) -> Eslestirici:
    return Eslestirici(R.SECENEKLER[sutun], KURAL_ES_ANLAMLILARI.get(sutun))


def ilce_eslestirici() -> Eslestirici:
    return Eslestirici(list(R.ILCE_IL), esik=88)
