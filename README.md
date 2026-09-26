# Kararsızım 🤔

Kararsız kaldığın konularda başkalarına danışabildiğin basit bir anket platformu.
Django 5 + saf HTML/CSS/JS. Üye olmadan oy verilir, anket açmak için üyelik gerekir.

Proje kuralları ve tüm detaylar için: [CLAUDE.md](CLAUDE.md)

## Yerelde çalıştırma

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

`.env` içinde `DEBUG=True` olmalı. `DATABASE_URL` boşsa yerel SQLite (`db.sqlite3`) kullanılır.

## Testler

```bash
python manage.py test
```

## Ortam değişkenleri

| Değişken | Açıklama |
|-|-|
| `SECRET_KEY` | Django gizli anahtarı (`DEBUG=False` iken zorunlu) |
| `DEBUG` | `True` / `False` |
| `ALLOWED_HOSTS` | Virgülle ayrılmış host listesi |
| `CSRF_TRUSTED_ORIGINS` | Virgülle ayrılmış, şemalı origin listesi (`https://...`) |
| `DATABASE_URL` | Boşsa SQLite; doluysa (Supabase pooler) PostgreSQL |

## Yayına alma (Supabase + Vercel)

### 1. Supabase (veritabanı)

1. [supabase.com](https://supabase.com) üzerinde yeni bir proje oluştur ve veritabanı şifresini not al.
2. Projede **Connect** (veya *Project Settings → Database*) bölümünden **Transaction pooler** bağlantı adresini kopyala (port **6543**). Şuna benzer:
   `postgresql://postgres.<proje-ref>:<ŞİFRE>@aws-0-<bölge>.pooler.supabase.com:6543/postgres`
   Şifrede `@ : / ? # %` gibi özel karakterler varsa URL-encode et.
3. Migration'ları **yerel makineden** Supabase'e karşı çalıştır (Vercel'de migrate çalıştırılmaz):

   ```bash
   # PowerShell
   $env:DATABASE_URL="postgresql://..."; python manage.py migrate; python manage.py createsuperuser
   # macOS/Linux
   DATABASE_URL="postgresql://..." python manage.py migrate
   DATABASE_URL="postgresql://..." python manage.py createsuperuser
   ```

`settings.py`, `DATABASE_URL` tanımlıyken pooler için gereken ayarları otomatik uygular
(`CONN_MAX_AGE=0`, `DISABLE_SERVER_SIDE_CURSORS`, `sslmode=require`, hazır ifadeler kapalı).

4. **Güvenlik (RLS):** Supabase `public` şemasındaki tabloları REST API'ye açar. Uygulama bu API'yi kullanmadığı için tüm tablolarda Row Level Security **politikasız** etkinleştirilmiştir (anon/authenticated roller hiçbir satıra erişemez; Django `postgres` rolüyle bağlandığı için etkilenmez). Yeni bir migration tablo eklerse şunu çalıştır ve *Advisors → Security* ekranını kontrol et:

   ```sql
   ALTER TABLE public.<yeni_tablo> ENABLE ROW LEVEL SECURITY;
   ```

### 2. Vercel (uygulama)

Vercel, Django'yu otomatik algılar (`config/wsgi.py` içindeki `application`); ayrıca `builds`/`routes` yazmaya gerek yoktur. Python sürümü `.python-version` dosyasından okunur.

1. Kodu bir Git deposuna (GitHub vb.) gönder ve Vercel'de **Add New → Project** ile içe aktar. Framework olarak Django algılanmalı.
2. **Settings → Environment Variables** bölümüne ekle:

   | Değişken | Değer |
   |-|-|
   | `SECRET_KEY` | Uzun, rastgele bir anahtar (`python -c "import secrets; print(secrets.token_urlsafe(50))"`) |
   | `DEBUG` | `False` |
   | `DATABASE_URL` | Supabase transaction pooler adresi |
   | `ALLOWED_HOSTS` | `.vercel.app` (özel alan adı kullanırsan onu da ekle, virgülle) |
   | `CSRF_TRUSTED_ORIGINS` | `https://<proje>.vercel.app` |

3. Deploy et. Statik dosyalar WhiteNoise ile doğrudan `static/` klasöründen sunulur (`WHITENOISE_USE_FINDERS=True`), ayrıca `collectstatic` gerekmez.
4. Uçtan uca kontrol: kayıt ol → giriş yap → anket aç → oy ver. Veriler Supabase'de *Table Editor* içinde görünmelidir.

### Sorun giderme

- **`DisallowedHost` / 400:** `ALLOWED_HOSTS` içinde alan adı yok.
- **CSRF hatası (403):** `CSRF_TRUSTED_ORIGINS` şemalı (`https://`) ve tam alan adıyla yazılmalı.
- **`prepared statement ... does not exist`:** `DATABASE_URL` pooler (6543) adresi olmalı ve `settings.py`'deki `prepare_threshold=None` korunmalı.
