"""Sentetik veri üretimi: temiz veri (gerçek doğru) + kirli veri + bozma kaydı."""

from __future__ import annotations

from pathlib import Path

from .bozma import boz, csv_yaz, metne_cevir
from .temiz import temiz_veri_uret


def uret(klasor: Path, seed: int = 42, siparis: int = 10_000, musteri: int = 2_500, urun: int = 300,
         oran_carpani: float = 1.0, surpriz: bool = False) -> dict[str, int]:
    """`klasor/kirli` altına temizleyicilerin göreceği veriyi, `klasor/gercek` altına ölçüm verisini yazar."""
    klasor = Path(klasor)
    (klasor / "kirli").mkdir(parents=True, exist_ok=True)
    (klasor / "gercek").mkdir(parents=True, exist_ok=True)
    temiz = temiz_veri_uret(seed, siparis, musteri, urun)
    sonuc = boz(temiz, seed, oran_carpani, surpriz=surpriz)
    for tablo, df in temiz.items():
        (klasor / "gercek" / f"{tablo}.csv").write_text(csv_yaz(metne_cevir(tablo, df)), encoding="utf-8")
    for tablo, metin in sonuc.csv_metinleri.items():
        (klasor / "kirli" / f"{tablo}.csv").write_text(metin, encoding="utf-8")
    sonuc.kayit.to_csv(klasor / "gercek" / "bozma_kaydi.csv", index=False)
    sonuc.tekrar_eslesme.to_csv(klasor / "gercek" / "tekrar_eslesme.csv", index=False)
    return {"bozuk_hucre": int((sonuc.kayit.sutun != "*satir*").sum()), "kayit": len(sonuc.kayit)}
