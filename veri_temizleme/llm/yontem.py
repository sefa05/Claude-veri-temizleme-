"""Sadece LLM yöntemi: ham CSV satırları küçük gruplar halinde Claude'a gider, model temiz kaydı döner.

Kod yalnızca yapısal işleri yapar: dosyayı gruplara bölmek, aynı sipariş numarasının tekrarını silmek ve müşteri
tekrarı adaylarını ad-soyad ile gruplamak (blocking). Hücrelerin anlamlandırılması ve iki kaydın aynı kişi olup
olmadığı kararı tamamen modele aittir. Bozma kataloğu modele gösterilmez.
"""

from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from .. import referans as R
from ..metin import anahtar
from ..temizleme.kural import yaz
from .istemci import LLMIstemci

BICIMLER = {
    "id": "Önek + sıfır dolgulu sayı: musteri_id 'M' + 5 hane (M00042), urun_id 'U' + 4 hane (U0007), "
          "siparis_id 'S' + 6 hane (S000123)",
    "isim": "Türkçe yazımıyla, baş harfi büyük (Ayşe, Işık, Şahin)",
    "eposta": "küçük harf, geçerli adres (ad.soyad@gmail.com)",
    "telefon": "+90 5XX XXX XX XX",
    "tarih": "YYYY-AA-GG",
    "para": "nokta ondalık ayraçlı sayı, para birimi yok (1250.50)",
    "oran": "0 ile 1 arası ondalık (yüzde 10 -> 0.10)",
    "adet": "pozitif tam sayı",
    "il": "Türkiye'nin 81 ilinden birinin resmi adı",
    "ilce": "ilçenin resmi Türkçe adı",
    "metin": "fazla boşluk ve bozuk karakterler temizlenmiş metin",
}
IS_KURALLARI = """İş kuralları:
- Veri 2025-01-01'de çekildi. Bu tarihten sonraki sipariş ve kayıt tarihleri geçersizdir.
- Doğum tarihi 1920-01-01 ile 2010-12-31 arasında olmalıdır.
- teslim_tarihi, siparis_tarihi ile aynı gün ya da sonrasındadır ve en fazla 30 gün sonradır. Kargoda, Hazırlanıyor
  ve İptal Edildi durumundaki siparişlerin teslim tarihi yoktur.
- toplam_tutar = adet × birim_fiyat × (1 − indirim_orani), 2 ondalığa yuvarlanır.
- Kaynak sistemler tarihleri çoğunlukla gün/ay sırasıyla yazar. Bazı kayıtlar ay/gün sırasıyla gelmiş olabilir."""


def _sema_metni(tablo: str) -> str:
    satirlar = []
    for sutun, tip in R.SEMA[tablo].items():
        bicim = BICIMLER.get(tip if tip not in ("ref",) else "id")
        if tip == "secenek":
            bicim = "yalnızca şunlardan biri: " + " | ".join(R.SECENEKLER[sutun])
        satirlar.append(f"- {sutun}: {bicim}")
    return "\n".join(satirlar)


def sistem_metni(tablo: str, ek: str = "") -> str:
    return f"""Sen bir veri temizleme sistemisin. Bir e-ticaret şirketinin dağınık CSV dışa aktarımından gelen ham
satırları temizliyorsun. Tablo: {tablo}.

Hedef sütunlar ve biçimleri:
{_sema_metni(tablo)}

{IS_KURALLARI}

Talimatlar:
1. Her ham satırı bir kayıt olarak döndür. Satır bozuk olabilir: yanlış ayraç, fazladan boş alan ya da iki kaydın tek
   satıra yapışması. İki kayıt yapışmışsa iki ayrı kayıt döndür.
2. Her değeri hedef biçime çevir. Seçenekli sütunlarda yalnızca listedeki değerlerden birini yaz.
3. Bir değeri güvenle çıkaramıyorsan null yaz. Tahmin etme, değer uydurma. Aynı satırdaki diğer alanlardan kesin
   olarak hesaplanabilen değerleri (ör. toplam_tutar) hesapla.
4. Anahtar sütununu ({R.ANAHTARLAR[tablo]}) her zaman doldur.

İl listesi: {", ".join(R.ILLER.values())}
{ek}"""


def cikti_semasi(tablo: str) -> dict:
    alanlar = {s: {"type": ["string", "null"]} for s in R.SEMA[tablo]}
    return {
        "type": "object",
        "properties": {"kayitlar": {"type": "array", "items": {
            "type": "object", "properties": alanlar, "required": list(alanlar), "additionalProperties": False}}},
        "required": ["kayitlar"], "additionalProperties": False,
    }


def _sayi(v):
    try:
        return None if v is None or str(v).strip() == "" else float(v)
    except ValueError:
        return None


def _tiplere_cevir(tablo: str, kayitlar: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(kayitlar, columns=list(R.SEMA[tablo])).astype(object)
    for sutun, tip in R.SEMA[tablo].items():
        if tip in ("para", "oran", "adet"):
            df[sutun] = pd.Series([_sayi(v) for v in df[sutun]], index=df.index, dtype=object)
        if tip == "adet":
            df[sutun] = pd.Series([None if v is None or not float(v).is_integer() else int(v) for v in df[sutun]],
                                  index=df.index, dtype=object)
    return df


def orneklem_sec(kirli_siparisler: Path, n: int, seed: int) -> set[str]:
    metin = Path(kirli_siparisler).read_text(encoding="utf-8")
    kimlikler = sorted(set(re.findall(r"S\d{6}", metin)))
    if n >= len(kimlikler):
        return set(kimlikler)
    return set(random.Random(seed).sample(kimlikler, n))


class LLMTemizleyici:
    def __init__(self, istemci: LLMIstemci, paralel: int = 4, grup_boyutu: dict[str, int] | None = None):
        self.istemci = istemci
        self.paralel = paralel
        self.grup = {"musteriler": 25, "urunler": 25, "siparisler": 20, **(grup_boyutu or {})}
        self.istatistik: dict[str, int] = defaultdict(int)

    def _tablo_temizle(self, tablo: str, satirlar: list[str], baslik: str, ek: str = "") -> pd.DataFrame:
        sistem = sistem_metni(tablo, ek)
        sema = cikti_semasi(tablo)
        gruplar = [satirlar[i:i + self.grup[tablo]] for i in range(0, len(satirlar), self.grup[tablo])]

        def calistir(grup: list[str]):
            mesaj = "Başlık satırı:\n" + baslik + "\n\nHam satırlar:\n" + "\n".join(grup)
            cevap = self.istemci.json_iste(sistem, mesaj, sema)
            if cevap is None:
                self.istatistik[f"{tablo}.basarisiz_grup"] += 1
                return []
            return cevap["kayitlar"]

        with ThreadPoolExecutor(self.paralel) as havuz:
            kayitlar = [k for sonuc in havuz.map(calistir, gruplar) for k in sonuc]
        self.istatistik[f"{tablo}.grup"] += len(gruplar)
        return _tiplere_cevir(tablo, kayitlar)

    def temizle(self, kirli: Path, orneklem: set[str] | None = None) -> dict[str, pd.DataFrame]:
        kirli = Path(kirli)
        ham = {t: (kirli / f"{t}.csv").read_text(encoding="utf-8").rstrip("\n").split("\n") for t in R.SEMA}
        urunler = self._tablo_temizle("urunler", ham["urunler"][1:], ham["urunler"][0])
        musteriler = self._tablo_temizle("musteriler", ham["musteriler"][1:], ham["musteriler"][0])
        siparis_satirlari = ham["siparisler"][1:]
        if orneklem is not None:
            siparis_satirlari = [s for s in siparis_satirlari if set(re.findall(r"S\d{6}", s)) & orneklem]
        fiyatlar = "\n".join(f"{u}: {'' if f is None else f'{f:.2f}'}"
                             for u, f in zip(urunler["urun_id"], urunler["birim_fiyat"]) if u)
        siparisler = self._tablo_temizle("siparisler", siparis_satirlari, ham["siparisler"][0],
                                         ek=f"\nÜrün fiyat listesi (urun_id: birim_fiyat):\n{fiyatlar}")
        urunler = urunler.drop_duplicates("urun_id")
        musteriler, self.eslesme = self._tekrar_birlestir(musteriler.drop_duplicates("musteri_id"))
        siparisler["musteri_id"] = pd.Series([self.eslesme.get(m, m) for m in siparisler["musteri_id"]],
                                             index=siparisler.index, dtype=object)
        siparisler = siparisler.drop_duplicates("siparis_id").sort_values("siparis_id").reset_index(drop=True)
        return {"musteriler": musteriler, "urunler": urunler, "siparisler": siparisler}

    def _tekrar_birlestir(self, df: pd.DataFrame):
        """Ad-soyad bloklarındaki kayıtları modele sorar: hangileri aynı kişi?"""
        kayitlar = {r["musteri_id"]: r for r in df.to_dict("records") if r["musteri_id"]}
        bloklar: dict[frozenset, list[str]] = defaultdict(list)
        for mid, r in kayitlar.items():
            if r["ad"] and r["soyad"]:
                bloklar[frozenset((anahtar(r["ad"]), anahtar(r["soyad"])))].append(mid)
        adaylar = [sorted(b) for b in bloklar.values() if len(b) >= 2]
        sistem = """Sen bir müşteri kaydı eşleştirme sistemisin. Her grupta adı ve soyadı aynı olan müşteri kayıtları
var. Aynı ada sahip farklı kişiler olabilir. Hangi kayıtların aynı kişiye ait olduğuna karar ver. Kanıt: doğum tarihi,
telefon, e-posta, ilçe. Emin değilsen kayıtları ayrı bırak. Her grup için aynı kişiye ait kayıt kümelerini döndür
(tek kayıtlık kümeleri yazma)."""
        sema = {"type": "object", "properties": {"gruplar": {"type": "array", "items": {
            "type": "object", "properties": {
                "grup": {"type": "integer"},
                "kumeler": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}}},
            "required": ["grup", "kumeler"], "additionalProperties": False}}},
            "required": ["gruplar"], "additionalProperties": False}
        gorunen = ["musteri_id", "ad", "soyad", "eposta", "telefon", "dogum_tarihi", "il", "ilce", "kayit_tarihi"]
        paketler = [list(enumerate(adaylar))[i:i + 10] for i in range(0, len(adaylar), 10)]

        def calistir(paket):
            mesaj = json.dumps([{"grup": g, "kayitlar": [{s: kayitlar[m].get(s) for s in gorunen} for m in blok]}
                                for g, blok in paket], ensure_ascii=False, default=str)
            cevap = self.istemci.json_iste(sistem, mesaj, sema)
            return [] if cevap is None else cevap["gruplar"]

        with ThreadPoolExecutor(self.paralel) as havuz:
            sonuclar = [g for s in havuz.map(calistir, paketler) for g in s]
        self.istatistik["tekrar_grubu"] = len(adaylar)
        eslesme: dict[str, str] = {}
        for g in sonuclar:
            if not 0 <= g["grup"] < len(adaylar):
                continue
            izinli = set(adaylar[g["grup"]])
            for kume in g["kumeler"]:
                kume = sorted(set(kume) & izinli - set(eslesme))
                for m in kume[1:]:
                    eslesme[m] = kume[0]
        for eski, yeni in eslesme.items():
            for s, v in kayitlar[eski].items():
                if (kayitlar[yeni].get(s) is None or kayitlar[yeni].get(s) == "") and v not in (None, "") \
                        and s != "kayit_tarihi":
                    kayitlar[yeni][s] = v
        cikti = pd.DataFrame([r for m, r in kayitlar.items() if m not in eslesme], columns=df.columns)
        return cikti.astype(object).sort_values("musteri_id").reset_index(drop=True), eslesme

    def yaz(self, tablolar, cikti: Path, ek: dict | None = None):
        yaz(tablolar, Path(cikti), self.eslesme, [], [],
            {**dict(self.istatistik), "llm": self.istemci.kullanim.sozluk(), **(ek or {})})


def maliyet_tahmini(kirli: Path, orneklem: set[str], model: str, grup: dict[str, int] | None = None) -> dict:
    """Sadece LLM yöntemi için kaba maliyet tahmini. Düşünme tokenları dahil değildir, gerçek maliyet daha
    yüksek çıkabilir."""
    from .istemci import maliyet_hesapla

    grup = {"musteriler": 25, "urunler": 25, "siparisler": 20, **(grup or {})}
    toplam_girdi = toplam_cikti = cagri = 0
    for tablo in R.SEMA:
        satirlar = (Path(kirli) / f"{tablo}.csv").read_text(encoding="utf-8").rstrip("\n").split("\n")[1:]
        if tablo == "siparisler":
            satirlar = [s for s in satirlar if set(re.findall(r"S\d{6}", s)) & orneklem]
        n = -(-len(satirlar) // grup[tablo])
        sistem = len(sistem_metni(tablo)) // 3 + (3000 if tablo == "siparisler" else 0)
        veri = sum(len(s) for s in satirlar) // 3
        toplam_girdi += n * sistem + veri
        toplam_cikti += int(veri * 1.8)  # JSON anahtarları çıktıyı büyütür.
        cagri += n
    return {"cagri": cagri, "girdi_token": toplam_girdi, "cikti_token": toplam_cikti,
            "maliyet": round(maliyet_hesapla(model, toplam_girdi, toplam_cikti), 2)}
