"""Sürpriz bozmalar (2. bölüm): kural yönteminin yazıldığı sırada hiç görülmemiş hata çeşitleri.

Aynı bozma türleri (B3, B4, B6...) gerçek hayatta başka yüzlerle de gelir. Burada her tür için yeni ama gerçekçi
biçimler var. Kural kodu bu biçimler eklenmeden önce donduruldu ve hiç değiştirilmedi. Yalnızca gerçek değeri
kirli metinden kesin olarak çıkarılabilen biçimler seçildi: sonuç belirsiz olsun diye bilerek belirsiz veri üretilmedi.
"""

from __future__ import annotations

import csv
import io
import random
from datetime import date, datetime, timezone

from .. import referans as R
from ..metin import ascii_fold, tr_lower, tr_upper

YER_TUTUCULAR = ["Belirtilmemiş", "YOK", "#N/A", "(boş)", "unknown", "NONE", "—", "boş", "Bilgi yok"]

_EN_AYLAR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

ES_ANLAMLILAR: dict[str, dict[str, list[str]]] = {
    "cinsiyet": {"Kadın": ["Kadin", "K.", "Female", "kadın (K)"], "Erkek": ["E.", "Male", "erkek (E)", "ERKEK."]},
    "kategori": {
        "Elektronik": ["Elektronik > Telefon & Aksesuar", "Electronics", "Elektronik Eşya"],
        "Ev & Yaşam": ["Ev Yaşam", "Ev / Yaşam", "Ev-Yaşam Ürünleri"],
        "Spor & Outdoor": ["Spor Outdoor", "Spor / Outdoor", "Sports & Outdoor"],
        "Kozmetik": ["Kozmetik > Cilt Bakımı", "Cosmetics", "Kozmetik Ürünleri"],
        "Süpermarket": ["Süper Market", "Supermarket", "Gıda & Süpermarket"],
        "Giyim": ["Giyim > Kadın", "Clothing", "Hazır Giyim"],
        "Kitap": ["Kitap > Roman", "Books", "Kitap & Dergi"],
        "Oyuncak": ["Oyuncak > Eğitici", "Toys", "Oyun & Oyuncak"],
    },
    "odeme_yontemi": {
        "Kredi Kartı": ["Kredi Kartı (Visa)", "Kredi Kartı - Mastercard", "KREDİ KARTI İLE", "Kredi kartı ile ödeme"],
        "Banka Kartı": ["Banka Kartı (Debit)", "Bankamatik Kartı", "banka kartı ile"],
        "Havale/EFT": ["EFT / Havale", "Havale veya EFT", "Banka Havalesi"],
        "Kapıda Ödeme": ["Kapıda Nakit", "Kapıda ödeme (nakit)", "Teslimatta Ödeme"],
        "Dijital Cüzdan": ["Dijital Cüzdan (Papara)", "Mobil Cüzdan", "E-Cüzdan"],
    },
    "kargo_firmasi": {
        "Yurtiçi Kargo": ["Yurtiçi Kargo A.Ş.", "Yurtici Krg", "YURTİÇİ KARGO (YK)"],
        "Aras Kargo": ["Aras Kargo A.Ş.", "ARAS KRG", "Aras Kargo Şubesi"],
        "MNG Kargo": ["MNG Kargo A.Ş.", "Mng Krg", "MNG KARGO YURTİÇİ"],
        "PTT Kargo": ["PTT Kargo Hizmetleri", "Ptt Krg", "Posta (PTT)"],
        "Sürat Kargo": ["Sürat Kargo A.Ş.", "Surat Krg", "SÜRAT KARGO LOJİSTİK"],
        "Trendyol Express": ["Trendyol Exp.", "Trendyol Ekspres Kargo", "TY Express"],
        "HepsiJet": ["Hepsijet Teslimat", "HepsiJET Kargo", "Hepsi-Jet"],
    },
    "durum": {
        "Teslim Edildi": ["Teslim edildi ✓", "Teslimat tamamlandı", "Delivered", "TESLİM"],
        "Kargoda": ["Kargoya verildi", "Yolda", "Dağıtımda"],
        "Hazırlanıyor": ["Hazırlanmakta", "Sipariş hazırlanıyor", "Paketleniyor"],
        "İptal Edildi": ["İptal (müşteri)", "Sipariş iptal", "Cancelled"],
        "İade Edildi": ["İade alındı", "İade tamamlandı", "Returned"],
    },
}


def tarih(rng: random.Random, iso: str) -> str:
    d = date.fromisoformat(iso)
    unix = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())
    excel = (d - date(1899, 12, 30)).days
    return rng.choice([
        f"{d:%Y.%m.%d}", f"{d.day}.{d.month}.{d.year}", f"{d.day} {R.AYLAR[d.month - 1]} {d.year} "
        f"{_GUNLER[d.weekday()]}", f"{_EN_AYLAR[d.month - 1]} {d.day}, {d.year}", f"{d.year}-{d.month}-{d.day}",
        str(unix), str(excel), f"{d:%d.%m.%Y} 14:32", f"{d.day:02d}{d.month:02d}{d.year}",
    ])


def mojibake(rng: random.Random, s: str) -> str:
    adaylar = []
    try:
        adaylar.append(s.encode("utf-8").decode("cp1252").encode("utf-8").decode("cp1252"))  # Çift bozulma.
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    varliklar = "".join(f"&#{ord(c)};" if c in "çğıöşüÇĞİÖŞÜ" else c for c in s)
    adaylar += [varliklar, "".join("_" if c in "çğıöşüÇĞİÖŞÜ" else c for c in s),
                "".join("�" if c in "çğıöşüÇĞİÖŞÜ" else c for c in s)]
    adaylar = [a for a in adaylar if a != s]
    return rng.choice(adaylar) if adaylar else s


def para(rng: random.Random, v: float) -> str:
    tam, kurus = f"{v:.2f}".split(".")
    binlik = f"{int(tam):,}"
    return rng.choice([
        f"{binlik.replace(',', ' ')},{kurus} TL", f"{tam}.{kurus} TRY", f"TL {binlik.replace(',', '.')},{kurus}",
        f"{binlik.replace(',', chr(39))}.{kurus}", f"{tam},{kurus} Türk Lirası", f"{tam} TL {kurus} kr",
        f"{tam}.{kurus} ₺ (KDV dahil)",
    ])


def oran(rng: random.Random, v: float) -> str:
    yuzde = round(v * 100)
    return rng.choice([f"yüzde {yuzde}", f"%{yuzde} indirim", f"{yuzde} %", f"{v:.1f}" if yuzde % 10 == 0 else f"{v:.2f}",
                       f"{yuzde}/100", "indirim yok" if yuzde == 0 else f"-%{yuzde}"])


def telefon(rng: random.Random, tel: str) -> str:
    d = "".join(c for c in tel if c.isdigit())[-10:]
    return rng.choice([
        f"0{d[:3]}-{d[3:6]}-{d[6:8]}-{d[8:]}", f"(0{d[:3]}) {d[3:]}", f"+90 {d[:3]} {d[3:]} (cep)",
        f"{d[:3]} {d[3:6]} {d[6:]}", f"0{d} / cep", f"+90-{d[:3]}-{d[3:6]}-{d[6:8]}-{d[8:]}", f"tel: 0{d}",
    ])


def eposta(rng: random.Random, e: str) -> str:
    yerel, alan = e.split("@")
    return rng.choice([
        f"{yerel}[at]{alan}", f"{yerel} @ {alan.replace('.', ' . ')}", f"mailto:{e}", f"<{e}>", f"{e}.",
        f"{yerel}@{alan.split('.')[0]}", f'"{e}"', f"{yerel}(at){alan}",
    ])


def bosluk(rng: random.Random, s: str) -> str:
    return rng.choice([f"{s}\r", f"  {s} ", f"{s} ", f"‎{s}", f"{s}­",
                       s.replace(" ", " ​ ", 1) if " " in s else f" {s}"])


def id_kaydir(rng: random.Random, v: str) -> str:
    onek, sayi = v[0], int(v[1:])
    uzun = {"M": "MUS", "U": "URN", "S": "SIP"}[onek]
    return rng.choice([f"{uzun}-{v[1:]}", f"{onek} {v[1:]}", f"{v}.0", f"{sayi:07d}", f"{onek}/{sayi}"])


def adet(rng: random.Random, n: int) -> str:
    kelime = {v: k for k, v in R.SAYI_KELIMELERI.items()}.get(n)
    secenekler = [f"{n} ADET", f"{n} pcs", f"{n}x", f"{n} tane", f"{n} (adet)", f"Adet: {n}"]
    if kelime:
        secenekler += [f"{kelime} adet", f"{n} ({kelime})", f"{kelime} tane"]
    return rng.choice(secenekler)


def es_anlamli(rng: random.Random, sutun: str, v: str) -> str:
    if sutun == "il":
        adaylar = [f"{v}/{rng.choice(R.IL_ILCELER.get(v, ([v], 0))[0])}", f"{v} Merkez", f"{v} İli", f"T.C. {v}",
                   f"{tr_upper(v)} / TÜRKİYE", f"{v}, Türkiye"]
        return rng.choice(adaylar)
    if sutun in ES_ANLAMLILAR:
        return rng.choice(ES_ANLAMLILAR[sutun][v])
    if sutun == "ilce":
        return rng.choice([f"{v} İlçesi", f"{v} (ilçe)", f"{tr_upper(ascii_fold(v))} ILCESI"])
    return rng.choice([f"{tr_upper(v)}.", f"{v} (müşteri)", tr_lower(v).capitalize() + "."])


def satir_boz(rng: random.Random, satir: str, baslik_sayisi: int) -> str:
    alanlar = next(csv.reader([satir]))
    tur = rng.randrange(3)
    if tur == 0:
        return "\t".join(alanlar)
    if tur == 1:
        return "|".join(alanlar)
    buf = io.StringIO()
    csv.writer(buf, lineterminator="", quoting=csv.QUOTE_ALL).writerow(alanlar)
    return buf.getvalue() + ","  # Sonda fazladan ayraç.


HUCRE = {"B3": tarih, "B4": mojibake, "B9": telefon, "B10": eposta, "B11": bosluk, "B13": id_kaydir}
