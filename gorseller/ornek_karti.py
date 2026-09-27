"""Örnek kartı: gerçek veriden elle seçilmiş kirli → temiz örnekleri (seed 42, kural yöntemi).

Çalıştırma: python gorseller/ornek_karti.py
"""
from veri_temizleme.gorsel import ekran_goruntusu, FONT
import html
duzeldi=[("dogum_tarihi","24-Oct-1959","1959-10-24"),("soyad","YÄ±ldÄ±z","Yıldız"),("ad","Ay?e","Ayşe"),
("birim_fiyat","₺4,851.99","4851.99"),("eposta","orhan.isikgmail.com","orhan.isik@gmail.com"),("il","SAM.","Samsun"),
("adet","dört","4"),("adet","-3","3  (toplamdan doğrulandı)"),("toplam_tutar","1135.10","113.51  (yeniden hesaplandı)")]
bos=[("siparis_tarihi","2036-01-11","boş bıraktı  (gelecek tarih, gerçeği bilinemez)")]
olmadi=[("kargo_firmasi","TEX","boş","Trendyol Express"),("odeme_yontemi","Papara","boş","Dijital Cüzdan"),
("durum","Tamamlandı","boş","Teslim Edildi"),("dogum_tarihi","06/01/1967","1967-01-06","1967-06-01")]
e=html.escape
def satir(s,k,t,sinif,g=""):
    return (f"<div class='r'><div class='s'>{e(s)}</div><div class='v kirli'>{e(k)}</div><div class='ok'>→</div>"
            f"<div class='v {sinif}'>{e(t)}{f'<span class=g>gerçek: {e(g)}</span>' if g else ''}</div></div>")
css="""*{box-sizing:border-box;margin:0}body{width:1200px;background:#faf8f3;color:#1c1b19;
font-family:"Inter","Liberation Sans","DejaVu Sans",sans-serif;padding:60px 64px 44px}
h1{font-size:42px;line-height:1.15;font-weight:700}.alt{font-size:21px;color:#6d6a63;margin:12px 0 30px}
h2{font-size:20px;text-transform:uppercase;letter-spacing:.05em;margin:28px 0 8px;display:flex;align-items:center;gap:10px}
h2 .n{display:inline-grid;place-items:center;width:30px;height:30px;border-radius:50%;color:#fff;font-size:17px}
.y h2 .n{background:#2f8a5b}.b h2 .n{background:#6d6a63}.x h2 .n{background:#c44b3f}
.r{display:grid;grid-template-columns:200px minmax(0,1fr) 34px minmax(0,1.25fr);align-items:center;gap:12px;padding:9px 0;border-bottom:1px solid #e7e3da}
.s{font-size:16px;color:#8a867d;font-family:"Liberation Mono","DejaVu Sans Mono",monospace}
.v{font-family:"Liberation Mono","DejaVu Sans Mono",monospace;font-size:21px;padding:6px 10px;border-radius:6px;overflow-wrap:anywhere}
.kirli{background:#f3e3df;color:#8f2f25}.dogru{background:#e1efe6;color:#1f6b44}.notr{background:#ebe8e1;color:#4d4a44}
.yanlis{background:#f7e9cf;color:#8a5a0c}.ok{font-size:22px;color:#9a968d;text-align:center}
.g{display:block;font-size:15px;color:#6d6a63;margin-top:3px}
.kaynak{margin-top:30px;font-size:17px;color:#6d6a63;display:flex;justify-content:space-between}"""
h=(f"<!doctype html><html lang='tr'><head><meta charset='utf-8'>{FONT}<style>{css}</style></head><body>"
 "<h1>Kirli veri, kuralların elinden geçince</h1><p class='alt'>Gerçek örnekler · LLM yok · sentetik e-ticaret verisi</p>"
 "<div class='y'><h2><span class='n'>✓</span>Düzeltti</h2>"+"".join(satir(*x,"dogru") for x in duzeldi)+"</div>"
 "<div class='b'><h2><span class='n'>–</span>Doğru olanı yaptı: uydurmadı</h2>"+"".join(satir(*x,"notr") for x in bos)+"</div>"
 "<div class='x'><h2><span class='n'>✗</span>Yapamadı</h2>"+"".join(satir(s,k,t,"yanlis",g) for s,k,t,g in olmadi)+"</div>"
 "<div class='kaynak'><span>Sıradaki soru: LLM bunları uydurmadan çözebilir mi?</span><span>github.com/sefa05/Claude-veri-temizleme-</span></div></body></html>")
ekran_goruntusu(h,"gorseller/kirli_temiz_ornekler.png")
