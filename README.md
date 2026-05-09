# PhotonField

**Experimental spectral file-in-image encoder.** Embeds arbitrary bytes into a single **RGB PNG** by coding data in the **phase** of mid-band FFT bins (not in pixels like QR). Includes zlib compression, Reed–Solomon ECC, optional **AES-256-GCM** encryption (key derived with **scrypt**).

> Bu depo deneysel bir projedir; QR/endüstri standardı barkodların yerine geçmez. Üretimde hassas veri için kanıtlanmış araçları tercih edin.

---

## Ne işe yarar?

- Küçük veya orta boy dosyayı tek bir **PhotonField PNG** içinde taşımak (paylaşım, arşiv, puzzle/CTF tarzı kullanımlar).
- **Şifresiz** (`PHF3` iç gövde) veya **şifreli** (`PHFE`: AES-GCM + scrypt) mod.

## Ne işe yaramaz / sınırlar

- Telefon kamerasıyla “QR okut” akışı için tasarlanmadı.
- **JPEG**, yeniden boyutlandırma veya kayıplı işlemler özellikle **yüksek dolulukta** veriyi bozabilir — mümkünse **PNG** kullanın.
- Görsel dosya boyutu çoğu zaman ham veriden **büyük veya yakın** kalabilir.
- Şifre **zayıfsa** offline deneme saldırıları teorik olarak mümkündür; uzun, tahmin edilemez parolalar kullanın.

---

## Kurulum

Python **3.10+** önerilir.

```bash
git clone https://github.com/sergenpoyraz/photonfield.git
cd PhotonField
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Web arayüzü (Flask)

```bash
python app.py
```

Tarayıcı: **http://127.0.0.1:5000**

- **Dosya → PhotonField:** dosya seç, isteğe bağlı şifre, PNG üret.
- **PhotonField → Dosya:** PNG yükle, şifreliyse şifre gir, dosyayı geri al.

---

## Python API

```python
import io
import photonfield as pf
from PIL import Image

data = b"hello"
img, info = pf.encode(data, "hello.txt", password=None)  # veya password="güçlü-parola"

buf = io.BytesIO()
img.save(buf, format="PNG")
buf.seek(0)
result = pf.decode(Image.open(buf), password=None)

assert result["success"]
assert result["data"] == data
```

Şifreli görsellerde `decode` şifre olmadan `needs_password`, yanlış şifrede `wrong_password` dönebilir.

---

## Teknik özet

| Bileşen | Açıklama |
|--------|-----------|
| Taşıyıcı | 2D FFT fazı, 16 seviye (Gray kodlu), 3 RGB kanalı |
| Paket | `PHF3` başlık + zlib + SHA-256 checksum (8 bayt) |
| ECC | Reed–Solomon 255 bayt blok (223 veri + 32 parity) |
| Şifre | `PHFE`: salt + nonce + AES-GCM; anahtar scrypt (`n=32768, r=8, p=1`) |
| Boyut | Adaptif kare: 512 … 1600 px (veriye göre en küçük uygun) |

---

## Lisans

MIT — bakınız [LICENSE](LICENSE).

---

## English (short)

PhotonField encodes files into **RGB PNG** images via **FFT phase** coding, with zlib, Reed–Solomon, and optional **AES-256-GCM** (scrypt KDF). Not a QR replacement; use **lossless PNG** for reliability.
