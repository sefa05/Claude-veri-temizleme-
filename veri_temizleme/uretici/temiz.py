"""Temiz (gerçek doğru) e-ticaret verisini üretir. Tüm iş kurallarını sağlar."""

from __future__ import annotations

import math
import random
from datetime import date, timedelta

import pandas as pd

from .. import referans as R
from ..metin import ascii_fold, tr_lower


def _agirlikli(rng: random.Random, secenekler: dict):
    return rng.choices(list(secenekler), weights=list(secenekler.values()))[0]


def _tarih(rng: random.Random, bas: date, son: date) -> date:
    return bas + timedelta(days=rng.randint(0, (son - bas).days))


def musteriler_uret(rng: random.Random, adet: int) -> pd.DataFrame:
    iller = list(R.IL_ILCELER)
    il_agirlik = [R.IL_ILCELER[i][1] for i in iller]
    kullanilan_epostalar: set[str] = set()
    satirlar = []
    for n in range(1, adet + 1):
        cinsiyet = rng.choice(R.CINSIYETLER)
        ad = rng.choice(R.KADIN_ADLARI if cinsiyet == "Kadın" else R.ERKEK_ADLARI)
        soyad = rng.choice(R.SOYADLARI)
        il = rng.choices(iller, weights=il_agirlik)[0]
        ilce = rng.choice(R.IL_ILCELER[il][0])
        dogum = _tarih(rng, date(1950, 1, 1), date(2006, 12, 31))
        kayit = _tarih(rng, date(2021, 1, 1), date(2023, 12, 31))
        taban = ascii_fold(tr_lower(f"{ad}.{soyad}")).replace(" ", "")
        eposta = ""
        while not eposta or eposta in kullanilan_epostalar:
            ek = rng.choice(["", str(rng.randint(1, 99)), str(dogum.year), str(dogum.year)[2:]])
            eposta = f"{taban}{ek}@{_agirlikli(rng, R.EPOSTA_ALANLARI)}"
        kullanilan_epostalar.add(eposta)
        tel = f"5{rng.choice('0345')}{rng.randint(0, 9)}{rng.randint(0, 9999999):07d}"
        satirlar.append({
            "musteri_id": f"M{n:05d}", "ad": ad, "soyad": soyad, "eposta": eposta,
            "telefon": f"+90 {tel[:3]} {tel[3:6]} {tel[6:8]} {tel[8:]}",
            "dogum_tarihi": dogum.isoformat(), "cinsiyet": cinsiyet, "il": il, "ilce": ilce,
            "kayit_tarihi": kayit.isoformat(),
        })
    return pd.DataFrame(satirlar)


def urunler_uret(rng: random.Random, adet: int) -> pd.DataFrame:
    kategoriler = list(R.KATEGORILER)
    kullanilan: set[str] = set()
    satirlar = []
    for n in range(1, adet + 1):
        kategori = rng.choice(kategoriler)
        tipler, markalar, (alt, ust) = R.KATEGORILER[kategori]
        ad = ""
        while not ad or ad in kullanilan:
            marka = rng.choice(markalar)
            ad = (f"{marka} {rng.choice(tipler)} "
                  f"{rng.choice(['Pro', 'Plus', 'Lite', 'Max', 'Classic', 'Slim', 'Mini', 'Ultra'])} "
                  f"{rng.randint(1, 99)}")
        kullanilan.add(ad)
        # Log-düzgün dağılım: ucuz ürün çok, pahalı ürün az.
        fiyat = math.exp(rng.uniform(math.log(alt), math.log(ust)))
        fiyat = round(fiyat, 0) - 0.01 if fiyat > 100 else round(fiyat, 2)
        satirlar.append({"urun_id": f"U{n:04d}", "urun_adi": ad, "kategori": kategori,
                         "marka": marka, "birim_fiyat": round(fiyat, 2)})
    return pd.DataFrame(satirlar)


def siparisler_uret(rng: random.Random, adet: int, musteriler: pd.DataFrame, urunler: pd.DataFrame) -> pd.DataFrame:
    # Bazı müşteriler çok sipariş verir: ağırlıklar Pareto benzeri.
    m_ids = musteriler["musteri_id"].tolist()
    m_agirlik = [rng.paretovariate(1.5) for _ in m_ids]
    m_kayit = dict(zip(musteriler["musteri_id"], musteriler["kayit_tarihi"]))
    u_ids = urunler["urun_id"].tolist()
    u_fiyat = dict(zip(urunler["urun_id"], urunler["birim_fiyat"]))
    u_agirlik = [1 / (0.3 + f / 1000) for f in urunler["birim_fiyat"]]

    # Sipariş günleri: hafta sonu ve Kasım (indirim dönemi) daha yoğun.
    gunler, gun_agirlik = [], []
    g = date(2023, 1, 1)
    while g <= date(2024, 12, 31):
        gunler.append(g)
        gun_agirlik.append(1.0 + 0.4 * (g.weekday() >= 5) + 1.5 * (g.month == 11))
        g += timedelta(days=1)

    satirlar = []
    for n in range(1, adet + 1):
        mid = rng.choices(m_ids, weights=m_agirlik)[0]
        uid = rng.choices(u_ids, weights=u_agirlik)[0]
        kayit = date.fromisoformat(m_kayit[mid])
        tarih = rng.choices(gunler, weights=gun_agirlik)[0]
        if tarih < kayit:
            tarih = _tarih(rng, max(kayit, date(2023, 1, 1)), date(2024, 12, 31))
        miktar = rng.choices([1, 2, 3, 4, 5, 6, 8, 10], weights=[60, 20, 8, 5, 3, 2, 1, 1])[0]
        fiyat = u_fiyat[uid]
        indirim = _agirlikli(rng, R.INDIRIM_ORANLARI)
        durum = _agirlikli(rng, R.DURUMLAR)
        if durum in ("Kargoda", "Hazırlanıyor") and tarih < date(2024, 12, 20):
            durum = "Teslim Edildi"  # Eski siparişler yolda kalmaz.
        teslim_gunu = tarih + timedelta(days=rng.randint(1, 7))
        if durum not in R.TESLIMSIZ_DURUMLAR and teslim_gunu > date(2024, 12, 31):
            durum = "Kargoda"  # Veri çekildiğinde henüz teslim edilmemiş.
        teslim = "" if durum in R.TESLIMSIZ_DURUMLAR else teslim_gunu.isoformat()
        satirlar.append({
            "siparis_id": f"S{n:06d}", "musteri_id": mid, "urun_id": uid, "siparis_tarihi": tarih.isoformat(),
            "adet": miktar, "birim_fiyat": fiyat, "indirim_orani": indirim,
            "toplam_tutar": round(miktar * fiyat * (1 - indirim), 2),
            "odeme_yontemi": _agirlikli(rng, R.ODEME_YONTEMLERI), "kargo_firmasi": _agirlikli(rng, R.KARGO_FIRMALARI),
            "teslim_tarihi": teslim, "durum": durum,
        })
    df = pd.DataFrame(satirlar)
    return df.sort_values(["siparis_tarihi", "siparis_id"]).reset_index(drop=True).assign(
        siparis_id=[f"S{n:06d}" for n in range(1, adet + 1)])


def temiz_veri_uret(seed: int, siparis: int, musteri: int, urun: int) -> dict[str, pd.DataFrame]:
    rng = random.Random(seed)
    musteriler = musteriler_uret(rng, musteri)
    urunler = urunler_uret(rng, urun)
    siparisler = siparisler_uret(rng, siparis, musteriler, urunler)
    return {"musteriler": musteriler, "urunler": urunler, "siparisler": siparisler}
