import pandas as pd

from veri_temizleme import referans as R
from veri_temizleme.uretici.bozma import boz
from veri_temizleme.uretici.temiz import temiz_veri_uret


def test_ayni_seed_ayni_veri():
    a = boz(temiz_veri_uret(3, 300, 100, 30), 3)
    b = boz(temiz_veri_uret(3, 300, 100, 30), 3)
    assert a.csv_metinleri == b.csv_metinleri


def test_temiz_veri_is_kurallarini_saglar():
    d = temiz_veri_uret(5, 2000, 300, 50)
    s = d["siparisler"]
    beklenen = (s.adet * s.birim_fiyat * (1 - s.indirim_orani)).round(2)
    assert (abs(s.toplam_tutar - beklenen) < 0.011).all()  # numpy ve Python yuvarlaması farklı
    assert (s.teslim_tarihi <= "2024-12-31").all()
    teslimli = s[s.teslim_tarihi != ""]
    gun = (pd.to_datetime(teslimli.teslim_tarihi) - pd.to_datetime(teslimli.siparis_tarihi)).dt.days
    assert gun.between(1, 7).all()
    assert (s[s.durum.isin(R.TESLIMSIZ_DURUMLAR)].teslim_tarihi == "").all()
    m = d["musteriler"]
    assert m.eposta.is_unique and m.musteri_id.is_unique
    assert all(R.ILCE_IL[i] == il for i, il in zip(m.ilce, m.il))


def test_bozma_kaydi_kirli_veriyle_tutarli():
    temiz = temiz_veri_uret(9, 1000, 200, 40)
    sonuc = boz(temiz, 9)
    kayit = sonuc.kayit[(sonuc.kayit.sutun != "*satir*") & (sonuc.kayit.bozma != "B1")]
    siparis = sonuc.tablolar["siparisler"].drop_duplicates("siparis_id").set_index("siparis_id")
    for r in kayit[kayit.tablo == "siparisler"].itertuples():
        assert siparis.at[r.anahtar, r.sutun] == r.bozuk
    assert set(sonuc.kayit.bozma) >= {"B1", "B2", "B3", "B5", "B6", "B8", "B14"}
    assert (~sonuc.kayit.kurtarilabilir).any()


def test_surpriz_bozmalar_standart_veriyi_etkilemez():
    temiz = temiz_veri_uret(11, 500, 120, 30)
    standart = boz(temiz, 11)
    assert boz(temiz, 11).csv_metinleri == standart.csv_metinleri
    surpriz = boz(temiz, 11, surpriz=True)
    assert surpriz.csv_metinleri != standart.csv_metinleri
    assert surpriz.csv_metinleri == boz(temiz, 11, surpriz=True).csv_metinleri
    assert set(surpriz.kayit.bozma) >= {"B3", "B6", "B8", "B14"}
