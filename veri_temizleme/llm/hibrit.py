"""Hibrit yöntem: kural hattı önce çalışır, yalnızca çözemediği hücreler ve belirsiz müşteri çiftleri LLM'e gider.

İl ve seçenek sütunlarında model serbest yazmaz. Kuralın referans listeden bulanık aramayla çektiği adaylar arasından
seçim yapar (RAG). Modelin cevabı kural tarafında yeniden doğrulanır: aday dışı bir değer boş sayılır.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path

from ..temizleme.kural import Belirsiz, BelirsizCift, KuralTemizleyici
from .istemci import LLMIstemci
from .yontem import IS_KURALLARI

HUCRE_SISTEMI = f"""Sen bir veri temizleme uzmanısın. Kural tabanlı bir temizleyici bir e-ticaret veri setinde bazı
hücreleri güvenle çözemedi. Her hücre için doğru değeri belirle.

Alanlar:
- sutun: hücrenin sütunu, ham: kirli değer, tur: beklenen değer tipi
- adaylar: doluysa cevap YALNIZCA bu listeden biri olabilir (referans listeden çekilmiş en yakın değerler)
- baglam: aynı satırdaki diğer ham alanlar

Cevap biçimleri: tarih YYYY-AA-GG, isim Türkçe yazımıyla baş harfi büyük, eposta küçük harf, cinsiyet Kadın | Erkek.

{IS_KURALLARI}

Emin değilsen deger alanına null yaz. Tahmin etme, değer uydurma."""

CIFT_SISTEMI = """Sen bir müşteri kaydı eşleştirme uzmanısın. Her çiftte adı ve soyadı aynı olan iki müşteri kaydı var.
Kural tabanlı eşleştirici bu çiftlere karar veremedi. İki kayıt aynı kişiye mi ait? Aynı ada sahip farklı kişiler
olabilir. Emin değilsen false döndür."""

HUCRE_SEMASI = {"type": "object", "properties": {"cevaplar": {"type": "array", "items": {
    "type": "object", "properties": {"id": {"type": "string"}, "deger": {"type": ["string", "null"]}},
    "required": ["id", "deger"], "additionalProperties": False}}}, "required": ["cevaplar"],
    "additionalProperties": False}
CIFT_SEMASI = {"type": "object", "properties": {"kararlar": {"type": "array", "items": {
    "type": "object", "properties": {"id": {"type": "string"}, "ayni_kisi": {"type": "boolean"}},
    "required": ["id", "ayni_kisi"], "additionalProperties": False}}}, "required": ["kararlar"],
    "additionalProperties": False}


class LLMCozucu:
    def __init__(self, istemci: LLMIstemci, paralel: int = 4, grup_boyutu: int = 25):
        self.istemci = istemci
        self.paralel = paralel
        self.grup_boyutu = grup_boyutu

    def _paketle(self, ogeler: list) -> list[list]:
        return [ogeler[i:i + self.grup_boyutu] for i in range(0, len(ogeler), self.grup_boyutu)]

    def hucreleri_coz(self, hucreler: list[Belirsiz]) -> dict[str, str | None]:
        def calistir(paket: list[Belirsiz]):
            ogeler = [{k: v for k, v in asdict(h).items() if k not in ("tablo", "anahtar", "varsayilan")}
                      for h in paket]
            cevap = self.istemci.json_iste(HUCRE_SISTEMI, json.dumps(ogeler, ensure_ascii=False), HUCRE_SEMASI)
            return [] if cevap is None else cevap["cevaplar"]

        with ThreadPoolExecutor(self.paralel) as havuz:
            cevaplar = [c for s in havuz.map(calistir, self._paketle(hucreler)) for c in s]
        gecerli = {h.id for h in hucreler}
        return {c["id"]: c["deger"] for c in cevaplar if c["id"] in gecerli}

    def ciftleri_coz(self, ciftler: list[BelirsizCift]) -> dict[str, bool]:
        def calistir(paket: list[BelirsizCift]):
            ogeler = [{"id": c.id, "kayit_a": c.a, "kayit_b": c.b} for c in paket]
            cevap = self.istemci.json_iste(CIFT_SISTEMI, json.dumps(ogeler, ensure_ascii=False), CIFT_SEMASI)
            return [] if cevap is None else cevap["kararlar"]

        with ThreadPoolExecutor(self.paralel) as havuz:
            kararlar = [k for s in havuz.map(calistir, self._paketle(ciftler)) for k in s]
        return {k["id"]: bool(k["ayni_kisi"]) for k in kararlar}


def hibrit_ile_temizle(kirli: Path, cikti: Path, istemci: LLMIstemci) -> KuralTemizleyici:
    t = KuralTemizleyici(LLMCozucu(istemci))
    tablolar = t.temizle(kirli)
    t.yaz(tablolar, cikti, {"llm": istemci.kullanim.sozluk()})
    return t
