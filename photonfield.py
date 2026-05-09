"""
PhotonField :: Spektral Konstellasyon Kodlama Sistemi
=====================================================

Veriyi 2D Fourier uzayına yerleştirerek tek bir RGB görsel oluşturur.
Bilgi piksele değil, frekans bileşenlerinin fazına gömülüdür.

Anahtar fikirler:
  - Her bilgi parçası 2D bir frekansa karşılık gelir
  - Faz quantization (16 seviye = 4 bit/hücre)
  - Sabit genlik (linear scaling fazı korur)
  - Hermitian simetri (gerçek değerli IFFT)
  - Mid-frequency band (DC ve Nyquist'ten kaçın)
  - Reed-Solomon hata düzeltme (255-byte blok)
  - Gray code ile faz indeksi (komşu seviyeler 1 bit fark)
  - 3 renk kanalı (R/G/B) bağımsız veri taşır → 3× kapasite

Kapasite (N=1536, geniş band):
  ~810K hücre × 4 bit ÷ 8 = ~405 KB ham / kanal
  3 kanal × ~355 KB net / kanal (RS sonrası)
  Toplam: ~1.07 MB net / görsel

API:
  encode(data: bytes, filename: str, password: str | None = None) -> (PIL.Image RGB, info dict)
  decode(img: PIL.Image, password: str | None = None) -> dict

Şifreli mod (PHFE): iç gövde AES-256-GCM ile şifrelenir; anahtar scrypt ile türetilir.
Şifresiz görseller geriye dönük uyumludur (magic PHF3 ile başlar).
"""

from __future__ import annotations

import hashlib
import secrets
import struct
import time
import zlib
from dataclasses import dataclass

import numpy as np
from PIL import Image
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from reedsolo import RSCodec

# ─────────────────────────────────────────────
#  ŞİFRELEME (AES-256-GCM + scrypt)
# ─────────────────────────────────────────────

ENC_MAGIC = b'PHFE'  # şifreli iç paket imzası (plaintext PHF3 ile başlar)
GCM_AAD = b'PhotonField-GCM-v1'
SALT_LEN = 16
NONCE_LEN = 12
# Bellek-zorluğu bilinen parametreler (masaüstü için makul süre)
SCRYPT_N = 32768  # 2**15
SCRYPT_R = 8
SCRYPT_P = 1


def _derive_key(password: str, salt: bytes) -> bytes:
    pw = password.encode('utf-8')
    if len(pw) > 1024:
        raise ValueError('Şifre en fazla 1024 UTF-8 bayt olabilir')
    return hashlib.scrypt(pw, salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32, maxmem=128 * 1024 * 1024)


def _wrap_encrypted_payload(password: str, payload: bytes) -> bytes:
    salt = secrets.token_bytes(SALT_LEN)
    nonce = secrets.token_bytes(NONCE_LEN)
    key = _derive_key(password, salt)
    aes = AESGCM(key)
    ciphertext = aes.encrypt(nonce, payload, GCM_AAD)
    return ENC_MAGIC + salt + nonce + ciphertext


def _unwrap_encrypted_payload(password: str, blob: bytes) -> bytes:
    """blob = ENC_MAGIC + salt + nonce + ciphertext"""
    min_len = len(ENC_MAGIC) + SALT_LEN + NONCE_LEN + 16  # + minimum tag
    if len(blob) < min_len:
        raise ValueError('Şifreli paket çok kısa')
    salt = blob[len(ENC_MAGIC):len(ENC_MAGIC) + SALT_LEN]
    nonce = blob[len(ENC_MAGIC) + SALT_LEN:len(ENC_MAGIC) + SALT_LEN + NONCE_LEN]
    ct = blob[len(ENC_MAGIC) + SALT_LEN + NONCE_LEN:]
    key = _derive_key(password, salt)
    aes = AESGCM(key)
    return aes.decrypt(nonce, ct, GCM_AAD)

# ─────────────────────────────────────────────
#  KONFİGÜRASYON
# ─────────────────────────────────────────────

@dataclass(frozen=True)
class Config:
    # Standart görsel boyutları — encoder veri boyutuna göre en küçük uygun olanı seçer
    SIZES: tuple = (512, 768, 1024, 1280, 1600)
    N_MAX: int = 1600          # maksimum görsel boyutu

    PHASE_BITS: int = 4        # hücre başına bit
    INNER_RATIO: float = 0.0375  # iç halka (Nyquist'in %3.75'i)
    OUTER_RATIO: float = 0.90    # dış halka (Nyquist'in %90'ı, JPEG güvenli)

    RS_DATA: int = 223         # RS bloğu veri boyutu
    RS_PARITY: int = 32        # RS bloğu ECC boyutu (≈%14 düzeltme)
    CHANNELS: int = 3          # RGB
    MAGIC: bytes = b'PHF3'     # versiyon imzası

CFG = Config()
PHASE_LEVELS = 1 << CFG.PHASE_BITS
RS_BLOCK = CFG.RS_DATA + CFG.RS_PARITY  # 255
RSC = RSCodec(CFG.RS_PARITY)


def _radii_for(N: int) -> tuple[float, float]:
    """Verili N için iç/dış frekans halkası yarıçapları."""
    nyq = N / 2
    return CFG.INNER_RATIO * nyq, CFG.OUTER_RATIO * nyq


# ─────────────────────────────────────────────
#  GRAY CODE (komşu fazlar 1 bit fark)
# ─────────────────────────────────────────────

def _gray_encode(n: np.ndarray) -> np.ndarray:
    return n ^ (n >> 1)

def _gray_decode(g: np.ndarray) -> np.ndarray:
    n = g.copy()
    shift = 1
    while shift < CFG.PHASE_BITS:
        n = n ^ (n >> shift)
        shift <<= 1
    return n


# ─────────────────────────────────────────────
#  FREKANS HÜCRE KOORDİNATLARI
# ─────────────────────────────────────────────

_COORDS_CACHE: dict[int, list[tuple[int, int]]] = {}

def _build_coords(N: int) -> list[tuple[int, int]]:
    """Belirli bir N için Hermitian-bağımsız mid-band frekans hücreleri."""
    inner_r, outer_r = _radii_for(N)
    r_in_sq = inner_r ** 2
    r_out_sq = outer_r ** 2

    coords = []
    for ky in range(-N // 2 + 1, N // 2):
        for kx in range(-N // 2 + 1, N // 2):
            r2 = kx * kx + ky * ky
            if r2 < r_in_sq or r2 > r_out_sq:
                continue
            if ky > 0 or (ky == 0 and kx > 0):
                coords.append((kx, ky, r2))

    coords.sort(key=lambda c: (c[2], np.arctan2(c[1], c[0])))
    return [(kx, ky) for kx, ky, _ in coords]


def get_coords(N: int) -> list[tuple[int, int]]:
    if N not in _COORDS_CACHE:
        _COORDS_CACHE[N] = _build_coords(N)
    return _COORDS_CACHE[N]


def channel_rs_capacity_bytes(N: int) -> int:
    cells = len(get_coords(N))
    raw_bytes = (cells * CFG.PHASE_BITS) // 8
    rs_blocks = raw_bytes // RS_BLOCK
    return rs_blocks * RS_BLOCK


def channel_capacity_bytes(N: int) -> int:
    return (channel_rs_capacity_bytes(N) // RS_BLOCK) * CFG.RS_DATA


def capacity_bytes(N: int | None = None) -> int:
    """Verili N (veya N_MAX) için toplam (3 kanal) NET kapasite."""
    if N is None:
        N = CFG.N_MAX
    return channel_capacity_bytes(N) * CFG.CHANNELS


def _pick_size(framed_len: int) -> int:
    """Veriye yetecek en küçük standart N'i seç."""
    for N in CFG.SIZES:
        if framed_len <= capacity_bytes(N):
            return N
    return CFG.N_MAX  # max'a sığmıyorsa hata kapasite kontrolünden gelir


def _snap_size(actual: int) -> int:
    """Bir piksel boyutunu en yakın standart N'e yapıştır."""
    return min(CFG.SIZES, key=lambda n: abs(n - actual))


# ─────────────────────────────────────────────
#  BİT / BYTE YARDIMCILARI
# ─────────────────────────────────────────────

def _bytes_to_bits(data: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))

def _bits_to_bytes(bits: np.ndarray) -> bytes:
    pad = (-len(bits)) % 8
    if pad:
        bits = np.concatenate([bits, np.zeros(pad, dtype=np.uint8)])
    return np.packbits(bits).tobytes()


def _rs_encode(data: bytes) -> bytes:
    """Veriyi 223-bytelık bloklara bölüp her birine 32 bytelık ECC ekler."""
    out = bytearray()
    for i in range(0, len(data), CFG.RS_DATA):
        block = data[i:i + CFG.RS_DATA]
        if len(block) < CFG.RS_DATA:
            block = block + b'\x00' * (CFG.RS_DATA - len(block))
        out.extend(RSC.encode(block))
    return bytes(out)


def _rs_decode(data: bytes, original_len: int) -> bytes:
    out = bytearray()
    for i in range(0, len(data), RS_BLOCK):
        block = data[i:i + RS_BLOCK]
        if len(block) < RS_BLOCK:
            break
        decoded, _, _ = RSC.decode(bytes(block))
        out.extend(decoded)
        if len(out) >= original_len:
            break
    return bytes(out)[:original_len]


# ─────────────────────────────────────────────
#  TEK KANAL ENCODE / DECODE
# ─────────────────────────────────────────────

def _encode_channel(bits: np.ndarray, N: int, filler_seed: int) -> np.ndarray:
    """
    Bit dizisini tek bir gri tonlu (uint8) görsele kodlar.
    Veri olmayan hücreler rastgele faz ile doldurulur (görsel doku için).
    """
    coords = get_coords(N)
    cx = N // 2
    bin_size = 2 * np.pi / PHASE_LEVELS
    fixed_mag = 1.0

    # Bit'leri 4-lük faz indekslerine grupla
    pad = (-len(bits)) % CFG.PHASE_BITS
    if pad:
        bits = np.concatenate([bits, np.zeros(pad, dtype=np.uint8)])
    n_cells_used = len(bits) // CFG.PHASE_BITS
    chunks = bits.reshape(n_cells_used, CFG.PHASE_BITS)
    weights = (1 << np.arange(CFG.PHASE_BITS - 1, -1, -1)).astype(np.uint8)
    raw_indices = (chunks * weights).sum(axis=1).astype(np.int32)
    phase_indices = _gray_encode(raw_indices)

    # Spektrumu doldur
    spectrum = np.zeros((N, N), dtype=np.complex128)

    coords_arr = np.array(coords, dtype=np.int32)
    rows = cx + coords_arr[:, 1]
    cols = cx + coords_arr[:, 0]
    rows_conj = cx - coords_arr[:, 1]
    cols_conj = cx - coords_arr[:, 0]

    # Veri hücrelerinin fazları (bin merkezleri = idx * bin_size)
    data_phases = phase_indices * bin_size
    data_coefs = fixed_mag * np.exp(1j * data_phases)

    # Veri hücrelerini yerleştir
    spectrum[rows[:n_cells_used], cols[:n_cells_used]] = data_coefs
    spectrum[rows_conj[:n_cells_used], cols_conj[:n_cells_used]] = np.conj(data_coefs)

    # Boş hücreleri yarım-genlikli rastgele fazla doldur (görsel doku)
    n_unused = len(coords) - n_cells_used
    if n_unused > 0:
        rng = np.random.default_rng(seed=filler_seed)
        filler_phases = rng.uniform(0, 2 * np.pi, size=n_unused)
        filler_coefs = (fixed_mag * 0.5) * np.exp(1j * filler_phases)
        spectrum[rows[n_cells_used:], cols[n_cells_used:]] = filler_coefs
        spectrum[rows_conj[n_cells_used:], cols_conj[n_cells_used:]] = np.conj(filler_coefs)

    # Inverse FFT → gerçek değerli görüntü
    img = np.real(np.fft.ifft2(np.fft.ifftshift(spectrum)))

    # [0, 255] uint8'e normalize et (linear → faz korunur)
    img_min, img_max = img.min(), img.max()
    if img_max - img_min < 1e-10:
        return np.full((N, N), 128, dtype=np.uint8)
    img_norm = (img - img_min) / (img_max - img_min) * 255.0
    return np.clip(np.round(img_norm), 0, 255).astype(np.uint8)


def _decode_channel(arr: np.ndarray, N: int) -> np.ndarray:
    """Tek gri kanal → tüm hücrelerin bit dizisi."""
    coords = get_coords(N)
    cx = N // 2
    bin_size = 2 * np.pi / PHASE_LEVELS

    arr_f = arr.astype(np.float64)
    arr_f = arr_f - arr_f.mean()

    spectrum = np.fft.fftshift(np.fft.fft2(arr_f))

    coords_arr = np.array(coords, dtype=np.int32)
    rows = cx + coords_arr[:, 1]
    cols = cx + coords_arr[:, 0]
    coefs = spectrum[rows, cols]

    phases = np.angle(coefs) % (2 * np.pi)
    raw_idx = np.round(phases / bin_size).astype(np.int32) % PHASE_LEVELS
    phase_indices = _gray_decode(raw_idx)

    bits_per_cell = CFG.PHASE_BITS
    chunks = np.zeros((len(coords), bits_per_cell), dtype=np.uint8)
    for b in range(bits_per_cell):
        chunks[:, b] = (phase_indices >> (bits_per_cell - 1 - b)) & 1
    return chunks.flatten()


# ─────────────────────────────────────────────
#  PUBLIC API: ENCODE
# ─────────────────────────────────────────────

def encode(data: bytes, filename: str = "data.bin", password: str | None = None) -> tuple[Image.Image, dict]:
    """
    Veriyi tek bir RGB PhotonField sembolüne kodlar.
    password verilirse iç paket AES-256-GCM ile şifrelenir (scrypt anahtar türetimi).
    """
    t0 = time.time()

    # 1. Sıkıştır
    compressed = zlib.compress(data, level=9)

    # 2. Header
    fname_bytes = filename.encode('utf-8')[:255]
    checksum = hashlib.sha256(data).digest()[:8]
    header = struct.pack('>4sIIB',
                         CFG.MAGIC,
                         len(data),
                         len(compressed),
                         len(fname_bytes)) + fname_bytes + checksum
    payload = header + compressed

    # 3. İsteğe bağlı şifreleme → iç gövde
    if password is not None and password != '':
        try:
            inner = _wrap_encrypted_payload(password, payload)
        except ValueError as e:
            raise ValueError(str(e)) from e
        encrypted_flag = True
    else:
        inner = payload
        encrypted_flag = False

    # 4. Frame: uzunluk öneki + iç gövde (şifreli veya düz PHF3 payload)
    framed = struct.pack('>I', len(inner)) + inner
    N = _pick_size(len(framed))
    total_net = capacity_bytes(N)
    if len(framed) > total_net:
        max_cap = capacity_bytes(CFG.N_MAX)
        raise ValueError(
            f"Veri tek görsele sığmıyor.\n"
            f"  Maks ({CFG.N_MAX}×{CFG.N_MAX}): {max_cap//1024} KB (RS sonrası net)\n"
            f"  Bu dosya: {len(data)//1024} KB → sıkıştırılmış {len(compressed)//1024} KB → "
            f"framed {len(framed)//1024} KB"
        )

    # 6. RS encode
    rs_data = _rs_encode(framed)

    # 7. Sıralı kanal dolumu: kanal 0 dolar → 1 → 2
    per_channel_rs = channel_rs_capacity_bytes(N)
    chunks = []
    pos = 0
    for c in range(CFG.CHANNELS):
        end = min(pos + per_channel_rs, len(rs_data))
        chunks.append(rs_data[pos:end])
        pos = end

    # 8. Her kanalı kodla
    channel_imgs = []
    for c, chunk in enumerate(chunks):
        bits = _bytes_to_bits(chunk) if chunk else np.array([], dtype=np.uint8)
        channel_imgs.append(_encode_channel(bits, N=N, filler_seed=0xC0DE + c))

    # 9. RGB birleşim
    rgb_arr = np.stack(channel_imgs, axis=2)
    img = Image.fromarray(rgb_arr, mode='RGB')

    elapsed = time.time() - t0
    cells_per_channel = len(get_coords(N))
    cells_total = cells_per_channel * CFG.CHANNELS
    cells_used = sum((len(c) * 8 + CFG.PHASE_BITS - 1) // CFG.PHASE_BITS for c in chunks)
    channels_used = sum(1 for c in chunks if c)

    info = {
        'original_size': len(data),
        'compressed_size': len(compressed),
        'compression_ratio': f'{(1 - len(compressed)/max(len(data),1))*100:.1f}%',
        'rs_payload_size': len(rs_data),
        'cells_total': cells_total,
        'cells_used': cells_used,
        'used_pct': f'{cells_used/cells_total*100:.1f}%',
        'capacity_bytes': total_net,
        'channels_used': channels_used,
        'bits_per_cell': CFG.PHASE_BITS,
        'phase_levels': PHASE_LEVELS,
        'channels': CFG.CHANNELS,
        'N': N,
        'image_size': f'{N}×{N}',
        'encode_time': f'{elapsed:.2f}s',
        'filename': filename,
        'encrypted': encrypted_flag,
    }
    return img, info


# ─────────────────────────────────────────────
#  PUBLIC API: DECODE
# ─────────────────────────────────────────────

def decode(img: Image.Image, password: str | None = None) -> dict:
    """RGB PhotonField görselinden veriyi çözer. Şifreli paketler için doğru şifre gerekir."""
    t0 = time.time()
    pw = (password or '').strip()

    img = img.convert('RGB')
    # Görselin boyutundan N'i bul (en yakın standart boyuta yapıştır)
    actual_w = max(img.size)
    N = _snap_size(actual_w)
    if img.size != (N, N):
        img = img.resize((N, N), Image.LANCZOS)

    rgb = np.array(img)  # H × W × 3

    # 1. Kanal 0'dan başla (header burada)
    bits_0 = _decode_channel(rgb[:, :, 0], N)
    ch0_bytes = _bits_to_bytes(bits_0)

    if len(ch0_bytes) < RS_BLOCK:
        return {'success': False, 'error': 'Kanal 0\'da yetersiz veri'}

    try:
        first_decoded, _, _ = RSC.decode(ch0_bytes[:RS_BLOCK])
    except Exception as e:
        return {'success': False, 'error': f'RS hatası (ilk blok): {e}'}

    payload_len = struct.unpack('>I', bytes(first_decoded[:4]))[0]
    if payload_len <= 0 or payload_len > capacity_bytes(N):
        return {'success': False, 'error': f'Geçersiz payload uzunluğu: {payload_len}'}

    framed_total = 4 + payload_len
    rs_blocks_needed = (framed_total + CFG.RS_DATA - 1) // CFG.RS_DATA
    rs_bytes_needed = rs_blocks_needed * RS_BLOCK

    # 2. Sıralı kanal dolumu: önce kanal 0, dolarsa 1, dolarsa 2
    per_channel_rs = channel_rs_capacity_bytes(N)

    rs_combined = bytearray()
    rs_combined.extend(ch0_bytes[:min(per_channel_rs, rs_bytes_needed)])

    if rs_bytes_needed > per_channel_rs:
        bits_1 = _decode_channel(rgb[:, :, 1], N)
        ch1_bytes = _bits_to_bytes(bits_1)
        remaining = rs_bytes_needed - per_channel_rs
        rs_combined.extend(ch1_bytes[:min(per_channel_rs, remaining)])

    if rs_bytes_needed > 2 * per_channel_rs:
        bits_2 = _decode_channel(rgb[:, :, 2], N)
        ch2_bytes = _bits_to_bytes(bits_2)
        remaining = rs_bytes_needed - 2 * per_channel_rs
        rs_combined.extend(ch2_bytes[:min(per_channel_rs, remaining)])

    if len(rs_combined) < rs_bytes_needed:
        return {'success': False, 'error': 'Görselden yetersiz veri çıkarıldı'}

    # 3. RS decode
    try:
        framed = _rs_decode(bytes(rs_combined), framed_total)
    except Exception as e:
        return {'success': False, 'error': f'RS düzeltme başarısız: {e}'}

    payload = framed[4:]
    was_encrypted_at_rest = False

    # Şifreli iç paket (PHFE) — düz metin PHF3 magic ile başlar
    if payload.startswith(ENC_MAGIC):
        was_encrypted_at_rest = True
        if not pw:
            return {
                'success': False,
                'error': 'Bu görsel şifre ile korunuyor. Dosyayı çözmek için şifreyi girin; şifre olmadan içerik matematiksel olarak okunamaz.',
                'needs_password': True,
            }
        try:
            payload = _unwrap_encrypted_payload(pw, payload)
        except InvalidTag:
            return {
                'success': False,
                'error': 'Şifre yanlış veya görsel bozulmuş (kimlik doğrulama başarısız). Doğru şifreyi deneyin.',
                'wrong_password': True,
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Şifre çözümü başarısız: {e}',
            }
    elif pw:
        # Kullanıcı şifre yazdı ama görsel şifreli değil — şifreyi yok say
        pass

    # Header parse (payload = PHF3 header + zlib)
    if len(payload) < 13:
        return {'success': False, 'error': 'Payload çok kısa'}

    magic, orig_size, comp_size, fname_len = struct.unpack('>4sIIB', payload[:13])
    if magic != CFG.MAGIC:
        return {'success': False, 'error': f'Magic uyuşmazlık: {magic}'}

    fname_start = 13
    fname_end = fname_start + fname_len
    if fname_end + 8 > len(payload):
        return {'success': False, 'error': 'Header tamamlanmamış'}

    filename = payload[fname_start:fname_end].decode('utf-8', errors='replace')
    checksum_stored = payload[fname_end:fname_end + 8]

    payload_start = fname_end + 8
    if payload_start + comp_size > len(payload):
        return {'success': False, 'error': 'Sıkıştırılmış veri eksik'}

    compressed_data = payload[payload_start:payload_start + comp_size]

    # 6. Decompress
    try:
        original_data = zlib.decompress(compressed_data)
    except Exception as e:
        return {'success': False, 'error': f'Decompress hatası: {e}'}

    # 7. Checksum doğrula
    checksum_calc = hashlib.sha256(original_data).digest()[:8]
    valid = checksum_calc == checksum_stored

    elapsed = time.time() - t0
    return {
        'success': True,
        'data': original_data,
        'filename': filename,
        'original_size': orig_size,
        'compressed_size': comp_size,
        'valid_checksum': valid,
        'decode_time': f'{elapsed:.2f}s',
        'image_size': f'{N}×{N}',
        'was_encrypted': was_encrypted_at_rest,
    }


# ─────────────────────────────────────────────
#  ROUNDTRIP TESTİ
# ─────────────────────────────────────────────

if __name__ == '__main__':
    print(f"PhotonField config: RGB, {PHASE_LEVELS} faz seviyesi, "
          f"band {CFG.INNER_RATIO:.3f}-{CFG.OUTER_RATIO:.2f} of Nyquist")
    print(f"Standart boyutlar ve kapasiteler:")
    for n in CFG.SIZES:
        print(f"  N={n:>4}: {len(get_coords(n)):>7} hücre/kanal, "
              f"~{capacity_bytes(n)//1024:>4} KB net (RS sonrası)")
    print()

    rng = np.random.default_rng(42)
    test_cases = [
        ("Kısa metin", b"Merhaba dunya! " * 50),
        ("Yapısal binary", bytes(range(256)) * 100),
        ("Sıkışmaz rastgele", bytes(rng.integers(0, 256, size=200_000, dtype=np.uint8))),
        ("Sıkışmaz rastgele (büyük)", bytes(rng.integers(0, 256, size=600_000, dtype=np.uint8))),
        ("Sıkıştırılabilir metin", b"Lorem ipsum dolor sit amet. " * 50_000),
    ]

    for name, data in test_cases:
        print(f"--- {name}: {len(data)} byte ---")
        try:
            img, info = encode(data, "test.bin")
        except ValueError as e:
            print(f"  SIĞMIYOR: {e}")
            print()
            continue
        print(f"  Sıkıştırma: {info['compression_ratio']}, hücre kullanımı: {info['used_pct']}")
        print(f"  Encode: {info['encode_time']}")

        png_path = f"_test.png"
        img.save(png_path, format='PNG')

        img2 = Image.open(png_path)
        result = decode(img2)
        if result['success']:
            match = result['data'] == data
            print(f"  Decode: {result['decode_time']}, checksum={result['valid_checksum']}, "
                  f"byte-eşleşme={match}")
        else:
            print(f"  FAILED: {result['error']}")
        print()

    import os
    if os.path.exists('_test.png'):
        os.remove('_test.png')
