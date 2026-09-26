# Kararsızım — Proje Rehberi (CLAUDE.md)

Bu dosya, **Kararsızım** web uygulamasının tüm detaylarını içerir. Claude Code bu dosyayı projenin tek doğru kaynağı olarak kullanmalıdır.

\---

## 0\. Claude Code İçin Çalışma Kuralları

* Proje **fazlara** bölünmüştür (bkz. Bölüm 8). **Her seferinde yalnızca istenen fazı uygula.** Faz bitince yapılanları özetle, nasıl test edileceğini yaz ve bir sonraki faza geçmeden onay bekle.
* Bu bir **prototip**. Basit, okunabilir ve az bağımlılıklı çözümleri tercih et. Celery, Redis, Docker, React/Vue, Tailwind build süreci, DRF gibi ek teknolojiler **ekleme**.
* Arayüz metinleri **Türkçe**, kod (değişken, fonksiyon, sınıf adları) ve yorumlar **İngilizce** olsun.
* Gizli bilgileri (SECRET\_KEY, veritabanı şifresi) asla koda yazma; `.env` dosyasından oku ve `.env`'yi `.gitignore`'a ekle. Bunun yerine `.env.example` oluştur.
* Her fazın sonunda `python manage.py check` çalıştır ve hatasız olduğundan emin ol.

\---

## 1\. Proje Özeti

**Kararsızım**, kullanıcıların kararsız kaldıkları konularda diğer kullanıcılara danışabildiği basit bir anket platformudur.

Örnek: *"Bugün sinemaya mı gitsem, yemeğe mi?"* → Seçenekler: `Sinema`, `Yemek`, `Evde dizi`

### Temel kurallar

|Kural|Açıklama|
|-|-|
|Seçenek sayısı|Her ankette **en az 2, en fazla 5** seçenek|
|Oy kullanma|**Üye olmadan** oy kullanılabilir|
|Anket açma|**Sadece üyeler** anket açabilir|
|Görünürlük|Takip/arkadaşlık sistemi **yok**. Herkes platformdaki **tüm anketleri** görür|
|Oy sınırı|Her ziyaretçi/kullanıcı bir ankette **yalnızca 1 kez** oy verir|
|Kayıt bilgileri|E-posta + kullanıcı adı + şifre|

\---

## 2\. Teknoloji Yığını

|Katman|Teknoloji|
|-|-|
|Backend|Python 3.12, Django 5.x|
|Veritabanı|Supabase (PostgreSQL)|
|Frontend|Django şablonları + saf HTML, CSS, JavaScript (framework yok, aynı repo)|
|Statik dosyalar|WhiteNoise|
|Deployment|Vercel (Python serverless runtime)|

### requirements.txt

```
Django>=5.0,<6.0
dj-database-url
psycopg\[binary]
whitenoise
python-dotenv
```

\---

## 3\. Klasör Yapısı

```
kararsizim/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── vercel.json
├── .env.example
├── .gitignore
├── manage.py
├── config/                 # Django proje ayarları
│   ├── \_\_init\_\_.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/               # Kayıt, giriş, çıkış, özel User modeli
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── polls/                  # Anketler, seçenekler, oylar
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── utils.py            # voter token yardımcıları
│   └── admin.py
├── templates/
│   ├── base.html
│   ├── partials/
│   │   ├── navbar.html
│   │   ├── messages.html
│   │   └── poll\_card.html
│   ├── accounts/
│   │   ├── register.html
│   │   └── login.html
│   └── polls/
│       ├── poll\_list.html
│       ├── poll\_detail.html
│       ├── poll\_create.html
│       └── my\_polls.html
└── static/
    ├── css/
    │   └── main.css
    └── js/
        ├── poll\_create.js  # seçenek ekle/çıkar
        └── poll\_vote.js    # fetch ile oy verme + sonuç animasyonu
```

\---

## 4\. Veri Modelleri

### 4.1 `accounts.User` (özel kullanıcı modeli)

**Önemli:** İlk migration'dan **önce** oluşturulmalı. `settings.AUTH\_USER\_MODEL = "accounts.User"`.

`AbstractUser`'dan türetilir:

* `username` — zorunlu, benzersiz, 3–20 karakter, sadece harf, rakam, `\_` ve `.`
* `email` — zorunlu, **benzersiz** (`unique=True`), küçük harfe çevrilerek kaydedilir
* Giriş **e-posta veya kullanıcı adı** ile yapılabilir (basit bir özel authentication backend ile).

### 4.2 `polls.Poll`

|Alan|Tip|Not|
|-|-|-|
|`author`|FK → User|`on\_delete=CASCADE`, `related\_name="polls"`|
|`question`|CharField(200)|zorunlu, min 5 karakter|
|`description`|TextField|opsiyonel, max 500 karakter|
|`is\_active`|Boolean|varsayılan `True`; `False` ise oy alınmaz|
|`created\_at`|DateTime|`auto\_now\_add`|

* `Meta.ordering = \["-created\_at"]`
* `total\_votes` için property veya `annotate(Count("votes"))` kullan.

### 4.3 `polls.Option`

|Alan|Tip|Not|
|-|-|-|
|`poll`|FK → Poll|`related\_name="options"`|
|`text`|CharField(80)|zorunlu|
|`order`|PositiveSmallInteger|seçenek sırası|

### 4.4 `polls.Vote`

|Alan|Tip|Not|
|-|-|-|
|`poll`|FK → Poll|`related\_name="votes"` (hızlı sayım için)|
|`option`|FK → Option|`related\_name="votes"`|
|`user`|FK → User|`null=True`, üye oyları için|
|`voter\_token`|CharField(64)|anonim ziyaretçiyi tanımlayan UUID|
|`created\_at`|DateTime|`auto\_now\_add`|

**Tekrar oy engelleme (veritabanı seviyesinde):**

```python
constraints = \[
    models.UniqueConstraint(fields=\["poll", "voter\_token"], name="unique\_vote\_per\_token"),
    models.UniqueConstraint(
        fields=\["poll", "user"],
        condition=models.Q(user\_\_isnull=False),
        name="unique\_vote\_per\_user",
    ),
]
```

### 4.5 Anonim oy mantığı (voter token)

* Ziyaretçinin tarayıcısında `kz\_voter` adında bir **cookie** tutulur (UUID4, 1 yıl geçerli, `httponly`, `samesite=Lax`, prod'da `secure`).
* Cookie yoksa oy verilirken oluşturulur ve response'a eklenir.
* Giriş yapmış kullanıcı oy verirken hem `user` hem `voter\_token` kaydedilir. Kontrol önce `user`, sonra `voter\_token` üzerinden yapılır.
* Bu prototip için yeterli bir önlemdir; cookie silinerek aşılabileceği bilinir ve kabul edilir.

\---

## 5\. Sayfalar ve URL'ler

|URL|View|Erişim|Açıklama|
|-|-|-|-|
|`/`|`poll\_list`|Herkes|Tüm anketler, en yeniden eskiye, sayfalama (12'şer)|
|`/anket/<id>/`|`poll\_detail`|Herkes|Soru, seçenekler, oy verme / sonuçlar|
|`/anket/<id>/oy/`|`poll\_vote` (POST)|Herkes|Oy kaydı; JSON veya redirect döner|
|`/anket/yeni/`|`poll\_create`|**Üye**|Anket oluşturma formu|
|`/anketlerim/`|`my\_polls`|**Üye**|Kullanıcının kendi anketleri|
|`/anket/<id>/kapat/`|`poll\_toggle` (POST)|**Sahibi**|Anketi oylamaya kapat/aç|
|`/anket/<id>/sil/`|`poll\_delete` (POST)|**Sahibi**|Anketi sil (onay ile)|
|`/kayit/`|`register`|Misafir|Kayıt formu; başarılıysa otomatik giriş|
|`/giris/`|`login`|Misafir|E-posta veya kullanıcı adı + şifre|
|`/cikis/`|`logout` (POST)|Üye|Çıkış|
|`/admin/`|Django admin|Superuser|Yönetim|

* Üye olmayan biri `/anket/yeni/`'ye girerse `/giris/?next=/anket/yeni/`'ye yönlendirilir ve *"Anket açmak için giriş yapmalısın 👋"* mesajı gösterilir.
* Ana sayfada misafirlere belirgin bir **"Sen de sor!"** butonu gösterilir; tıklayınca kayıt/girişe gider.

\---

## 6\. İş Kuralları ve Doğrulamalar

### Anket oluşturma

* Soru: 5–200 karakter, boş olamaz.
* Seçenekler: **2 ile 5 arası**, her biri 1–80 karakter.
* Boş seçenek alanları yok sayılır; kalan dolu seçenek sayısı 2'den azsa hata.
* Aynı ankette **tekrar eden seçenek olamaz** (büyük/küçük harf ve baştaki/sondaki boşluk yok sayılarak karşılaştır).
* Poll ve Option kayıtları `transaction.atomic()` içinde oluşturulur.
* Formset yerine basit yaklaşım: formda `option` adlı birden fazla input, view'da `request.POST.getlist("option")` ile okunur ve bir form `clean()` metodunda doğrulanır.

### Oy verme

* Anket `is\_active=False` ise oy kabul edilmez.
* Seçilen `option` gerçekten o ankete ait olmalı.
* Daha önce oy verilmişse (user veya token eşleşmesi) yeni oy kaydedilmez; `IntegrityError` da yakalanır.
* Oy verdikten sonra kullanıcı **sonuçları** görür (yüzde + oy sayısı + kendi seçtiği işaretli).
* Oy **vermemiş** kullanıcı sonuçları görmez (etkilenmemesi için); sadece toplam oy sayısını görür.
* Anket sahibi kendi anketinin sonuçlarını her zaman görür ve kendi anketine de oy verebilir.
* Kapalı anketlerde herkes sonuçları görür.

### Oy endpoint'i (`POST /anket/<id>/oy/`)

* Normal form POST'u ile çalışır (JS kapalıyken de çalışmalı → redirect).
* `fetch` ile `X-Requested-With: XMLHttpRequest` veya `Accept: application/json` gelirse JSON döner:

```json
{
  "ok": true,
  "total\_votes": 42,
  "voted\_option\_id": 7,
  "results": \[
    {"id": 7, "text": "Sinema", "votes": 25, "percent": 59.5},
    {"id": 8, "text": "Yemek", "votes": 17, "percent": 40.5}
  ]
}
```

* Hata durumunda: `{"ok": false, "error": "Bu ankete zaten oy verdin."}` ve uygun HTTP kodu (400/403/409).

\---

## 7\. Arayüz Tasarımı

### Genel his

Gençlere hitap eden, **açık arka planlı**, **canlı renklerin açık tonlarıyla boyanmış** yüzeyler, yuvarlak köşeler, eğlenceli ama sade. Mobil öncelikli (mobile-first) tasarım.

### Renk paleti (CSS değişkenleri olarak `:root` içinde)

```css
:root {
  /\* Zemin \*/
  --bg: #FBFAFF;
  --surface: #FFFFFF;
  --text: #1E1B2E;
  --text-muted: #6B6880;
  --border: #ECE8F7;

  /\* Canlı ana renkler \*/
  --purple: #7C3AED;
  --pink: #EC4899;
  --orange: #F97316;
  --yellow: #FACC15;
  --teal: #14B8A6;
  --blue: #3B82F6;

  /\* Açık tonlar (kart ve rozet zeminleri) \*/
  --purple-tint: #F3E8FF;
  --pink-tint: #FCE7F3;
  --orange-tint: #FFEDD5;
  --yellow-tint: #FEF9C3;
  --teal-tint: #CCFBF1;
  --blue-tint: #DBEAFE;

  --primary: var(--purple);
  --primary-gradient: linear-gradient(135deg, var(--purple), var(--pink));

  --radius-sm: 10px;
  --radius: 18px;
  --radius-lg: 28px;
  --shadow: 0 6px 20px rgba(124, 58, 237, 0.10);
}
```

### Tipografi

* Google Fonts: **"Poppins"** (başlıklar, 600–800) ve **"Inter"** (gövde, 400–500); yedek: `system-ui, sans-serif`.
* Başlıklar büyük ve kalın, gövde metni 16px.

### Bileşenler

* **Navbar:** Solda logo "kararsızım 🤔" (gradient metin), sağda misafir için `Giriş` / `Kayıt ol`, üye için `+ Anket aç`, `Anketlerim`, `@kullaniciadi`, `Çıkış`.
* **Anket kartı:** Beyaz kart, üstte ince renkli şerit. Kart renkleri sırayla dönen tint'lerden seçilir (mor, pembe, turuncu, turkuaz, mavi). İçerik: soru, `@yazar`, "3 saat önce" (`timesince`), toplam oy rozeti, "Oy ver →" butonu.
* **Seçenek butonları (detay sayfası):** Her seçenek büyük, tam genişlik, yuvarlak buton; her biri farklı bir tint renginde. Hover'da hafif büyüme (`transform: scale(1.02)`).
* **Sonuç çubukları:** Seçeneğin renginde dolan yatay bar; genişlik `0`'dan yüzdeye CSS transition ile animasyonlu dolar. Kullanıcının seçtiği seçenekte ✓ işareti.
* **Butonlar:** Ana buton gradient (`--primary-gradient`), beyaz yazı, `border-radius: 999px`.
* **Mesajlar (Django messages):** Başarı = teal tint, hata = pink tint, bilgi = blue tint; birkaç saniye sonra JS ile kaybolur.
* **Boş durum:** Hiç anket yoksa büyük emoji + "Henüz kimse kararsız değil… İlk soruyu sen sor!" metni.
* Emoji kullanımı serbest ama abartılmamalı.

### Anket oluşturma sayfası (JS)

* Başlangıçta 2 seçenek input'u görünür.
* "+ Seçenek ekle" butonu; 5'e ulaşınca devre dışı kalır.
* 

  3. seçenekten itibaren her input'un yanında "×" silme butonu; 2'nin altına inilemez.
* Canlı karakter sayacı (soru için 0/200).
* Aynı doğrulamalar sunucu tarafında da **mutlaka** yapılır (JS sadece kolaylık).

### Oy verme (JS)

* Form submit'i `fetch` ile yakalanır, CSRF token cookie'den veya formdaki hidden input'tan alınır.
* Başarılı yanıtta seçenek butonları sonuç çubuklarına dönüşür (animasyonlu).
* JS kapalıysa form normal POST olarak çalışır.

### Erişilebilirlik

* Yeterli kontrast, `:focus-visible` stilleri, form input'larında `label`, butonlarda anlamlı metin.
* `prefers-reduced-motion` açıksa animasyonları kapat.

\---

## 8\. Fazlar

> Claude Code: Aşağıdaki fazları \*\*sırayla ve teker teker\*\* uygula. Her fazın sonunda "Kabul kriterleri"ni kontrol et.

### Faz 1 — Proje iskeleti ve ayarlar

* Django projesi (`config`) ve `accounts`, `polls` uygulamalarını oluştur.
* `requirements.txt`, `.gitignore`, `.env.example`, `README.md` oluştur.
* `settings.py`:

  * `python-dotenv` ile `.env` okunur.
  * `SECRET\_KEY`, `DEBUG`, `ALLOWED\_HOSTS`, `CSRF\_TRUSTED\_ORIGINS` ortam değişkenlerinden.
  * `DATABASE\_URL` tanımlıysa `dj\_database\_url` ile kullanılır, **tanımlı değilse yerel SQLite** (geliştirme kolaylığı).
  * `LANGUAGE\_CODE = "tr"`, `TIME\_ZONE = "Europe/Istanbul"`, `USE\_TZ = True`.
  * `TEMPLATES\["DIRS"] = \[BASE\_DIR / "templates"]`, `STATICFILES\_DIRS = \[BASE\_DIR / "static"]`, `STATIC\_ROOT = BASE\_DIR / "staticfiles"`.
  * WhiteNoise middleware (`SecurityMiddleware`'den hemen sonra).
* `accounts.User` özel modelini oluştur, `AUTH\_USER\_MODEL` ayarla, **ardından** ilk migration'ı yap.
* `base.html` ve `main.css` içinde renk değişkenleri + temel layout.

**Kabul kriterleri:** `python manage.py runserver` ile boş ana sayfa, yeni renk temasıyla açılıyor; `migrate` hatasız; admin paneline giriliyor.

### Faz 2 — Üyelik sistemi

* Kayıt formu: kullanıcı adı, e-posta, şifre, şifre tekrar. Django'nun şifre doğrulayıcıları aktif.
* E-posta ve kullanıcı adı benzersizliği için anlaşılır Türkçe hata mesajları.
* E-posta **veya** kullanıcı adı ile giriş yapan authentication backend.
* Kayıttan sonra otomatik giriş ve ana sayfaya yönlendirme.
* Çıkış (POST ile).
* Navbar'ın giriş durumuna göre değişmesi.
* Giriş yapmış kullanıcı `/kayit/` veya `/giris/`'e girerse ana sayfaya yönlendirilir.

**Kabul kriterleri:** Kayıt ol → otomatik giriş → çıkış → e-posta ile giriş → çıkış → kullanıcı adı ile giriş akışı çalışıyor. Aynı e-posta ile ikinci kayıt engelleniyor.

### Faz 3 — Anketler ve oylama

* `Poll`, `Option`, `Vote` modelleri, migration'lar ve admin kayıtları (Poll admin'inde Option inline).
* Anket oluşturma (sadece üyeler) + `poll\_create.js`.
* Ana sayfa anket listesi (sayfalama, oy sayısı `annotate` ile, N+1 sorgudan kaçın: `select\_related("author")`).
* Anket detay + oy verme (anonim + üye), voter token cookie mantığı.
* `poll\_vote.js` ile sayfa yenilenmeden oylama ve animasyonlu sonuçlar.
* "Anketlerim" sayfası, anketi kapat/aç ve sil (sadece sahibi, POST + onay).

**Kabul kriterleri:**

* Misafir oy verebiliyor ama anket açamıyor (girişe yönlendiriliyor).
* 1 veya 6 seçenekli anket oluşturulamıyor (hem JS hem sunucu).
* Aynı tarayıcıdan ikinci oy engelleniyor; gizli sekmeden farklı oy verilebiliyor.
* Oy vermeden sonuç görünmüyor, oy verince görünüyor.
* Başkasının anketi silinemiyor/kapatılamıyor (403).

### Faz 4 — Arayüz cilası

* Bölüm 7'deki tüm bileşenlerin tamamlanması: renkli kartlar, gradient butonlar, sonuç animasyonları, boş durumlar, mesajların otomatik kaybolması.
* Mobil (360px), tablet ve masaüstünde kontrol; yatay kaydırma olmamalı.
* Özel 404 ve 500 sayfaları (aynı temada).
* Favicon (emoji tabanlı SVG) ve sayfa başlıkları (`<title>Kararsızım · ...</title>`).

**Kabul kriterleri:** Tüm sayfalar tutarlı temada, mobilde rahat kullanılıyor.

### Faz 5 — Supabase ve Vercel'e yayın

**Supabase:**

* Supabase'de proje oluşturulur; *Project Settings → Database → Connection string* kısmından **Connection pooler (Transaction mode, port 6543)** adresi alınır ve `DATABASE\_URL` olarak kullanılır.
* Pooler (PgBouncer transaction modu) nedeniyle ayarlar:

```python
  DATABASES\["default"]\["CONN\_MAX\_AGE"] = 0
  DATABASES\["default"]\["DISABLE\_SERVER\_SIDE\_CURSORS"] = True
  ```

  ve bağlantı için `sslmode=require`.

* Migration'lar **yerel makineden** Supabase'e karşı çalıştırılır: `DATABASE\_URL=... python manage.py migrate`. Vercel üzerinde migrate çalıştırılmaz.
* Superuser yine yerelden oluşturulur.

**Vercel:**

* `config/wsgi.py` sonuna `app = application` ekle (Vercel bu değişkeni arar).
* `vercel.json` (klasik Python runtime yapılandırması; Vercel'in güncel Python/Django dokümanıyla karşılaştır, gerekirse güncelle):

```json
  {
    "builds": \[
      { "src": "config/wsgi.py", "use": "@vercel/python" }
    ],
    "routes": \[
      { "src": "/(.\*)", "dest": "config/wsgi.py" }
    ]
  }
  ```

* Statik dosyalar: WhiteNoise ile Django üzerinden sunulur. Build adımında `collectstatic` ile uğraşmamak için prototipte `WHITENOISE\_USE\_FINDERS = True` kullan (statik dosyalar doğrudan `static/` klasöründen bulunur).
* Vercel ortam değişkenleri: `SECRET\_KEY`, `DEBUG=False`, `DATABASE\_URL`, `ALLOWED\_HOSTS=.vercel.app`, `CSRF\_TRUSTED\_ORIGINS=https://<proje>.vercel.app`.
* Prod güvenlik ayarları (`DEBUG=False` iken): `SESSION\_COOKIE\_SECURE`, `CSRF\_COOKIE\_SECURE`, `SECURE\_PROXY\_SSL\_HEADER = ("HTTP\_X\_FORWARDED\_PROTO", "https")`.
* Oturumlar veritabanında tutulur (varsayılan `db` backend) — Supabase'e yazıldığı için serverless ortamda da kalıcıdır.
* `README.md`'ye adım adım yayın talimatları ekle.

**Kabul kriterleri:** Vercel URL'sinde kayıt, giriş, anket açma, oy verme uçtan uca çalışıyor; CSS/JS yükleniyor; veriler Supabase'de görünüyor.

\---

## 9\. Kapsam Dışı (Şimdilik Yapılmayacak)

Bunlar ileride eklenebilir, **prototipte yapılmayacak**:

* Takip, arkadaşlık, bildirim sistemi
* Yorumlar, beğeniler
* E-posta doğrulama ve şifre sıfırlama e-postaları
* Görsel/fotoğraf yükleme
* Anketlere süre/bitiş tarihi
* Kategoriler, etiketler, arama
* REST API, mobil uygulama
* Rate limiting, bot koruması

\---

## 10\. Test

* Her uygulama için `tests.py` içinde temel testler yaz (Faz 2 ve Faz 3'te):

  * Kayıt, e-posta/kullanıcı adı ile giriş.
  * Anonim kullanıcının anket oluşturma sayfasına erişememesi.
  * 2–5 seçenek doğrulaması ve tekrar eden seçenek engeli.
  * Aynı token ile ikinci oyun engellenmesi.
  * Başka birinin anketine silme/kapama isteğinde 403.
* Testler `python manage.py test` ile çalışmalı (yerelde SQLite kullanır).

