"""Kural tabanlı temizleme hattı.

Hat LLM kullanmaz. Güvenle çözemediği hücreleri `belirsizler` listesine yazar. Bir `cozucu` verilirse (hibrit
yöntem) bu hücreler ona sorulur, verilmezse kural kendi varsayılanını kullanır ya da hücreyi boş bırakır.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

import pandas as pd
from rapidfuzz import fuzz, process

from .. import referans as R
from ..metin import anahtar, tr_title
from . import cozumleyiciler as C
from .okuma import oku
from .sozluk import IlEslestirici, anahtar_joker, ilce_eslestirici, secenek_eslestirici

# Veri 2025 başında çekildi: bu tarihten sonraki sipariş veya kayıt tarihi geçersizdir.
KESIM_TARIHI = date(2025, 1, 1)
EN_ESKI_TARIH = date(2015, 1, 1)
DOGUM_ARALIGI = (date(1920, 1, 1), date(2010, 12, 31))
AZAMI_TESLIM_GUNU = 30


@dataclass
class Belirsiz:
    """Kuralın güvenle çözemediği bir hücre."""
    id: str
    tablo: str
    anahtar: str
    sutun: str
    ham: str
    tur: str
    adaylar: list[str] = field(default_factory=list)
    baglam: dict[str, str] = field(default_factory=dict)
    varsayilan: str | None = None


@dataclass
class BelirsizCift:
    id: str
    a: dict[str, str]
    b: dict[str, str]
    kanit: list[str]


class Cozucu(Protocol):
    def hucreleri_coz(self, hucreler: list[Belirsiz]) -> dict[str, str | None]: ...

    def ciftleri_coz(self, ciftler: list[BelirsizCift]) -> dict[str, bool]: ...


def _nesne(df: pd.DataFrame, degerler) -> pd.Series:
    """pandas'ın sütunu str tipine çevirmesini engeller: sütunlar karışık tipli değer taşır."""
    return pd.Series(list(degerler), index=df.index, dtype=object)


def _bos(v) -> bool:
    return v is None or (isinstance(v, float) and v != v)


class KuralTemizleyici:
    def __init__(self, cozucu: Cozucu | None = None):
        self.cozucu = cozucu
        self.belirsizler: list[Belirsiz] = []
        self.belirsiz_ciftler: list[BelirsizCift] = []
        self.sorunlar: list[dict] = []
        self.karantina: list[dict] = []
        self.istatistik: Counter = Counter()
        self._uygula: dict[str, tuple[pd.DataFrame, int, str]] = {}
        self._il = IlEslestirici()
        self._ilce = ilce_eslestirici()
        self._secenek = {s: secenek_eslestirici(s) for s in R.SECENEKLER}

    # --- Yardımcılar -------------------------------------------------------------------------------------------

    def _belirsiz(self, df: pd.DataFrame, i: int, tablo: str, sutun: str, ham: str, tur: str,
                  adaylar=None, varsayilan=None, baglam_sutunlari=None):
        anahtar_sutun = R.ANAHTARLAR[tablo]
        kimlik = f"{tablo}:{df.at[i, anahtar_sutun]}:{sutun}:{i}"
        baglam = {s: str(self._ham[tablo][i].get(s, "")) for s in (baglam_sutunlari or [])}
        self.belirsizler.append(Belirsiz(kimlik, tablo, str(df.at[i, anahtar_sutun]), sutun, ham, tur,
                                         list(adaylar or []), baglam, varsayilan))
        self._uygula[kimlik] = (df, i, sutun)

    def _sorun(self, tablo, anahtar_deger, sutun, ham, temiz, islem):
        self.sorunlar.append({"tablo": tablo, "anahtar": anahtar_deger, "sutun": sutun, "ham": ham,
                              "temiz": "" if _bos(temiz) else temiz, "islem": islem})
        self.istatistik[f"{tablo}.{islem}"] += 1

    # --- Ana akış ----------------------------------------------------------------------------------------------

    def temizle(self, kirli_klasor: Path) -> dict[str, pd.DataFrame]:
        kirli_klasor = Path(kirli_klasor)
        okunan = {t: oku(kirli_klasor / f"{t}.csv", t) for t in R.SEMA}
        for o in okunan.values():
            self.karantina.extend(o.karantina)
            self.istatistik["onarilan_satir"] += o.onarilan
        self._ham = {t: o.satirlar for t, o in okunan.items()}
        tablolar = {t: pd.DataFrame(o.satirlar, columns=list(R.SEMA[t])).astype(object)
                    for t, o in okunan.items()}
        for t, df in tablolar.items():
            self.istatistik[f"{t}.ham_satir"] = len(df)
            for s in df.columns:
                df[s] = _nesne(df, (C.on_temizle(v) for v in df[s]))

        urunler = self._urunler(tablolar["urunler"])
        musteriler = self._musteriler(tablolar["musteriler"])
        siparisler = self._siparisler(tablolar["siparisler"])
        self._belirsizleri_coz()
        urunler, siparisler = self._turet_fiyat(urunler, siparisler)
        siparisler = self._turet_tutar(siparisler)
        musteriler = self._turet_musteri(musteriler)
        musteriler, eslesme = self._tekrar_birlestir(musteriler)
        siparisler = self._siparis_bagla(siparisler, eslesme)
        self.eslesme = eslesme
        return {"musteriler": musteriler, "urunler": urunler, "siparisler": siparisler}

    def _belirsizleri_coz(self):
        self.istatistik["belirsiz_hucre"] = len(self.belirsizler)
        cevaplar = self.cozucu.hucreleri_coz(self.belirsizler) if self.cozucu and self.belirsizler else {}
        for b in self.belirsizler:
            df, i, sutun = self._uygula[b.id]
            if b.id in cevaplar:
                deger = self._dogrula(b, cevaplar[b.id])
                islem = "llm_cozdu" if deger is not None else "llm_bos_birakti"
            else:
                deger, islem = b.varsayilan, ("varsayilan" if b.varsayilan is not None else "bosaltildi")
            df.at[i, sutun] = deger
            self._sorun(b.tablo, b.anahtar, sutun, b.ham, deger, f"belirsiz_{islem}")

    def _dogrula(self, b: Belirsiz, cevap) -> str | None:
        """Çözücünün cevabını hücre tipine göre doğrular. Geçersiz cevap boş sayılır."""
        if _bos(cevap) or str(cevap).strip() == "":
            return None
        cevap = str(cevap).strip()
        if b.tur in ("secenek", "il", "ilce", "tarih_secim"):
            return cevap if cevap in b.adaylar else None
        if b.tur == "tarih":
            aday = C.tarih_adaylari(cevap)
            return aday[0].isoformat() if len(aday) == 1 else None
        if b.tur == "isim":
            return tr_title(cevap) if re.fullmatch(r"[^\d?@]+", cevap) else None
        if b.tur == "eposta":
            cevap = C.eposta_on(cevap)
            return cevap if C.EPOSTA_DESENI.fullmatch(cevap) else None
        if b.tur == "cinsiyet":
            return cevap if cevap in R.CINSIYETLER else None
        if b.tur == "sayi":
            v = C.para(cevap)
            return None if v is None else v
        return cevap

    # --- Ürünler -----------------------------------------------------------------------------------------------

    def _urunler(self, df: pd.DataFrame) -> pd.DataFrame:
        t = "urunler"
        df["urun_id"] = _nesne(df, (C.id_normalize(v, "U", 4) for v in df["urun_id"]))
        df["urun_adi"] = _nesne(df, self._kelime_onar(df["urun_adi"], baslik=False))
        markalar = self._sozluk([v for v in df["marka"] if not C.yer_tutucu_mu(v)])
        for i in df.index:
            ham = df.at[i, "marka"]
            if C.yer_tutucu_mu(ham):
                ad = df.at[i, "urun_adi"] or ""
                bulunan = [m for m in markalar.values() if anahtar(ad).startswith(anahtar(m))]
                df.at[i, "marka"] = max(bulunan, key=len) if bulunan else None
                self._sorun(t, df.at[i, "urun_id"], "marka", ham, df.at[i, "marka"], "turetildi")
            else:
                df.at[i, "marka"] = markalar.get(anahtar(ham), ham)
            ham = df.at[i, "kategori"]
            df.at[i, "kategori"] = self._secenek_coz(df, i, t, "kategori", ham, self._secenek["kategori"],
                                                     ["urun_adi", "marka"])
            df.at[i, "birim_fiyat"] = self._sayi(df, i, t, "birim_fiyat", C.para)
        return df

    # --- Müşteriler --------------------------------------------------------------------------------------------

    def _musteriler(self, df: pd.DataFrame) -> pd.DataFrame:
        t = "musteriler"
        df["musteri_id"] = _nesne(df, (C.id_normalize(v, "M", 5) for v in df["musteri_id"]))
        for s in ("ad", "soyad"):
            df[s] = _nesne(df, self._kelime_onar(df[s], baslik=True, tablo=t, sutun=s, df=df))
        epostalar = [C.eposta_on(v) for v in df["eposta"] if not C.yer_tutucu_mu(v)]
        alan_sayim = Counter(e.split("@", 1)[1] for e in epostalar if "@" in e)
        bilinen_alanlar = [a for a, n in alan_sayim.items() if n >= max(5, 0.01 * len(epostalar))]
        for i in df.index:
            df.at[i, "eposta"] = self._eposta(df, i, df.at[i, "eposta"], bilinen_alanlar)
            ham = df.at[i, "telefon"]
            df.at[i, "telefon"] = None if C.yer_tutucu_mu(ham) else C.telefon(ham)
            if df.at[i, "telefon"] is None and not C.yer_tutucu_mu(ham):
                self._sorun(t, df.at[i, "musteri_id"], "telefon", ham, None, "gecersiz")
            df.at[i, "dogum_tarihi"] = self._tarih(df, i, t, "dogum_tarihi", *DOGUM_ARALIGI)
            df.at[i, "kayit_tarihi"] = self._tarih(df, i, t, "kayit_tarihi", EN_ESKI_TARIH, KESIM_TARIHI)
            ham = df.at[i, "cinsiyet"]
            df.at[i, "cinsiyet"] = None if C.yer_tutucu_mu(ham) else \
                self._secenek_coz(df, i, t, "cinsiyet", ham, self._secenek["cinsiyet"], ["ad"])
            ham = df.at[i, "il"]
            df.at[i, "il"] = None if C.yer_tutucu_mu(ham) else \
                self._secenek_coz(df, i, t, "il", ham, self._il, ["ilce"], tur="il")
            ham = df.at[i, "ilce"]
            df.at[i, "ilce"] = None if C.yer_tutucu_mu(ham) else \
                self._secenek_coz(df, i, t, "ilce", ham, self._ilce, ["il"], tur="ilce")
        return df

    def _eposta(self, df, i, ham: str, bilinen_alanlar: list[str]) -> str | None:
        if C.yer_tutucu_mu(ham):
            return None
        e = C.eposta_on(ham)
        if "@" not in e:
            alan = next((a for a in bilinen_alanlar if e.endswith(a) and len(e) > len(a)), None)
            if alan:
                e = f"{e[:-len(alan)]}@{alan}"
        if "@" in e:
            yerel, alan = e.split("@", 1)
            if alan not in bilinen_alanlar and bilinen_alanlar:
                en_iyi = process.extractOne(alan, bilinen_alanlar, scorer=fuzz.ratio)
                if en_iyi and en_iyi[1] >= 80:
                    alan = en_iyi[0]
            e = f"{yerel}@{alan}"
        if C.EPOSTA_DESENI.fullmatch(e):
            if e != ham:
                self._sorun("musteriler", df.at[i, "musteri_id"], "eposta", ham, e, "duzeltildi")
            return e
        self._belirsiz(df, i, "musteriler", "eposta", ham, "eposta", baglam_sutunlari=["ad", "soyad"])
        return None

    # --- Siparişler --------------------------------------------------------------------------------------------

    def _siparisler(self, df: pd.DataFrame) -> pd.DataFrame:
        t = "siparisler"
        for sutun, (onek, basamak) in R.ID_ONEKLERI.items():
            if sutun in df.columns:
                yeni = [C.id_normalize(v, onek, basamak) for v in df[sutun]]
                for i, (ham, y) in enumerate(zip(df[sutun], yeni)):
                    if ham != y:
                        self._sorun(t, df.at[i, "siparis_id"], sutun, ham, y, "duzeltildi")
                df[sutun] = _nesne(df, yeni)
        for i in df.index:
            self._siparis_tarihleri(df, i)
            ham = df.at[i, "adet"]
            df.at[i, "adet"] = None if C.yer_tutucu_mu(ham) else C.adet(ham)
            df.at[i, "birim_fiyat"] = self._sayi(df, i, t, "birim_fiyat", C.para)
            df.at[i, "indirim_orani"] = self._sayi(df, i, t, "indirim_orani", C.oran)
            df.at[i, "toplam_tutar"] = self._sayi(df, i, t, "toplam_tutar", C.para)
            for s in ("odeme_yontemi", "kargo_firmasi", "durum"):
                ham = df.at[i, s]
                df.at[i, s] = None if C.yer_tutucu_mu(ham) else \
                    self._secenek_coz(df, i, t, s, ham, self._secenek[s], ["durum", "odeme_yontemi"])
        return df

    def _siparis_tarihleri(self, df, i):
        t = "siparisler"
        ham_s, ham_t = df.at[i, "siparis_tarihi"], df.at[i, "teslim_tarihi"]
        s_aday = [d for d in C.tarih_adaylari(ham_s) if EN_ESKI_TARIH <= d < KESIM_TARIHI]
        t_aday = C.tarih_adaylari(ham_t)
        # Bağlam: teslim tarihi sipariş tarihinden sonra ve en fazla 30 gün içinde olmalı.
        uyumlu = [(s, d) for s in s_aday for d in t_aday if 0 <= (d - s).days <= AZAMI_TESLIM_GUNU]
        if s_aday and t_aday and uyumlu:
            s_sec = {s for s, _ in uyumlu}
            t_sec = {d for _, d in uyumlu}
        else:
            s_sec, t_sec = set(s_aday), set()
            if t_aday and not s_aday:
                t_sec = set(t_aday)
        anahtar_deger = df.at[i, "siparis_id"]
        for sutun, ham, secim, adaylar in (("siparis_tarihi", ham_s, s_sec, s_aday),
                                           ("teslim_tarihi", ham_t, t_sec, t_aday)):
            sirali = [d for d in adaylar if d in secim]
            if len(sirali) == 1:
                df.at[i, sutun] = sirali[0].isoformat()
                if ham != df.at[i, sutun]:
                    self._sorun(t, anahtar_deger, sutun, ham, df.at[i, sutun], "duzeltildi")
            elif len(sirali) > 1:
                df.at[i, sutun] = None
                self._belirsiz(df, i, t, sutun, ham, "tarih_secim", [d.isoformat() for d in sirali],
                               sirali[0].isoformat(), ["siparis_tarihi", "teslim_tarihi", "durum"])
            else:
                df.at[i, sutun] = None
                if not C.yer_tutucu_mu(ham):
                    self._sorun(t, anahtar_deger, sutun, ham, None, "gecersiz")

    # --- Türetme -----------------------------------------------------------------------------------------------

    def _turet_fiyat(self, urunler, siparisler):
        fiyat = dict(zip(urunler["urun_id"], urunler["birim_fiyat"]))
        siparis_fiyat = defaultdict(list)
        for u, f in zip(siparisler["urun_id"], siparisler["birim_fiyat"]):
            if not _bos(f):
                siparis_fiyat[u].append(f)
        for i in urunler.index:
            if _bos(urunler.at[i, "birim_fiyat"]) and siparis_fiyat.get(urunler.at[i, "urun_id"]):
                degerler = Counter(siparis_fiyat[urunler.at[i, "urun_id"]])
                urunler.at[i, "birim_fiyat"] = degerler.most_common(1)[0][0]
                fiyat[urunler.at[i, "urun_id"]] = urunler.at[i, "birim_fiyat"]
                self._sorun("urunler", urunler.at[i, "urun_id"], "birim_fiyat", "", urunler.at[i, "birim_fiyat"],
                            "turetildi")
        for i in siparisler.index:
            if _bos(siparisler.at[i, "birim_fiyat"]) and not _bos(fiyat.get(siparisler.at[i, "urun_id"])):
                siparisler.at[i, "birim_fiyat"] = fiyat[siparisler.at[i, "urun_id"]]
                self._sorun("siparisler", siparisler.at[i, "siparis_id"], "birim_fiyat", "",
                            siparisler.at[i, "birim_fiyat"], "turetildi")
        return urunler, siparisler

    def _turet_tutar(self, df):
        t = "siparisler"
        for i in df.index:
            a, f, ind, top = (df.at[i, s] for s in ("adet", "birim_fiyat", "indirim_orani", "toplam_tutar"))
            k = df.at[i, "siparis_id"]
            gecerli = lambda x: not _bos(x) and float(x).is_integer() and 1 <= x <= 100  # noqa: E731
            if not gecerli(a):
                ham = a
                aday = None
                if not any(_bos(x) for x in (f, ind, top)) and f > 0:
                    oran = top / (f * (1 - ind))
                    if abs(oran - round(oran)) < 0.01 and gecerli(round(oran)):
                        aday = round(oran)
                if aday is None and not _bos(a) and gecerli(-a):
                    aday = -a
                a = aday
                df.at[i, "adet"] = a
                self._sorun(t, k, "adet", ham, a, "turetildi" if a is not None else "bosaltildi")
            if _bos(ind) and not any(_bos(x) for x in (a, f, top)) and a * f > 0:
                tahmin = 1 - top / (a * f)
                yuvarlak = round(tahmin * 20) / 20
                if abs(tahmin - yuvarlak) < 0.003 and 0 <= yuvarlak < 1:
                    ind = round(yuvarlak, 2)
                    df.at[i, "indirim_orani"] = ind
                    self._sorun(t, k, "indirim_orani", "", ind, "turetildi")
            if not any(_bos(x) for x in (a, f, ind)):
                beklenen = round(a * f * (1 - ind), 2)
                if _bos(top) or abs(top - beklenen) > 0.011:
                    df.at[i, "toplam_tutar"] = beklenen
                    self._sorun(t, k, "toplam_tutar", top, beklenen, "yeniden_hesaplandi")
        return df

    def _turet_musteri(self, df):
        t = "musteriler"
        ad_cinsiyet: dict[str, Counter] = defaultdict(Counter)
        for ad, c in zip(df["ad"], df["cinsiyet"]):
            if not _bos(ad) and not _bos(c):
                ad_cinsiyet[ad][c] += 1
        for i in df.index:
            if _bos(df.at[i, "cinsiyet"]) and not _bos(df.at[i, "ad"]):
                sayim = ad_cinsiyet.get(df.at[i, "ad"])
                if sayim and sum(sayim.values()) >= 3 and sayim.most_common(1)[0][1] / sum(sayim.values()) >= 0.9:
                    df.at[i, "cinsiyet"] = sayim.most_common(1)[0][0]
                    self._sorun(t, df.at[i, "musteri_id"], "cinsiyet", "", df.at[i, "cinsiyet"], "turetildi")
            if _bos(df.at[i, "il"]) and not _bos(df.at[i, "ilce"]):
                df.at[i, "il"] = R.ILCE_IL.get(df.at[i, "ilce"])
                self._sorun(t, df.at[i, "musteri_id"], "il", "", df.at[i, "il"], "turetildi")
        return df

    # --- Tekrar birleştirme ------------------------------------------------------------------------------------

    def _tekrar_birlestir(self, df: pd.DataFrame):
        kayitlar = df.to_dict("records")
        bloklar: dict[frozenset, list[int]] = defaultdict(list)
        for i, r in enumerate(kayitlar):
            if not _bos(r["ad"]) and not _bos(r["soyad"]):
                bloklar[frozenset((anahtar(r["ad"]), anahtar(r["soyad"])))].append(i)
        ebeveyn = list(range(len(kayitlar)))

        def kok(x):
            while ebeveyn[x] != x:
                ebeveyn[x] = ebeveyn[ebeveyn[x]]
                x = ebeveyn[x]
            return x

        bekleyen = []
        for uyeler in bloklar.values():
            for x_i, x in enumerate(uyeler):
                for y in uyeler[x_i + 1:]:
                    karar, kanit = tekrar_karari(kayitlar[x], kayitlar[y])
                    if karar == "evet":
                        ebeveyn[kok(x)] = kok(y)
                    elif karar == "belirsiz":
                        bekleyen.append((x, y, kanit))
        self.istatistik["belirsiz_cift"] = len(bekleyen)
        if bekleyen and self.cozucu:
            gorunen = ["musteri_id", "ad", "soyad", "eposta", "telefon", "dogum_tarihi", "il", "ilce",
                       "kayit_tarihi"]
            self.belirsiz_ciftler = [
                BelirsizCift(f"cift:{kayitlar[x]['musteri_id']}:{kayitlar[y]['musteri_id']}",
                             {s: "" if _bos(kayitlar[x][s]) else str(kayitlar[x][s]) for s in gorunen},
                             {s: "" if _bos(kayitlar[y][s]) else str(kayitlar[y][s]) for s in gorunen}, kanit)
                for x, y, kanit in bekleyen]
            cevap = self.cozucu.ciftleri_coz(self.belirsiz_ciftler)
            for (x, y, _), c in zip(bekleyen, self.belirsiz_ciftler):
                if cevap.get(c.id):
                    ebeveyn[kok(x)] = kok(y)
        kumeler: dict[int, list[int]] = defaultdict(list)
        for i in range(len(kayitlar)):
            kumeler[kok(i)].append(i)
        cikti, eslesme = [], {}
        for uyeler in kumeler.values():
            uyeler.sort(key=lambda i: kayitlar[i]["musteri_id"] or "~")
            birlesik = dict(kayitlar[uyeler[0]])
            for j in uyeler[1:]:
                eslesme[kayitlar[j]["musteri_id"]] = birlesik["musteri_id"]
                for s, v in kayitlar[j].items():
                    if _bos(birlesik.get(s)) and not _bos(v) and s != "kayit_tarihi":
                        birlesik[s] = v
            cikti.append(birlesik)
        self.istatistik["birlesen_musteri"] = len(eslesme)
        sonuc = pd.DataFrame(cikti, columns=df.columns).astype(object).sort_values("musteri_id").reset_index(drop=True)
        return sonuc, eslesme

    def _siparis_bagla(self, df, eslesme):
        df["musteri_id"] = _nesne(df, (eslesme.get(m, m) for m in df["musteri_id"]))
        once = len(df)
        df = df.drop_duplicates("siparis_id", keep="first").sort_values("siparis_id").reset_index(drop=True)
        self.istatistik["silinen_tekrar_siparis"] = once - len(df)
        return df

    # --- Hücre tipleri -----------------------------------------------------------------------------------------

    def _sayi(self, df, i, tablo, sutun, cozumleyici):
        ham = df.at[i, sutun]
        if C.yer_tutucu_mu(ham):
            return None
        v = cozumleyici(ham)
        if v is None:
            self._sorun(tablo, df.at[i, R.ANAHTARLAR[tablo]], sutun, ham, None, "gecersiz")
        return v

    def _tarih(self, df, i, tablo, sutun, alt: date, ust: date):
        ham = df.at[i, sutun]
        adaylar = [d for d in C.tarih_adaylari(ham) if alt <= d < ust]
        if len(adaylar) >= 1:
            # Birden fazla yorum varsa Türkiye biçimi (gün/ay) varsayılır.
            deger = adaylar[0].isoformat()
            if deger != ham:
                self._sorun(tablo, df.at[i, R.ANAHTARLAR[tablo]], sutun, ham, deger,
                            "duzeltildi" if len(adaylar) == 1 else "varsayilan")
            return deger
        if not C.yer_tutucu_mu(ham):
            self._sorun(tablo, df.at[i, R.ANAHTARLAR[tablo]], sutun, ham, None, "gecersiz")
        return None

    def _secenek_coz(self, df, i, tablo, sutun, ham, eslestirici, baglam, tur="secenek"):
        if C.yer_tutucu_mu(ham):
            return None
        e = eslestirici.eslestir(ham)
        if e.deger is not None:
            if e.deger != ham:
                self._sorun(tablo, df.at[i, R.ANAHTARLAR[tablo]], sutun, ham, e.deger, "duzeltildi")
            return e.deger
        self._belirsiz(df, i, tablo, sutun, ham, tur, e.adaylar, baglam_sutunlari=baglam)
        return None

    def _sozluk(self, degerler, baslik: bool = False) -> dict[str, str]:
        """anahtar -> en sık görülen yazım. '?' içeren yazımlar sayılmaz."""
        sayim: dict[str, Counter] = defaultdict(Counter)
        for v in degerler:
            if v and "?" not in v:
                sayim[anahtar(v)][tr_title(v) if baslik else v] += 1
        return {k: c.most_common(1)[0][0] for k, c in sayim.items()}

    def _kelime_onar(self, seri: pd.Series, baslik: bool, tablo=None, sutun=None, df=None) -> list:
        """Kelime sözlüğüyle yazımı birleştirir, '?' ile bozulmuş kelimeleri sözlükten tamamlar."""
        kelimeler = [k for v in seri if not C.yer_tutucu_mu(v) for k in v.split(" ")]
        sozluk = self._sozluk(kelimeler, baslik)
        sonuc = []
        for i, v in enumerate(seri):
            if C.yer_tutucu_mu(v):
                sonuc.append(None)
                continue
            parcalar, cozulemedi = [], False
            for k in v.split(" "):
                if "?" in k:
                    desen = re.compile(re.escape(anahtar_joker(k)).replace(r"\?", ".") + "$")
                    bulunan = [f for a, f in sozluk.items() if len(a) == len(anahtar_joker(k)) and desen.match(a)]
                    if len(bulunan) == 1:
                        parcalar.append(bulunan[0])
                    else:
                        parcalar.append(k)
                        cozulemedi = True
                else:
                    parcalar.append(sozluk.get(anahtar(k), tr_title(k) if baslik else k))
            yeni = " ".join(parcalar)
            if cozulemedi and df is not None:
                self._belirsiz(df, i, tablo, sutun, v, "isim", baglam_sutunlari=["ad", "soyad", "eposta"])
                sonuc.append(None)
                continue
            if cozulemedi:
                yeni = None
            sonuc.append(yeni)
        return sonuc

    # --- Çıktı -------------------------------------------------------------------------------------------------

    def yaz(self, tablolar: dict[str, pd.DataFrame], cikti: Path, ek: dict | None = None):
        yaz(tablolar, Path(cikti), self.eslesme, self.sorunlar, self.karantina,
            {**dict(self.istatistik), **(ek or {})})


def tekrar_karari(a: dict, b: dict) -> tuple[str, list[str]]:
    """İki müşteri kaydı aynı kişi mi? Ad-soyad bloğu içinde çağrılır."""
    guclu, orta = [], []
    for s in ("dogum_tarihi", "telefon", "eposta"):
        if not _bos(a[s]) and a[s] == b[s]:
            guclu.append(s)
    if not _bos(a["ilce"]) and a["ilce"] == b["ilce"]:
        orta.append("ilce")
    if not _bos(a["eposta"]) and not _bos(b["eposta"]) and "eposta" not in guclu:
        ya, yb = a["eposta"].split("@")[0], b["eposta"].split("@")[0]
        if ya != yb and (ya.startswith(yb) or yb.startswith(ya)) and abs(len(ya) - len(yb)) <= 1:
            orta.append("eposta_yerel")
    kanit = guclu + orta
    if len(guclu) >= 2 or (guclu and orta):
        return "evet", kanit
    if len(guclu) == 1 or len(orta) >= 2:
        return "belirsiz", kanit
    return "hayir", kanit


def yaz(tablolar: dict[str, pd.DataFrame], cikti: Path, eslesme: dict[str, str], sorunlar: list[dict],
        karantina: list[dict], istatistik: dict):
    """Tüm yöntemlerin ortak çıktı biçimi."""
    temiz = cikti / "temiz"
    temiz.mkdir(parents=True, exist_ok=True)
    for tablo, df in tablolar.items():
        df = df.copy()
        for sutun, tip in R.SEMA[tablo].items():
            if tip in ("para", "oran"):
                df[sutun] = [None if _bos(v) else f"{float(v):.2f}" for v in df[sutun]]
            elif tip == "adet":
                df[sutun] = [None if _bos(v) else str(int(v)) for v in df[sutun]]
        df.to_csv(temiz / f"{tablo}.csv", index=False, lineterminator="\n")
    pd.DataFrame(sorted(eslesme.items()), columns=["eski_id", "yeni_id"]).to_csv(
        temiz / "musteri_eslesme.csv", index=False)
    pd.DataFrame(sorunlar, columns=["tablo", "anahtar", "sutun", "ham", "temiz", "islem"]).to_csv(
        cikti / "sorunlar.csv", index=False)
    pd.DataFrame(karantina, columns=["tablo", "ham_satir", "sebep"]).to_csv(cikti / "karantina.csv", index=False)
    with pd.ExcelWriter(temiz / "veri.xlsx") as w:
        for tablo, df in tablolar.items():
            df.to_excel(w, sheet_name=tablo, index=False)
    (cikti / "istatistik.json").write_text(json.dumps(istatistik, ensure_ascii=False, indent=2, default=str),
                                          encoding="utf-8")


def kural_ile_temizle(kirli: Path, cikti: Path, cozucu: Cozucu | None = None) -> KuralTemizleyici:
    t = KuralTemizleyici(cozucu)
    tablolar = t.temizle(kirli)
    t.yaz(tablolar, cikti)
    return t
