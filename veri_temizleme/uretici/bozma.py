"""Bozma motoru: temiz veriyi bilerek kirletir ve her bozmayı `bozma_kaydi` tablosuna yazar.

Her hücre en fazla bir kez bozulur. Kayıttaki `kurtarilabilir` alanı, gerçek değerin kirli veriden (diğer sütunlar,
diğer tablolar veya ana veri yardımıyla) çıkarılıp çıkarılamayacağını söyler. Kurtarılamayan bir hücre için doğru
davranış onu boş bırakmaktır. Oraya yazılan her değer "uydurma" sayılır.
"""

from __future__ import annotations

import csv
import io
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

from .. import referans as R
from ..metin import ascii_fold, tr_lower, tr_upper

YER_TUTUCULAR = ["", "NULL", "null", "-", "yok", "N/A", "?", "nan", "Bilinmiyor", "--"]

BOZMA_ADLARI = {
    "B1": "Tekrarlanan müşteri", "B2": "Tekrarlanan sipariş satırı", "B3": "Karışık tarih formatı",
    "B4": "Bozuk Türkçe karakter", "B5": "Eksik değer / yer tutucu", "B6": "Sayı ve para formatı",
    "B7": "Geçersiz / aykırı değer", "B8": "Yazım tutarsızlığı", "B9": "Telefon formatı", "B10": "Bozuk e-posta",
    "B11": "Boşluk ve görünmez karakter", "B12": "Tutarsız toplam", "B13": "ID format kayması",
    "B14": "Kaymış / bozuk satır", "B15": "Karışık birim ve tip",
}

# (tablo, sütun, bozma, oran)
VARSAYILAN_ORANLAR: list[tuple[str, str, str, float]] = [
    ("musteriler", "ad", "B4", 0.03), ("musteriler", "ad", "B8", 0.04), ("musteriler", "ad", "B11", 0.03),
    ("musteriler", "soyad", "B4", 0.03), ("musteriler", "soyad", "B8", 0.04), ("musteriler", "soyad", "B11", 0.03),
    ("musteriler", "eposta", "B10", 0.06), ("musteriler", "eposta", "B5", 0.02), ("musteriler", "eposta", "B11", 0.02),
    ("musteriler", "telefon", "B9", 0.25), ("musteriler", "telefon", "B5", 0.03),
    ("musteriler", "dogum_tarihi", "B3", 0.2), ("musteriler", "dogum_tarihi", "B7", 0.015),
    ("musteriler", "dogum_tarihi", "B5", 0.02),
    ("musteriler", "cinsiyet", "B8", 0.08), ("musteriler", "cinsiyet", "B5", 0.03),
    ("musteriler", "il", "B8", 0.1), ("musteriler", "il", "B4", 0.03), ("musteriler", "il", "B5", 0.02),
    ("musteriler", "ilce", "B8", 0.05), ("musteriler", "ilce", "B4", 0.03), ("musteriler", "ilce", "B5", 0.02),
    ("musteriler", "kayit_tarihi", "B3", 0.2), ("musteriler", "kayit_tarihi", "B5", 0.01),
    ("urunler", "urun_adi", "B11", 0.04), ("urunler", "urun_adi", "B4", 0.03),
    ("urunler", "kategori", "B8", 0.12), ("urunler", "kategori", "B4", 0.02),
    ("urunler", "marka", "B8", 0.05), ("urunler", "marka", "B5", 0.03),
    ("urunler", "birim_fiyat", "B6", 0.3), ("urunler", "birim_fiyat", "B5", 0.02),
    ("siparisler", "musteri_id", "B13", 0.03), ("siparisler", "urun_id", "B13", 0.03),
    ("siparisler", "siparis_tarihi", "B3", 0.25), ("siparisler", "siparis_tarihi", "B7", 0.01),
    ("siparisler", "siparis_tarihi", "B5", 0.01),
    ("siparisler", "adet", "B15", 0.06), ("siparisler", "adet", "B7", 0.02),
    ("siparisler", "birim_fiyat", "B6", 0.25), ("siparisler", "birim_fiyat", "B5", 0.02),
    ("siparisler", "indirim_orani", "B6", 0.15), ("siparisler", "indirim_orani", "B5", 0.02),
    ("siparisler", "toplam_tutar", "B6", 0.25), ("siparisler", "toplam_tutar", "B12", 0.03),
    ("siparisler", "toplam_tutar", "B5", 0.02),
    ("siparisler", "odeme_yontemi", "B8", 0.1), ("siparisler", "odeme_yontemi", "B5", 0.02),
    ("siparisler", "odeme_yontemi", "B11", 0.03),
    ("siparisler", "kargo_firmasi", "B8", 0.1), ("siparisler", "kargo_firmasi", "B5", 0.02),
    ("siparisler", "kargo_firmasi", "B4", 0.02), ("siparisler", "kargo_firmasi", "B11", 0.03),
    ("siparisler", "teslim_tarihi", "B3", 0.2), ("siparisler", "teslim_tarihi", "B5", 0.03),
    ("siparisler", "teslim_tarihi", "B7", 0.01),
    ("siparisler", "durum", "B8", 0.08), ("siparisler", "durum", "B4", 0.02), ("siparisler", "durum", "B11", 0.03),
]
SATIR_ORANLARI = {"B1": 0.05, "B1_siparis": 0.4, "B2": 0.02, "B14": 0.01}

# Kurtarılamayan bozmalar. Diğer tüm bozmalarda gerçek değer kirli veriden çıkarılabilir.
KURTARILAMAZ = {
    ("musteriler", "eposta", "B5"), ("musteriler", "telefon", "B5"), ("musteriler", "dogum_tarihi", "B7"),
    ("musteriler", "dogum_tarihi", "B5"), ("musteriler", "ilce", "B5"), ("musteriler", "kayit_tarihi", "B5"),
    ("siparisler", "siparis_tarihi", "B7"), ("siparisler", "siparis_tarihi", "B5"),
    ("siparisler", "odeme_yontemi", "B5"), ("siparisler", "kargo_firmasi", "B5"),
    ("siparisler", "teslim_tarihi", "B7"),
}

ES_ANLAMLILAR: dict[str, dict[str, list[str]]] = {
    "cinsiyet": {"Kadın": ["K", "kadın", "KADIN", "Bayan", "kadin", "F"],
                 "Erkek": ["E", "erkek", "ERKEK", "Bay", "M"]},
    "kategori": {
        "Elektronik": ["elektronık", "ELEKTRONİK", "Elektronik Ürünler", "elektronik"],
        "Ev & Yaşam": ["Ev ve Yaşam", "Ev&Yasam", "ev & yaşam", "EV-YAŞAM"],
        "Spor & Outdoor": ["Spor ve Outdoor", "spor", "Spor&Outdoor", "SPOR OUTDOOR"],
        "Kozmetik": ["Kozmetik & Kişisel Bakım", "kozmetık", "KOZMETİK"],
        "Süpermarket": ["Market", "süpermarket", "Super Market", "SÜPERMARKET"],
        "Giyim": ["Giyim & Moda", "GİYİM", "giyım"],
        "Kitap": ["Kitaplar", "kitap", "KİTAP"],
        "Oyuncak": ["Oyuncaklar", "oyuncak", "OYUNCAK"],
    },
    "odeme_yontemi": {
        "Kredi Kartı": ["kredi kartı", "KK", "Kredi karti", "kredi_karti", "CC"],
        "Banka Kartı": ["banka kartı", "Debit", "Banka karti", "BANKA KARTI"],
        "Havale/EFT": ["havale", "EFT", "Havale - EFT", "HAVALE/EFT"],
        "Kapıda Ödeme": ["kapıda ödeme", "Kapida odeme", "KAPIDA", "Kapıda"],
        "Dijital Cüzdan": ["dijital cüzdan", "Papara", "e-cüzdan", "Dijital cuzdan"],
    },
    "kargo_firmasi": {
        "Yurtiçi Kargo": ["Yurtiçi", "yurtici kargo", "YK", "YURTİÇİ KARGO"],
        "Aras Kargo": ["Aras", "aras kargo", "ARAS"],
        "MNG Kargo": ["MNG", "mng kargo", "Mng"],
        "PTT Kargo": ["PTT", "ptt", "Ptt Kargo"],
        "Sürat Kargo": ["Sürat", "surat kargo", "SÜRAT"],
        "Trendyol Express": ["TEX", "trendyol express", "Trendyol Ekspres"],
        "HepsiJet": ["Hepsi Jet", "hepsijet", "HEPSİJET"],
    },
    "durum": {
        "Teslim Edildi": ["teslim edildi", "Teslim", "TESLİM EDİLDİ", "delivered", "Tamamlandı"],
        "Kargoda": ["kargoda", "Kargoya Verildi", "shipped"],
        "Hazırlanıyor": ["hazırlanıyor", "Hazirlaniyor", "HAZIRLANIYOR"],
        "İptal Edildi": ["iptal", "İPTAL", "cancelled", "Iptal edildi"],
        "İade Edildi": ["iade", "İade", "returned", "IADE EDILDI"],
    },
}
EPOSTA_YAZIM_HATALARI = {
    "gmail.com": ["gmial.com", "gmail.con", "gmai.com", "gmail.co"],
    "hotmail.com": ["hotmial.com", "hotmail.con", "hotmal.com"],
    "outlook.com": ["outlok.com", "outlook.con"],
    "yahoo.com": ["yaho.com", "yahoo.con"],
    "icloud.com": ["iclod.com", "icloud.con"],
}
_EN_AYLAR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@dataclass
class Sonuc:
    tablolar: dict[str, pd.DataFrame]
    csv_metinleri: dict[str, str]
    kayit: pd.DataFrame
    tekrar_eslesme: pd.DataFrame
    kayitlar: list[dict] = field(default_factory=list)


# --- Hücre bozucuları ------------------------------------------------------------------------------------------

def _harf_varyanti(rng: random.Random, s: str) -> str:
    adaylar = [tr_upper(s), tr_lower(s), ascii_fold(s), tr_upper(ascii_fold(s)), ascii_fold(tr_lower(s))]
    adaylar = [a for a in adaylar if a != s]
    return rng.choice(adaylar) if adaylar else s


def mojibake(rng: random.Random, s: str) -> str:
    adaylar = []
    try:
        adaylar.append(s.encode("utf-8").decode("cp1252"))
    except UnicodeDecodeError:
        pass
    try:
        adaylar.append(s.encode("cp1254").decode("latin-1"))
    except UnicodeEncodeError:
        pass
    adaylar.append("".join("?" if c in "çğıöşüÇĞİÖŞÜ" else c for c in s))
    adaylar = [a for a in adaylar if a != s]
    return rng.choice(adaylar) if adaylar else s


def tarih_formatla(rng: random.Random, iso: str) -> str:
    d = date.fromisoformat(iso)
    bicim = rng.choices(range(10), weights=[14, 14, 8, 12, 8, 8, 10, 6, 6, 6])[0]
    return [
        f"{d:%d/%m/%Y}", f"{d:%d.%m.%Y}", f"{d:%d.%m.%y}", f"{d.day} {R.AYLAR[d.month - 1]} {d.year}",
        f"{d:%Y%m%d}", f"{d:%Y-%m-%d}T00:00:00", f"{d:%m/%d/%Y}", f"{d:%Y/%m/%d}",
        f"{d.day:02d}-{_EN_AYLAR[d.month - 1]}-{d.year}", f"{d.day} {tr_lower(R.AYLAR[d.month - 1])} {d.year % 100:02d}",
    ][bicim]


def para_formatla(rng: random.Random, v: float) -> str:
    tam, kurus = f"{v:.2f}".split(".")
    binlik = f"{int(tam):,}"
    bicim = rng.randrange(8)
    return [
        f"{binlik.replace(',', '.')},{kurus} TL", f"₺{binlik}.{kurus}", f"{tam},{kurus} tl", f"{v:g}",
        f"TRY {tam}.{kurus}", f"{binlik.replace(',', '.')},{kurus}", f"{tam},{kurus}₺", f"{tam}.{kurus} TL",
    ][bicim]


def oran_formatla(rng: random.Random, v: float) -> str:
    yuzde = round(v * 100)
    return rng.choice([f"%{yuzde}", f"{yuzde}", f"{v:.2f}".replace(".", ","), f"{yuzde}%", f"%{yuzde}.0"])


def telefon_formatla(rng: random.Random, tel: str) -> str:
    d = "".join(c for c in tel if c.isdigit())[-10:]
    return rng.choice([
        f"0{d[:3]} {d[3:6]} {d[6:8]} {d[8:]}", f"+90({d[:3]}){d[3:]}", d, f"{d[:3]}-{d[3:6]}-{d[6:]}",
        f"0 ({d[:3]}) {d[3:6]} {d[6:8]} {d[8:]}", f"+90{d}", f"90 {d[:3]} {d[3:6]} {d[6:]}",
    ])


def eposta_boz(rng: random.Random, e: str) -> str:
    yerel, alan = e.split("@")
    tur = rng.randrange(5)
    if tur == 0:
        return f"  {e.upper()} "
    if tur == 1:
        return f"{yerel}@@{alan}"
    if tur == 2:
        return f"{yerel}@{alan.replace('.', ',')}"
    if tur == 3:
        return f"{yerel}@{rng.choice(EPOSTA_YAZIM_HATALARI[alan])}"
    return f"{yerel}{alan}"


def bosluk_boz(rng: random.Random, s: str) -> str:
    tur = rng.randrange(5)
    if tur == 0:
        return f"  {s}   "
    if tur == 1:
        return s.replace(" ", "  ", 1) + " " if " " in s else f" {s}"
    if tur == 2:
        return f"\t{s}"
    if tur == 3:
        i = rng.randint(1, max(1, len(s) - 1))
        return s[:i] + "​" + s[i:]
    return s.replace(" ", " ", 1) + " "


def id_kaydir(rng: random.Random, v: str) -> str:
    onek, sayi = v[0], int(v[1:])
    return rng.choice([f"{onek}{sayi}", f"{tr_lower(onek)}{v[1:]}", f"{onek}-{v[1:]}", str(sayi), f"#{sayi}"])


def adet_boz(rng: random.Random, n: int) -> str:
    kelime = {v: k for k, v in R.SAYI_KELIMELERI.items()}.get(n)
    secenekler = [f"{n} adet", f"{n}.0", f"{n},0", f"{n} ad.", f"x{n}"]
    if kelime:
        secenekler.append(kelime)
    return rng.choice(secenekler)


def es_anlamli(rng: random.Random, sutun: str, v: str) -> str:
    if sutun == "il":
        plaka = next(k for k, il in R.ILLER.items() if il == v)
        adaylar = [str(plaka), f"{plaka:02d}", _harf_varyanti(rng, v), tr_upper(v[:3]) + ".", ascii_fold(v)]
        if v == "İstanbul":
            adaylar += ["İstanbul (Avrupa)", "İST", "Ist."]
        return rng.choice([a for a in adaylar if a != v])
    if sutun in ES_ANLAMLILAR:
        return rng.choice(ES_ANLAMLILAR[sutun][v] + [_harf_varyanti(rng, v)])
    return _harf_varyanti(rng, v)


def hucre_boz(rng: random.Random, tablo: str, sutun: str, bozma: str, v, satir: dict, surpriz: bool = False):
    """Bir hücreyi bozar. Uygulanamıyorsa None döner. `surpriz` 2. bölümün yeni hata biçimlerini kullanır."""
    if surpriz:
        from . import surpriz as S
        if bozma in S.HUCRE:
            if bozma == "B3" and not v:
                return None
            s = S.HUCRE[bozma](rng, v)
            return s if s != v else None
        if bozma == "B5":
            return rng.choice(S.YER_TUTUCULAR)
        if bozma == "B6":
            return S.oran(rng, v) if sutun == "indirim_orani" else S.para(rng, v)
        if bozma == "B8":
            return S.es_anlamli(rng, sutun, v)
        if bozma == "B15":
            return S.adet(rng, v)
    if bozma == "B3":
        return tarih_formatla(rng, v) if v else None
    if bozma == "B4":
        s = mojibake(rng, v)
        return s if s != v else None
    if bozma == "B5":
        return rng.choice(YER_TUTUCULAR + (["0000-00-00"] if R.SEMA[tablo][sutun] == "tarih" else []))
    if bozma == "B6":
        return oran_formatla(rng, v) if sutun == "indirim_orani" else para_formatla(rng, v)
    if bozma == "B7":
        if sutun == "dogum_tarihi":
            d = date.fromisoformat(v)
            return d.replace(year=rng.choice([rng.randint(1800, 1899), rng.randint(2030, 2099)])).isoformat()
        if sutun == "siparis_tarihi":
            return date.fromisoformat(v).replace(year=rng.randint(2031, 2045)).isoformat()
        if sutun == "teslim_tarihi":
            if not v:
                return None
            return (date.fromisoformat(satir["siparis_tarihi"]) - timedelta(days=rng.randint(3, 40))).isoformat()
        if sutun == "adet":
            return rng.choice([str(-v), "9999", "0"]) if v else None
    if bozma == "B8":
        return es_anlamli(rng, sutun, v)
    if bozma == "B9":
        return telefon_formatla(rng, v)
    if bozma == "B10":
        return eposta_boz(rng, v)
    if bozma == "B11":
        return bosluk_boz(rng, v)
    if bozma == "B12":
        indirim = satir["indirim_orani"]
        if indirim > 0 and rng.random() < 0.6:
            yanlis = round(satir["adet"] * satir["birim_fiyat"], 2)  # İndirim uygulanmamış.
        else:
            yanlis = round(v * rng.choice([10, 0.1, 1.18, 2]), 2)
        return f"{yanlis:.2f}" if abs(yanlis - v) > 0.01 else None
    if bozma == "B13":
        return id_kaydir(rng, v)
    if bozma == "B15":
        return adet_boz(rng, v)
    raise ValueError(f"Bilinmeyen bozma: {bozma}")


# --- Tablo dönüşümleri -----------------------------------------------------------------------------------------

def metne_cevir(tablo: str, df: pd.DataFrame) -> pd.DataFrame:
    """Temiz değerleri kanonik metin biçimine çevirir (bozulmamış hücreler böyle görünür)."""
    out = df.copy().astype(object)
    for sutun, tip in R.SEMA[tablo].items():
        if tip == "para":
            out[sutun] = [f"{v:.2f}" for v in df[sutun]]
        elif tip == "oran":
            out[sutun] = [f"{v:.2f}" for v in df[sutun]]
        elif tip == "adet":
            out[sutun] = [str(int(v)) for v in df[sutun]]
        else:
            out[sutun] = df[sutun].astype(str)
    return out


def _musteri_tekrari(rng: random.Random, satir: dict, yeni_id: str) -> dict:
    t = dict(satir)
    t["musteri_id"] = yeni_id
    if rng.random() < 0.15:
        t["ad"], t["soyad"] = t["soyad"], t["ad"]
    for s in ("ad", "soyad"):
        if rng.random() < 0.5:
            t[s] = _harf_varyanti(rng, t[s])
    r = rng.random()
    if r < 0.35:
        yerel, alan = t["eposta"].split("@")
        t["eposta"] = f"{yerel}{rng.randint(1, 9)}@{rng.choice(list(R.EPOSTA_ALANLARI))}"
    elif r < 0.55:
        t["eposta"] = t["eposta"].upper()
    elif r < 0.65:
        t["eposta"] = ""
    if rng.random() < 0.6:
        t["telefon"] = telefon_formatla(rng, t["telefon"])
    elif rng.random() < 0.3:
        t["telefon"] = ""
    if rng.random() < 0.3:
        t["il"] = es_anlamli(rng, "il", t["il"])
    kayit = date.fromisoformat(t["kayit_tarihi"]) + timedelta(days=rng.randint(30, 700))
    t["kayit_tarihi"] = min(kayit, date(2024, 12, 31)).isoformat()
    if rng.random() < 0.3:
        t["dogum_tarihi"] = tarih_formatla(rng, t["dogum_tarihi"])
    return t


def csv_yaz(df: pd.DataFrame) -> str:
    buf = io.StringIO()
    df.to_csv(buf, index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    return buf.getvalue()


def _satir_boz(rng: random.Random, metin: str, oran: float, kayitlar: list[dict], surpriz: bool = False) -> str:
    satirlar = metin.rstrip("\n").split("\n")
    baslik, govde = satirlar[0], satirlar[1:]
    sonuc = [baslik]
    i = 0
    while i < len(govde):
        satir = govde[i]
        if rng.random() >= oran or i + 1 >= len(govde):
            sonuc.append(satir)
            i += 1
            continue
        alanlar = next(csv.reader([satir]))
        tur = rng.randrange(3)
        if surpriz:
            from .surpriz import satir_boz
            yeni = satir_boz(rng, satir, len(alanlar))
            kayitlar.append({"tablo": "siparisler", "anahtar": alanlar[0], "sutun": "*satir*", "bozma": "B14",
                             "gercek": "", "bozuk": yeni, "kurtarilabilir": True})
            sonuc.append(yeni)
            i += 1
            continue
        if tur == 0:
            yeni = ";".join(alanlar)
        elif tur == 1:
            k = rng.randint(2, len(alanlar) - 1)
            buf = io.StringIO()
            csv.writer(buf, lineterminator="").writerow(alanlar[:k] + [""] + alanlar[k:])
            yeni = buf.getvalue()
        else:
            yeni = satir + govde[i + 1]
            ikinci = next(csv.reader([govde[i + 1]]))[0]
            kayitlar.append({"tablo": "siparisler", "anahtar": ikinci, "sutun": "*satir*", "bozma": "B14",
                             "gercek": "", "bozuk": yeni, "kurtarilabilir": True})
            i += 1
        kayitlar.append({"tablo": "siparisler", "anahtar": alanlar[0], "sutun": "*satir*", "bozma": "B14",
                         "gercek": "", "bozuk": yeni, "kurtarilabilir": True})
        sonuc.append(yeni)
        i += 1
    return "\n".join(sonuc) + "\n"


def boz(temiz: dict[str, pd.DataFrame], seed: int, oran_carpani: float = 1.0,
        oranlar: list[tuple[str, str, str, float]] | None = None,
        satir_oranlari: dict[str, float] | None = None, surpriz: bool = False) -> Sonuc:
    rng = random.Random(seed + 1)
    oranlar = oranlar or VARSAYILAN_ORANLAR
    satir_oranlari = {**SATIR_ORANLARI, **(satir_oranlari or {})}
    kayitlar: list[dict] = []
    ham = {t: df.to_dict("records") for t, df in temiz.items()}  # Tipli gerçek değerler.
    kirli = {t: metne_cevir(t, df).to_dict("records") for t, df in temiz.items()}
    bozulan: set[tuple[str, int, str]] = set()

    def kaydet(tablo, anahtar, sutun, bozma, gercek, bozuk):
        kayitlar.append({"tablo": tablo, "anahtar": anahtar, "sutun": sutun, "bozma": bozma,
                         "gercek": gercek, "bozuk": bozuk,
                         "kurtarilabilir": (tablo, sutun, bozma) not in KURTARILAMAZ})

    # B1: tekrarlanan müşteriler ve bazı siparişlerinin yeni kayda bağlanması.
    musteri_sayisi = len(kirli["musteriler"])
    eslesme = []
    siparis_by_musteri: dict[str, list[int]] = {}
    for i, s in enumerate(kirli["siparisler"]):
        siparis_by_musteri.setdefault(s["musteri_id"], []).append(i)
    sonraki = musteri_sayisi + 1
    yeni_satirlar = []
    for satir in list(kirli["musteriler"]):
        if rng.random() >= satir_oranlari["B1"]:
            continue
        for _ in range(1 if rng.random() < 0.8 else 2):
            yeni_id = f"M{sonraki:05d}"
            sonraki += 1
            yeni_satirlar.append(_musteri_tekrari(rng, satir, yeni_id))
            eslesme.append({"tekrar_id": yeni_id, "asil_id": satir["musteri_id"]})
            kaydet("musteriler", yeni_id, "*satir*", "B1", satir["musteri_id"], yeni_id)
            for j in siparis_by_musteri.get(satir["musteri_id"], []):
                if rng.random() < satir_oranlari["B1_siparis"] and ("siparisler", j, "musteri_id") not in bozulan:
                    kirli["siparisler"][j]["musteri_id"] = yeni_id
                    bozulan.add(("siparisler", j, "musteri_id"))
                    kaydet("siparisler", kirli["siparisler"][j]["siparis_id"], "musteri_id", "B1",
                           satir["musteri_id"], yeni_id)

    # Hücre bozmaları.
    for tablo, sutun, bozma, oran in oranlar:
        anahtar_sutun = R.ANAHTARLAR[tablo]
        for i, satir in enumerate(kirli[tablo]):
            if (tablo, i, sutun) in bozulan or rng.random() >= oran * oran_carpani:
                continue
            gercek = ham[tablo][i][sutun]
            yeni = hucre_boz(rng, tablo, sutun, bozma, gercek, ham[tablo][i], surpriz)
            if yeni is None or yeni == satir[sutun]:
                continue
            satir[sutun] = yeni
            bozulan.add((tablo, i, sutun))
            kaydet(tablo, satir[anahtar_sutun], sutun, bozma, kirli_gercek(tablo, sutun, gercek), yeni)

    _kurtarilabilirlik_guncelle(kayitlar, ham)

    musteri_df = pd.DataFrame(kirli["musteriler"] + yeni_satirlar)
    musteri_df = musteri_df.sample(frac=1, random_state=seed).reset_index(drop=True)

    # B2: birebir tekrar eden sipariş satırları, orijinalin yakınına eklenir.
    siparisler = list(kirli["siparisler"])
    for s in list(siparisler):
        if rng.random() < satir_oranlari["B2"]:
            for _ in range(rng.choice([1, 1, 2])):
                siparisler.insert(min(len(siparisler), siparisler.index(s) + rng.randint(1, 40)), dict(s))
                kaydet("siparisler", s["siparis_id"], "*satir*", "B2", "", s["siparis_id"])

    tablolar = {"musteriler": musteri_df, "urunler": pd.DataFrame(kirli["urunler"]),
                "siparisler": pd.DataFrame(siparisler)}
    metinler = {t: csv_yaz(df) for t, df in tablolar.items()}
    metinler["siparisler"] = _satir_boz(rng, metinler["siparisler"], satir_oranlari["B14"] * oran_carpani,
                                        kayitlar, surpriz)
    kayit = pd.DataFrame(kayitlar, columns=["tablo", "anahtar", "sutun", "bozma", "gercek", "bozuk",
                                            "kurtarilabilir"])
    return Sonuc(tablolar, metinler, kayit, pd.DataFrame(eslesme, columns=["tekrar_id", "asil_id"]))


# Bilgiyi yok eden bozmalar. Aynı türetme grubunda iki tanesi birden olursa değerler kurtarılamaz.
_BILGI_KAYBI = {("siparisler", "adet", "B7"), ("siparisler", "indirim_orani", "B5"),
                ("siparisler", "toplam_tutar", "B5"), ("siparisler", "toplam_tutar", "B12")}


def _kurtarilabilirlik_guncelle(kayitlar: list[dict], ham: dict[str, list[dict]]):
    """Tek hücreye bakınca kurtarılabilir görünen ama aynı satırdaki başka bir kayıpla birlikte
    kurtarılamaz hale gelen hücreleri işaretler."""
    hucre = {(k["tablo"], k["anahtar"], k["sutun"]): k for k in kayitlar if k["sutun"] != "*satir*"}
    kayip = defaultdict(list)
    for (tablo, anahtar_deger, sutun), k in hucre.items():
        if (tablo, sutun, k["bozma"]) in _BILGI_KAYBI:
            kayip[anahtar_deger].append(k)
    for grup in kayip.values():
        if len(grup) >= 2:  # adet, indirim ve toplamdan ikisi kayıpsa denklem çözülemez.
            for k in grup:
                k["kurtarilabilir"] = False
    siparis_sayisi = defaultdict(int)
    for s in ham["siparisler"]:
        siparis_sayisi[s["urun_id"]] += 1
    for (tablo, anahtar_deger, sutun), k in hucre.items():
        if (tablo, sutun, k["bozma"]) == ("siparisler", "teslim_tarihi", "B5"):
            k["kurtarilabilir"] = k["gercek"] == ""  # Gerçekte boşsa doğru cevap boştur.
        elif (tablo, sutun, k["bozma"]) == ("musteriler", "il", "B5"):
            ilce = hucre.get(("musteriler", anahtar_deger, "ilce"))
            k["kurtarilabilir"] = not (ilce and ilce["bozma"] == "B5")
        elif (tablo, sutun, k["bozma"]) == ("urunler", "birim_fiyat", "B5"):
            k["kurtarilabilir"] = siparis_sayisi[anahtar_deger] > 0


def kirli_gercek(tablo: str, sutun: str, v) -> str:
    """Kayıt için gerçek değerin metin hali."""
    tip = R.SEMA[tablo][sutun]
    if tip in ("para", "oran"):
        return f"{v:.2f}"
    if tip == "adet":
        return str(int(v))
    return str(v)
