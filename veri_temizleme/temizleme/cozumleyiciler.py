"""Tek hücre çözümleyicileri. Her biri kirli bir metni kanonik değere çevirir ya da None döner."""

from __future__ import annotations

import re
from datetime import date

from .. import referans as R
from ..metin import ascii_fold, bosluk_temizle, mojibake_onar, tr_lower

YER_TUTUCU = {"", "null", "none", "nan", "-", "--", "yok", "n/a", "na", "?", "bilinmiyor", "0000-00-00", "#n/a"}


def on_temizle(v) -> str:
    """Her hücreye uygulanan ortak adım: görünmez karakter, boşluk ve mojibake onarımı."""
    if v is None:
        return ""
    return mojibake_onar(bosluk_temizle(str(v)))


def yer_tutucu_mu(s: str) -> bool:
    return tr_lower(s.strip()) in YER_TUTUCU


# --- Tarih -----------------------------------------------------------------------------------------------------

_AY_ANAHTAR = {ascii_fold(tr_lower(a)): i + 1 for i, a in enumerate(R.AYLAR)}
_AY_ANAHTAR.update({ascii_fold(tr_lower(a))[:3]: i + 1 for i, a in enumerate(R.AYLAR)})
_AY_ANAHTAR.update({a: i + 1 for i, a in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])})


def _yil(y: int) -> int:
    return y + (2000 if y < 50 else 1900) if y < 100 else y


def _gecerli(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def tarih_adaylari(s: str) -> list[date]:
    """Metnin olası tüm tarih yorumları. Birden fazla aday varsa tarih belirsizdir (gün/ay karışıklığı)."""
    s = s.strip()
    if yer_tutucu_mu(s):
        return []
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[T ].*)?", s)
    if m:
        d = _gecerli(int(m[1]), int(m[2]), int(m[3]))
        return [d] if d else []
    m = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", s)
    if m:
        d = _gecerli(int(m[1]), int(m[2]), int(m[3]))
        return [d] if d else []
    m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})", s)
    if m:
        a, b, y = int(m[1]), int(m[2]), _yil(int(m[3]))
        adaylar = [_gecerli(y, b, a)]  # Türkiye biçimi: gün/ay önce.
        if "/" in s:
            adaylar.append(_gecerli(y, a, b))  # ABD biçimi yalnızca eğik çizgide görülür.
        tekil = []
        for d in adaylar:
            if d and d not in tekil:
                tekil.append(d)
        return tekil
    m = re.fullmatch(r"(\d{1,2})[\s\-]+([^\s\-\d]+)[\s\-]+(\d{2,4})", s)
    if m:
        ay = _AY_ANAHTAR.get(ascii_fold(tr_lower(m[2])).rstrip("."))
        if ay:
            d = _gecerli(_yil(int(m[3])), ay, int(m[1]))
            return [d] if d else []
    return []


# --- Sayılar ---------------------------------------------------------------------------------------------------

def para(s: str) -> float | None:
    s = re.sub(r"(?i)(tl|try|₺|\s)", "", s)
    if not s or yer_tutucu_mu(s):
        return None
    if not re.fullmatch(r"-?[\d.,]+", s):
        return None
    if "." in s and "," in s:
        ondalik = "." if s.rfind(".") > s.rfind(",") else ","
    elif "," in s:
        ondalik = "," if len(s) - s.rfind(",") - 1 != 3 else None
    elif "." in s:
        ondalik = "." if s.count(".") == 1 and len(s) - s.rfind(".") - 1 != 3 else None
    else:
        ondalik = None
    binlik = {".", ","} - ({ondalik} if ondalik else set())
    for b in binlik:
        s = s.replace(b, "")
    if ondalik:
        s = s.replace(ondalik, ".")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def oran(s: str) -> float | None:
    yuzde = "%" in s
    v = para(s.replace("%", ""))
    if v is None:
        return None
    if yuzde or v > 1:
        v = v / 100
    return round(v, 4) if 0 <= v < 1 else None


def adet(s: str) -> int | None:
    s = tr_lower(s.strip())
    if s in R.SAYI_KELIMELERI:
        return R.SAYI_KELIMELERI[s]
    m = re.fullmatch(r"x?\s*(-?\d+(?:[.,]0+)?)\s*(?:adet|ad\.?|pcs|x)?", s)
    if not m:
        return None
    return int(float(m[1].replace(",", ".")))


# --- İletişim --------------------------------------------------------------------------------------------------

def telefon(s: str) -> str | None:
    rakam = re.sub(r"\D", "", s)
    if len(rakam) < 10:
        return None
    rakam = rakam[-10:]
    if not rakam.startswith("5"):
        return None
    return f"+90 {rakam[:3]} {rakam[3:6]} {rakam[6:8]} {rakam[8:]}"


EPOSTA_DESENI = re.compile(r"[a-z0-9._%+\-]+@[a-z0-9\-]+(\.[a-z0-9\-]+)*\.[a-z]{2,}")


def eposta_on(s: str) -> str:
    s = ascii_fold(s.replace("İ", "i").lower()).replace(" ", "").replace("\u0307", "")
    s = re.sub(r"@+", "@", s)
    if "@" in s:
        yerel, alan = s.split("@", 1)
        s = f"{yerel}@{alan.replace(',', '.')}"
    return s


def id_normalize(s: str, onek: str, basamak: int) -> str | None:
    m = re.fullmatch(rf"(?i)#?\s*{onek}?\s*-?\s*(\d+)", s.strip())
    if not m or len(m[1]) > basamak:
        return None
    return f"{onek}{int(m[1]):0{basamak}d}"
