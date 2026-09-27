from datetime import date

import pytest

from veri_temizleme.metin import mojibake_onar, tr_title
from veri_temizleme.temizleme import cozumleyiciler as C
from veri_temizleme.temizleme.sozluk import IlEslestirici, secenek_eslestirici


@pytest.mark.parametrize("kelime", ["İstanbul", "Şişli", "Ağrı", "Çiğli", "Gümüşhane", "Üsküdar", "Iğdır"])
def test_mojibake_iki_yonde_onarilir(kelime):
    assert mojibake_onar(kelime.encode("utf-8").decode("cp1252")) == kelime
    assert mojibake_onar(kelime.encode("cp1254").decode("latin-1")) == kelime


def test_turkce_baslik():
    assert tr_title("ışık izmir") == "Işık İzmir"
    assert tr_title("AYŞE YILMAZ") == "Ayşe Yılmaz"


@pytest.mark.parametrize("metin,beklenen", [
    ("5 Mart 2024", [date(2024, 3, 5)]), ("6 ocak 23", [date(2023, 1, 6)]), ("20240305", [date(2024, 3, 5)]),
    ("05.03.24", [date(2024, 3, 5)]), ("05-Mar-2024", [date(2024, 3, 5)]), ("03/15/2024", [date(2024, 3, 15)]),
    ("05/03/2024", [date(2024, 3, 5), date(2024, 5, 3)]), ("0000-00-00", []), ("yok", []),
])
def test_tarih_adaylari(metin, beklenen):
    assert C.tarih_adaylari(metin) == beklenen


@pytest.mark.parametrize("metin", ["1.250,50 TL", "₺1,250.50", "1250,50 tl", "1250.5", "TRY 1250.50", "1250,50₺"])
def test_para(metin):
    assert C.para(metin) == 1250.5


@pytest.mark.parametrize("metin", ["%10", "10", "0,10", "10%", "%10.0", "0.10"])
def test_oran(metin):
    assert C.oran(metin) == 0.1


@pytest.mark.parametrize("metin,beklenen", [("3 adet", 3), ("üç", 3), ("3,0", 3), ("x3", 3), ("-3", -3)])
def test_adet(metin, beklenen):
    assert C.adet(metin) == beklenen


def test_telefon_ve_id():
    assert C.telefon("0 (532) 123 45 67") == "+90 532 123 45 67"
    assert C.telefon("12345") is None
    assert C.id_normalize("#367", "M", 5) == "M00367"
    assert C.id_normalize("m-00367", "M", 5) == "M00367"


def test_eslestiriciler():
    il = IlEslestirici()
    assert il.eslestir("34").deger == "İstanbul"
    assert il.eslestir("İstanbul (Avrupa)").deger == "İstanbul"
    assert il.eslestir("Mu?la").deger == "Muğla"
    assert il.eslestir("BUR.").deger is None  # Bursa mı Burdur mu? Belirsiz kalmalı.
    kargo = secenek_eslestirici("kargo_firmasi")
    assert kargo.eslestir("Yurtiçi").deger == "Yurtiçi Kargo"
    sonuc = kargo.eslestir("TEX")
    assert sonuc.deger is None and "Trendyol Express" in sonuc.adaylar
