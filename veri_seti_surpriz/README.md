# Sürpriz Hatalar Veri Seti (2. bölüm)

`veri_seti/` ile aynı temiz veri (seed 42), ama hatalar kural yönteminin hiç görmediği biçimlerle geliyor:
`27 Şubat 1987 Cuma`, Unix zamanı, Excel tarih numarası, `ayse[at]gmail.com`, `MUS-00211`, `81 TL 62 kr`, HTML
karakter kodları, sekme ve `|` ile ayrılmış satırlar, görünmez `\r` karakteri. Tüm değerler kirli metinden kesin
olarak kurtarılabilir.

```bash
veri-temizle puanla benim_ciktim/ --gercek veri_seti_surpriz/gercek
```

Referans: aynı kural kodu burada %68,9'da kaldı (bilinen hatalarda %97,6). Yöntemin iki sette de iyiyse gerçekten
genelleşiyor demektir. Aynı veriyi `veri-temizle uret --seed 42 --surpriz` ile yeniden üretebilirsin.
