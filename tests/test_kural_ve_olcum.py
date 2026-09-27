import shutil

from veri_temizleme.olcum import olc
from veri_temizleme.temizleme.kural import kural_ile_temizle


def test_gercek_verinin_kendisi_tam_puan_alir(kucuk_veri, tmp_path):
    gercek = kucuk_veri / "veri" / "gercek"
    temiz = tmp_path / "temiz"
    shutil.copytree(gercek, temiz)
    eslesme = (gercek / "tekrar_eslesme.csv").read_text().replace("tekrar_id,asil_id", "eski_id,yeni_id")
    (temiz / "musteri_eslesme.csv").write_text(eslesme)
    o = olc(temiz, gercek).ozet
    assert o["genel_dogruluk"] == 1.0
    assert o["uydurma"]["n"] == 0
    assert o["tekrar"]["f1"] == 1.0


def test_kural_yontemi_uctan_uca(kucuk_veri, tmp_path):
    kural_ile_temizle(kucuk_veri / "veri" / "kirli", tmp_path)
    for dosya in ("temiz/musteriler.csv", "temiz/siparisler.csv", "temiz/veri.xlsx", "sorunlar.csv",
                  "karantina.csv", "istatistik.json"):
        assert (tmp_path / dosya).exists()
    o = olc(tmp_path / "temiz", kucuk_veri / "veri" / "gercek").ozet
    assert o["genel_dogruluk"] > 0.95
    assert o["uydurma"]["oran"] < 0.01
    assert o["temiz_hucreler"]["dogru"] > 0.999
    assert o["tekrar"]["f1"] > 0.95
    assert o["satirlar"]["siparisler"]["bulunan_satir"] == o["satirlar"]["siparisler"]["gercek_satir"]
    assert o["satir_bozmalari"]["B2"]["basari"] == 1.0
