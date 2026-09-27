"""LLM akışının testleri. Gerçek API çağrılmaz: sahte istemci şemaya uygun cevap üretir."""

import csv
import json
from types import SimpleNamespace

from veri_temizleme.deney import yontem_calistir
from veri_temizleme.llm.istemci import LLMIstemci, maliyet_hesapla
from veri_temizleme.llm.yontem import orneklem_sec


class SahteIstemci:
    """Ham alanları olduğu gibi döndüren saf bir 'model'. Akışı ve ölçümü test etmek için yeterli."""

    def __init__(self):
        self.cagrilar = []
        self.messages = SimpleNamespace(create=self._create)
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.cagrilar.append(kw)
        ozellikler = kw["output_config"]["format"]["schema"]["properties"]
        mesaj = kw["messages"][0]["content"]
        if "kayitlar" in ozellikler:
            baslik = next(csv.reader([mesaj.split("Başlık satırı:\n")[1].split("\n")[0]]))
            satirlar = mesaj.split("Ham satırlar:\n")[1].split("\n")
            kayitlar = [dict(zip(baslik, a)) for a in csv.reader(satirlar) if len(a) == len(baslik)]
            cevap = {"kayitlar": kayitlar}
        elif "gruplar" in ozellikler:
            cevap = {"gruplar": [{"grup": g["grup"], "kumeler": [[k["musteri_id"] for k in g["kayitlar"]]]}
                                 for g in json.loads(mesaj)]}
        elif "cevaplar" in ozellikler:
            cevap = {"cevaplar": [{"id": h["id"], "deger": (h["adaylar"] or [None])[0]} for h in json.loads(mesaj)]}
        else:
            cevap = {"kararlar": [{"id": c["id"], "ayni_kisi": False} for c in json.loads(mesaj)]}
        return SimpleNamespace(
            model=kw["model"], stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=1000, output_tokens=500, cache_read_input_tokens=0,
                                  cache_creation_input_tokens=0),
            content=[SimpleNamespace(type="text", text=json.dumps(cevap, ensure_ascii=False))])


def test_maliyet():
    assert maliyet_hesapla("claude-opus-5", 1_000_000, 1_000_000) == 30.0
    assert maliyet_hesapla("claude-haiku-4-5", 0, 0, okuma=1_000_000) == 0.1


def test_onbellek_ikinci_cagriyi_engeller(tmp_path):
    sahte = SahteIstemci()
    istemci = LLMIstemci(onbellek=tmp_path, client=sahte)
    sema = {"type": "object", "properties": {"kararlar": {}}}
    mesaj = json.dumps([{"id": "a"}])
    assert istemci.json_iste("s", mesaj, sema) == istemci.json_iste("s", mesaj, sema)
    assert len(sahte.cagrilar) == 1
    assert istemci.kullanim.cagri == 2 and istemci.kullanim.onbellekten == 1
    # Önbellekten okunan çağrı ilk maliyetiyle sayılır.
    assert abs(istemci.kullanim.maliyet - 2 * maliyet_hesapla("claude-opus-5", 1000, 500)) < 1e-9


def test_geri_donus_beta_istegiyle_gonderilir(tmp_path):
    sahte = SahteIstemci()
    LLMIstemci(client=sahte).json_iste("s", "[]", {"type": "object", "properties": {"kararlar": {}}})
    assert sahte.cagrilar[0]["fallbacks"] == "default"
    assert sahte.cagrilar[0]["betas"] == ["server-side-fallback-2026-07-01"]
    assert sahte.cagrilar[0]["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_llm_yontemi_uctan_uca(kucuk_veri, tmp_path):
    kirli, gercek = kucuk_veri / "veri" / "kirli", kucuk_veri / "veri" / "gercek"
    kapsam = {"siparisler": orneklem_sec(kirli / "siparisler.csv", 100, 1)}
    istemci = LLMIstemci(client=SahteIstemci(), onbellek=tmp_path / "onbellek")
    sonuc = yontem_calistir("llm", kirli, gercek, tmp_path / "llm", kapsam, istemci, paralel=2)
    o = sonuc["orneklem"]
    assert o["satirlar"]["siparisler"]["gercek_satir"] == 100
    # Ham değeri aynen döndüren sahte model bozuk hücrelerin çoğunu düzeltemez ama temiz hücreler doğru kalır.
    assert o["genel_dogruluk"] < 0.5
    assert o["temiz_hucreler"]["dogru"] > 0.95
    assert sonuc["llm"]["cagri"] > 0 and sonuc["llm"]["maliyet"] > 0


def test_hibrit_yontemi_belirsizleri_llme_sorar(kucuk_veri, tmp_path):
    kirli, gercek = kucuk_veri / "veri" / "kirli", kucuk_veri / "veri" / "gercek"
    kapsam = {"siparisler": orneklem_sec(kirli / "siparisler.csv", 100, 1)}
    sahte = SahteIstemci()
    sonuc = yontem_calistir("hibrit", kirli, gercek, tmp_path / "hibrit", kapsam, LLMIstemci(client=sahte))
    assert sonuc["istatistik"]["belirsiz_hucre"] > 0
    assert any("llm_cozdu" in k for k in sonuc["istatistik"])
    assert sonuc["tam"]["genel_dogruluk"] > 0.9
