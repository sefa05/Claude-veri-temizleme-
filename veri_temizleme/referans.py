"""Referans (ana) veri: iller, ilçeler, adlar, kategoriler ve alan sözlükleri.

Temizleme yöntemleri bu listeleri "ana veri" olarak kullanabilir. Gerçek bir şirkette de il listesi, kategori ağacı
ve kargo firmaları bilinen sabitlerdir. Bozma kataloğu ise hiçbir temizleyiciye verilmez.
"""

from __future__ import annotations

ILLER: dict[int, str] = {
    1: "Adana", 2: "Adıyaman", 3: "Afyonkarahisar", 4: "Ağrı", 5: "Amasya", 6: "Ankara", 7: "Antalya",
    8: "Artvin", 9: "Aydın", 10: "Balıkesir", 11: "Bilecik", 12: "Bingöl", 13: "Bitlis", 14: "Bolu",
    15: "Burdur", 16: "Bursa", 17: "Çanakkale", 18: "Çankırı", 19: "Çorum", 20: "Denizli", 21: "Diyarbakır",
    22: "Edirne", 23: "Elazığ", 24: "Erzincan", 25: "Erzurum", 26: "Eskişehir", 27: "Gaziantep", 28: "Giresun",
    29: "Gümüşhane", 30: "Hakkari", 31: "Hatay", 32: "Isparta", 33: "Mersin", 34: "İstanbul", 35: "İzmir",
    36: "Kars", 37: "Kastamonu", 38: "Kayseri", 39: "Kırklareli", 40: "Kırşehir", 41: "Kocaeli", 42: "Konya",
    43: "Kütahya", 44: "Malatya", 45: "Manisa", 46: "Kahramanmaraş", 47: "Mardin", 48: "Muğla", 49: "Muş",
    50: "Nevşehir", 51: "Niğde", 52: "Ordu", 53: "Rize", 54: "Sakarya", 55: "Samsun", 56: "Siirt", 57: "Sinop",
    58: "Sivas", 59: "Tekirdağ", 60: "Tokat", 61: "Trabzon", 62: "Tunceli", 63: "Şanlıurfa", 64: "Uşak",
    65: "Van", 66: "Yozgat", 67: "Zonguldak", 68: "Aksaray", 69: "Bayburt", 70: "Karaman", 71: "Kırıkkale",
    72: "Batman", 73: "Şırnak", 74: "Bartın", 75: "Ardahan", 76: "Iğdır", 77: "Yalova", 78: "Karabük",
    79: "Kilis", 80: "Osmaniye", 81: "Düzce",
}

# Müşteri üretiminde kullanılan iller: (ilçeler, yaklaşık nüfus ağırlığı). İlçe adları bu küme içinde tekildir.
IL_ILCELER: dict[str, tuple[list[str], float]] = {
    "İstanbul": (["Kadıköy", "Beşiktaş", "Üsküdar", "Şişli", "Bakırköy", "Ataşehir", "Maltepe", "Pendik",
                  "Esenyurt", "Bahçelievler", "Beylikdüzü", "Sarıyer", "Kartal", "Ümraniye", "Fatih", "Beyoğlu",
                  "Başakşehir", "Küçükçekmece"], 18.0),
    "Ankara": (["Çankaya", "Keçiören", "Yenimahalle", "Mamak", "Etimesgut", "Sincan", "Altındağ", "Pursaklar",
                "Gölbaşı"], 6.5),
    "İzmir": (["Karşıyaka", "Bornova", "Buca", "Konak", "Çiğli", "Bayraklı", "Karabağlar", "Gaziemir", "Menemen",
               "Torbalı"], 5.2),
    "Bursa": (["Osmangazi", "Nilüfer", "Yıldırım", "İnegöl", "Gemlik", "Mudanya"], 3.6),
    "Antalya": (["Muratpaşa", "Kepez", "Konyaaltı", "Alanya", "Manavgat"], 3.0),
    "Adana": (["Seyhan", "Çukurova", "Yüreğir", "Sarıçam", "Ceyhan"], 2.4),
    "Konya": (["Selçuklu", "Meram", "Karatay", "Akşehir"], 2.4),
    "Gaziantep": (["Şahinbey", "Şehitkamil", "Nizip"], 2.2),
    "Kocaeli": (["İzmit", "Gebze", "Darıca", "Körfez", "Gölcük"], 2.1),
    "Mersin": (["Yenişehir", "Toroslar", "Akdeniz", "Mezitli", "Tarsus"], 2.0),
    "Kayseri": (["Melikgazi", "Kocasinan", "Talas"], 1.5),
    "Eskişehir": (["Odunpazarı", "Tepebaşı"], 0.9),
    "Diyarbakır": (["Bağlar", "Kayapınar", "Bismil"], 1.8),
    "Samsun": (["Atakum", "İlkadım", "Canik", "Bafra"], 1.4),
    "Denizli": (["Pamukkale", "Merkezefendi", "Çivril"], 1.1),
    "Trabzon": (["Ortahisar", "Akçaabat", "Of"], 0.8),
    "Tekirdağ": (["Süleymanpaşa", "Çorlu", "Çerkezköy"], 1.1),
    "Muğla": (["Bodrum", "Fethiye", "Marmaris", "Menteşe"], 1.0),
    "Sakarya": (["Adapazarı", "Serdivan", "Erenler"], 1.1),
    "Manisa": (["Yunusemre", "Şehzadeler", "Akhisar", "Turgutlu"], 1.4),
    "Aydın": (["Efeler", "Kuşadası", "Nazilli", "Didim"], 1.1),
    "Balıkesir": (["Karesi", "Altıeylül", "Bandırma", "Edremit"], 1.2),
    "Hatay": (["Antakya", "İskenderun", "Defne"], 1.5),
    "Malatya": (["Battalgazi", "Yeşilyurt"], 0.8),
}

ILCE_IL: dict[str, str] = {ilce: il for il, (ilceler, _) in IL_ILCELER.items() for ilce in ilceler}

KADIN_ADLARI = [
    "Ayşe", "Fatma", "Emine", "Hatice", "Zeynep", "Elif", "Meryem", "Şerife", "Zehra", "Sultan", "Hanife", "Merve",
    "Özlem", "Esra", "Büşra", "Gül", "Derya", "Ebru", "Seda", "Tuğba", "Gizem", "Yasemin", "Dilek", "Sibel", "Özge",
    "Buse", "Ceren", "Damla", "Irmak", "Nur", "Şeyma", "Ecem", "Gamze", "İrem", "Pınar", "Aslı", "Çağla", "Nazlı",
    "Selin", "Ece", "Aylin", "Sevgi", "Hülya", "Gülşen", "Nesrin", "Songül", "Şule", "Tülay", "Yağmur", "Başak",
    "Melike", "Rabia", "Kübra", "Duygu", "Burcu", "Canan", "Didem", "Filiz", "Leyla",
]
ERKEK_ADLARI = [
    "Mehmet", "Mustafa", "Ahmet", "Ali", "Hüseyin", "Hasan", "İbrahim", "İsmail", "Osman", "Yusuf", "Murat", "Ömer",
    "Ramazan", "Halil", "Süleyman", "Abdullah", "Mahmut", "Salih", "Kemal", "Recep", "Emre", "Burak", "Serkan",
    "Oğuz", "Çağlar", "Barış", "Gökhan", "Onur", "Tolga", "Uğur", "Volkan", "Kaan", "Berk", "Arda", "Eren",
    "Emir", "Yiğit", "Doğan", "Erkan", "Sinan", "Tuncay", "Cem", "Erdem", "Özgür", "Levent", "Selim", "Tarık",
    "İlker", "Görkem", "Batuhan", "Furkan", "Enes", "Kerem", "Alper", "Hakan", "Orhan", "Cengiz", "Tayfun",
]
SOYADLARI = [
    "Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Yıldız", "Yıldırım", "Öztürk", "Aydın", "Özdemir", "Arslan",
    "Doğru", "Kılıç", "Aslan", "Çetin", "Kara", "Koç", "Kurt", "Özkan", "Şimşek", "Polat", "Özcan", "Korkmaz",
    "Çakır", "Erdoğan", "Yavuz", "Acar", "Şen", "Aktaş", "Güler", "Yalçın", "Güneş", "Bozkurt", "Bulut",
    "Keskin", "Ünal", "Turan", "Gül", "Özer", "Işık", "Kaplan", "Avcı", "Sarı", "Tekin", "Taş", "Köse", "Yüksel",
    "Ateş", "Aksoy", "Uçar", "Karataş", "Çiftçi", "Tuncer", "Kocabaş", "Uysal", "Akın", "Çınar", "Başaran",
    "Günay", "Kalkan", "Sönmez", "Ekinci", "Tunç", "Duman", "Oral", "Karakaya", "Toprak", "Altun", "Durmaz",
    "Bayram", "Coşkun", "Gündoğdu", "Ergün", "Akbulut", "Şeker",
]

CINSIYETLER = ["Kadın", "Erkek"]

EPOSTA_ALANLARI = {"gmail.com": 0.55, "hotmail.com": 0.2, "outlook.com": 0.1, "yahoo.com": 0.08, "icloud.com": 0.07}

# kategori: (ürün tipleri, markalar, (min fiyat, max fiyat))
KATEGORILER: dict[str, tuple[list[str], list[str], tuple[float, float]]] = {
    "Elektronik": (["Akıllı Telefon", "Kablosuz Kulaklık", "Laptop", "Tablet", "Akıllı Saat", "Bluetooth Hoparlör",
                    "Powerbank", "Monitör"],
                   ["Samsung", "Apple", "Xiaomi", "Lenovo", "Huawei", "JBL", "Anker", "Casper"], (350, 65000)),
    "Giyim": (["Tişört", "Kot Pantolon", "Mont", "Sweatshirt", "Elbise", "Gömlek"],
              ["LC Waikiki", "Koton", "DeFacto", "Mavi", "Zara", "Colin's"], (150, 3500)),
    "Ev & Yaşam": (["Nevresim Takımı", "Yemek Takımı", "Tencere Seti", "Havlu Seti", "Masa Lambası", "Halı"],
                   ["English Home", "Karaca", "Madame Coco", "Taç", "Paşabahçe"], (200, 8000)),
    "Kozmetik": (["Parfüm", "Nemlendirici Krem", "Şampuan", "Ruj", "Güneş Kremi", "Maskara"],
                 ["Flormar", "Nivea", "L'Oréal", "Golden Rose", "Garnier"], (60, 4000)),
    "Kitap": (["Roman", "Kişisel Gelişim Kitabı", "Çocuk Kitabı", "Tarih Kitabı", "Bilim Kurgu Romanı"],
              ["Can Yayınları", "İş Bankası Kültür Yayınları", "YKY", "Doğan Kitap", "Pegasus"], (40, 450)),
    "Spor & Outdoor": (["Koşu Ayakkabısı", "Yoga Matı", "Dambıl Seti", "Kamp Çadırı", "Bisiklet Kaskı", "Termos"],
                       ["Nike", "Adidas", "Puma", "Decathlon", "Columbia"], (150, 9000)),
    "Oyuncak": (["Yapı Seti", "Oyuncak Araba", "Peluş Ayı", "Yapboz", "Kutu Oyunu"],
                ["Lego", "Hasbro", "Mattel", "Fisher-Price"], (100, 3500)),
    "Süpermarket": (["Kahve", "Zeytinyağı", "Deterjan", "Çay", "Bebek Bezi"],
                    ["Nescafé", "Komili", "Ariel", "Çaykur", "Prima"], (50, 900)),
}

ODEME_YONTEMLERI = {"Kredi Kartı": 0.55, "Banka Kartı": 0.2, "Havale/EFT": 0.08, "Kapıda Ödeme": 0.07,
                    "Dijital Cüzdan": 0.1}
KARGO_FIRMALARI = {"Yurtiçi Kargo": 0.25, "Aras Kargo": 0.17, "MNG Kargo": 0.12, "PTT Kargo": 0.08,
                   "Sürat Kargo": 0.06, "Trendyol Express": 0.18, "HepsiJet": 0.14}
DURUMLAR = {"Teslim Edildi": 0.8, "Kargoda": 0.06, "Hazırlanıyor": 0.04, "İptal Edildi": 0.05, "İade Edildi": 0.05}
TESLIMSIZ_DURUMLAR = {"Kargoda", "Hazırlanıyor", "İptal Edildi"}
INDIRIM_ORANLARI = {0.0: 0.55, 0.05: 0.12, 0.1: 0.15, 0.15: 0.08, 0.2: 0.06, 0.25: 0.04}

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım",
         "Aralık"]

SAYI_KELIMELERI = {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8,
                   "dokuz": 9, "on": 10}

# Tablo şemaları: sütun -> tip. Tüm yöntemler ve ölçüm bu tanımı ortak kullanır.
SEMA: dict[str, dict[str, str]] = {
    "musteriler": {
        "musteri_id": "id", "ad": "isim", "soyad": "isim", "eposta": "eposta", "telefon": "telefon",
        "dogum_tarihi": "tarih", "cinsiyet": "secenek", "il": "il", "ilce": "ilce", "kayit_tarihi": "tarih",
    },
    "urunler": {
        "urun_id": "id", "urun_adi": "metin", "kategori": "secenek", "marka": "metin", "birim_fiyat": "para",
    },
    "siparisler": {
        "siparis_id": "id", "musteri_id": "ref", "urun_id": "ref", "siparis_tarihi": "tarih", "adet": "adet",
        "birim_fiyat": "para", "indirim_orani": "oran", "toplam_tutar": "para", "odeme_yontemi": "secenek",
        "kargo_firmasi": "secenek", "teslim_tarihi": "tarih", "durum": "secenek",
    },
}
ANAHTARLAR = {"musteriler": "musteri_id", "urunler": "urun_id", "siparisler": "siparis_id"}
ID_ONEKLERI = {"musteri_id": ("M", 5), "urun_id": ("U", 4), "siparis_id": ("S", 6)}

SECENEKLER: dict[str, list[str]] = {
    "cinsiyet": CINSIYETLER,
    "kategori": list(KATEGORILER),
    "odeme_yontemi": list(ODEME_YONTEMLERI),
    "kargo_firmasi": list(KARGO_FIRMALARI),
    "durum": list(DURUMLAR),
}
