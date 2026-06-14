import os
import io
import json
import base64
import zipfile
import secrets
import string
import shutil

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# tuning for the key derivation
PBKDF2_ITERATIONS = 200_000
SALT_LEN = 16
NONCE_LEN = 12
KEY_LEN = 32  # 256 bit key for AES-256

TEXT_TAG = "QC1:"          # marks an encrypted text blob
FILE_MAGIC = b"QCFILE01"   # marks an encrypted file


def _derive_key(password, salt):
    """Turn a password and salt into a 32 byte key."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


# -------------------------------------------------------------------
# TEXT
# -------------------------------------------------------------------
def encrypt_text(plain_text, password):
    """Encrypt a string. Returns a base64 token with the QC1 tag."""
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = _derive_key(password, salt)
    cipher = AESGCM(key)
    blob = cipher.encrypt(nonce, plain_text.encode("utf-8"), None)
    raw = salt + nonce + blob
    return TEXT_TAG + base64.b64encode(raw).decode("ascii")


def decrypt_text(token, password):
    """Decrypt a QC1 text token. Raises ValueError on bad input or wrong password."""
    if token.startswith(TEXT_TAG):
        token = token[len(TEXT_TAG):]
    try:
        raw = base64.b64decode(token.strip())
        salt = raw[:SALT_LEN]
        nonce = raw[SALT_LEN:SALT_LEN + NONCE_LEN]
        blob = raw[SALT_LEN + NONCE_LEN:]
        key = _derive_key(password, salt)
        cipher = AESGCM(key)
        plain = cipher.decrypt(nonce, blob, None)
    except Exception:
        raise ValueError("This text is not valid encrypted data, or the password is wrong.")
    return plain.decode("utf-8")


# -------------------------------------------------------------------
# FILES
# -------------------------------------------------------------------
def encrypt_file(in_path, password, out_path=None):
    """Encrypt a file to a .qcf file. Returns the output path."""
    if out_path is None:
        out_path = in_path + ".qcf"
    with open(in_path, "rb") as f:
        data = f.read()

    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = _derive_key(password, salt)
    cipher = AESGCM(key)
    blob = cipher.encrypt(nonce, data, None)

    with open(out_path, "wb") as f:
        f.write(FILE_MAGIC + salt + nonce + blob)
    return out_path


def decrypt_file(in_path, password, out_path=None):
    """Decrypt a .qcf file. Returns the output path."""
    with open(in_path, "rb") as f:
        raw = f.read()

    if not raw.startswith(FILE_MAGIC):
        raise ValueError("Not a QuickCrypto file.")

    pos = len(FILE_MAGIC)
    salt = raw[pos:pos + SALT_LEN]
    pos += SALT_LEN
    nonce = raw[pos:pos + NONCE_LEN]
    pos += NONCE_LEN
    blob = raw[pos:]

    key = _derive_key(password, salt)
    cipher = AESGCM(key)
    try:
        data = cipher.decrypt(nonce, blob, None)
    except Exception:
        raise ValueError("Wrong password or damaged file.")

    if out_path is None:
        if in_path.endswith(".qcf"):
            out_path = in_path[:-4]
        else:
            out_path = in_path + ".dec"
    with open(out_path, "wb") as f:
        f.write(data)
    return out_path


# -------------------------------------------------------------------
# FOLDERS  (zip the folder, then encrypt the zip)
# -------------------------------------------------------------------
def encrypt_folder(folder_path, password, out_path=None):
    """Zip a folder in memory, then encrypt it to a .qcf file."""
    if out_path is None:
        out_path = folder_path.rstrip("/\\") + ".qcf"

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(folder_path):
            for name in files:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, folder_path)
                zf.write(full, rel)
    data = buffer.getvalue()

    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = _derive_key(password, salt)
    cipher = AESGCM(key)
    blob = cipher.encrypt(nonce, data, None)

    with open(out_path, "wb") as f:
        f.write(FILE_MAGIC + salt + nonce + blob)
    return out_path


def decrypt_folder(in_path, password, out_dir=None):
    """Decrypt a .qcf folder archive and unzip it. Returns the output folder."""
    with open(in_path, "rb") as f:
        raw = f.read()
    if not raw.startswith(FILE_MAGIC):
        raise ValueError("Not a QuickCrypto file.")

    pos = len(FILE_MAGIC)
    salt = raw[pos:pos + SALT_LEN]
    pos += SALT_LEN
    nonce = raw[pos:pos + NONCE_LEN]
    pos += NONCE_LEN
    blob = raw[pos:]

    key = _derive_key(password, salt)
    cipher = AESGCM(key)
    try:
        data = cipher.decrypt(nonce, blob, None)
    except Exception:
        raise ValueError("Wrong password or damaged file.")

    if out_dir is None:
        out_dir = in_path
        if out_dir.endswith(".qcf"):
            out_dir = out_dir[:-4]
        out_dir = out_dir + "_decrypted"
    os.makedirs(out_dir, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
        zf.extractall(out_dir)
    return out_dir


# -------------------------------------------------------------------
# SECURE SHRED  (overwrite then delete)
# -------------------------------------------------------------------
def shred_file(path, passes=3):
    """Overwrite a file with random bytes, then delete it. Cannot be undone."""
    if not os.path.isfile(path):
        raise ValueError("Not a file.")
    length = os.path.getsize(path)
    with open(path, "r+b") as f:
        for _ in range(passes):
            f.seek(0)
            f.write(os.urandom(length))
            f.flush()
            os.fsync(f.fileno())
        f.seek(0)
        f.write(b"\x00" * length)
        f.flush()
        os.fsync(f.fileno())
    os.remove(path)
    return True


def shred_folder(folder_path, passes=3):
    """Shred every file in a folder, then remove the folder. Cannot be undone."""
    count = 0
    for root, _dirs, files in os.walk(folder_path):
        for name in files:
            shred_file(os.path.join(root, name), passes)
            count += 1
    shutil.rmtree(folder_path, ignore_errors=True)
    return count


# -------------------------------------------------------------------
# PASSWORD TOOLS
# -------------------------------------------------------------------
def generate_password(length=16, use_upper=True, use_digits=True, use_symbols=True):
    """Make a strong random password using the secrets module."""
    pool = string.ascii_lowercase
    if use_upper:
        pool += string.ascii_uppercase
    if use_digits:
        pool += string.digits
    if use_symbols:
        pool += "!@#$%^&*()-_=+[]{}"
    if length < 4:
        length = 4
    return "".join(secrets.choice(pool) for _ in range(length))


def test_password_strength(password):
    """Score a password from 0 to 100 and return a label and notes."""
    score = 0
    notes = []
    length = len(password)

    if length >= 12:
        score += 35
    elif length >= 8:
        score += 20
        notes.append("Use 12 or more characters.")
    else:
        notes.append("Too short. Use at least 12 characters.")

    classes = 0
    if any(c.islower() for c in password):
        classes += 1
    if any(c.isupper() for c in password):
        classes += 1
    if any(c.isdigit() for c in password):
        classes += 1
    if any(not c.isalnum() for c in password):
        classes += 1
    score += classes * 15

    if classes < 3:
        notes.append("Mix upper, lower, digits, and symbols.")
    if len(set(password)) < length * 0.6:
        notes.append("Avoid repeated characters.")
        score -= 5

    score = max(0, min(100, score))
    if score >= 80:
        label = "Strong"
    elif score >= 50:
        label = "Medium"
    else:
        label = "Weak"
    return score, label, notes


# -------------------------------------------------------------------
# SELF DECRYPTING MESSAGE  (HTML file, opens in any browser)
# -------------------------------------------------------------------
def create_self_decrypting_html(message, password, out_path):
    """
    Build an HTML file holding an encrypted message."""
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = _derive_key(password, salt)
    cipher = AESGCM(key)
    blob = cipher.encrypt(nonce, message.encode("utf-8"), None)

    b64_salt = base64.b64encode(salt).decode("ascii")
    b64_nonce = base64.b64encode(nonce).decode("ascii")
    b64_blob = base64.b64encode(blob).decode("ascii")

    html = """<!doctype html>
<html><head><meta charset="utf-8"><title>Self Decrypting Message</title>
<style>
body{background:#000;color:#f2c200;font-family:Arial,sans-serif;text-align:center;padding:40px}
input,button{font-size:16px;padding:8px;margin:6px}
button{background:#f2c200;color:#000;border:0;font-weight:bold;cursor:pointer}
#out{white-space:pre-wrap;text-align:left;max-width:640px;margin:20px auto;
border:1px solid #d8a500;padding:14px;min-height:40px}
</style></head><body>
<h2>Self Decrypting Message</h2>
<p>Type the password to read the hidden message.</p>
<input id="pw" type="password" placeholder="password">
<button onclick="go()">Decrypt</button>
<div id="out"></div>
<script>
const SALT="__SALT__", NONCE="__NONCE__", BLOB="__BLOB__", ITER=__ITER__;
function b64(s){return Uint8Array.from(atob(s),c=>c.charCodeAt(0));}
async function go(){
  const pw=document.getElementById('pw').value;
  const out=document.getElementById('out');
  try{
    const enc=new TextEncoder();
    const baseKey=await crypto.subtle.importKey('raw',enc.encode(pw),'PBKDF2',false,['deriveKey']);
    const key=await crypto.subtle.deriveKey(
      {name:'PBKDF2',salt:b64(SALT),iterations:ITER,hash:'SHA-256'},
      baseKey,{name:'AES-GCM',length:256},false,['decrypt']);
    const plain=await crypto.subtle.decrypt({name:'AES-GCM',iv:b64(NONCE)},key,b64(BLOB));
    out.textContent=new TextDecoder().decode(plain);
  }catch(e){ out.textContent="Wrong password or damaged data."; }
}
</script></body></html>"""

    html = html.replace("__SALT__", b64_salt)
    html = html.replace("__NONCE__", b64_nonce)
    html = html.replace("__BLOB__", b64_blob)
    html = html.replace("__ITER__", str(PBKDF2_ITERATIONS))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
