"""Türkçe metin yardımcıları: büyük/küçük harf, ASCII'ye indirgeme, mojibake onarımı, boşluk temizliği."""

from __future__ import annotations

import re
import unicodedata

_TR_UPPER = str.maketrans({"i": "İ", "ı": "I"})
_TR_LOWER = str.maketrans({"I": "ı", "İ": "i"})
_ASCII = str.maketrans("çğıöşüÇĞİÖŞÜâîûÂÎÛ", "cgiosuCGIOSUaiuAIU")

# Görünmez karakterler: sıfır genişlikli boşluk, BOM, bölünmez boşluk vb.
_GORUNMEZ = re.compile("[​‌‍⁠﻿]")
_BOSLUK = re.compile(r"[\s ]+")


def tr_upper(s: str) -> str:
    return s.translate(_TR_UPPER).upper()


def tr_lower(s: str) -> str:
    return s.translate(_TR_LOWER).lower()


def tr_title(s: str) -> str:
    """Her kelimenin ilk harfini Türkçe kurallarıyla büyütür: 'ışık izmir' -> 'Işık İzmir'."""

    def kelime(k: str) -> str:
        return tr_upper(k[:1]) + tr_lower(k[1:]) if k else k

    return re.sub(r"[^\s\-']+", lambda m: kelime(m.group(0)), s)


def ascii_fold(s: str) -> str:
    return s.translate(_ASCII)


def anahtar(s: str) -> str:
    """Karşılaştırma anahtarı: küçük harf, ASCII, sadece harf ve rakam."""
    return re.sub(r"[^a-z0-9]", "", ascii_fold(tr_lower(s)))


def bosluk_temizle(s: str) -> str:
    s = _GORUNMEZ.sub("", s)
    return _BOSLUK.sub(" ", s).strip()


# UTF-8 baytlarının yanlış kod sayfasıyla okunmasıyla oluşan tipik diziler.
_UTF8_CP1252_IZI = re.compile("[ÃÄÅ][\u0080-ÿŒœŠšŸŽžƒˆ˜–-›€™]")
# Windows-1254 (Türkçe) baytlarının Latin-1 ile okunması: Þ, þ, Ð, ð, Ý, ý.
_CP1254_LATIN1_IZI = re.compile("[ÞþÐðÝý]")


def mojibake_onar(s: str) -> str:
    """Bozuk kodlanmış Türkçe karakterleri geri çevirir. Emin olunamazsa metni aynen döner."""
    if _UTF8_CP1252_IZI.search(s):
        try:
            return s.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    if _CP1254_LATIN1_IZI.search(s):
        try:
            return s.encode("latin-1").decode("cp1254")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return s


def mojibake_var_mi(s: str) -> bool:
    return bool(_UTF8_CP1252_IZI.search(s) or _CP1254_LATIN1_IZI.search(s))


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)
