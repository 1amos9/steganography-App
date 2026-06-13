"""
Stego engine.
LSB image steganography. Logic follows the Day 3 class slides:
- text to binary, one byte per char, 08b
- end marker 1111111111111110
- hide in least significant bit of each flattened pixel value
- extract by reading LSBs until the end marker
This module has no GUI. The interface imports these functions.
"""

import os
import numpy as np
from PIL import Image

# 16 bit end marker from the slides. Marks where the payload stops.
END_MARKER = "1111111111111110"

# Header used for file payloads so extraction knows the name and size.
# Format inside the hidden bytes:
#   [4 bytes magic 'CSF1'][2 bytes name length][name][8 bytes data length][data]
FILE_MAGIC = b"CSF1"


def load_image(path):
    """Open an image and return it as a NumPy array. Forces a lossless RGB form."""
    image = Image.open(path)
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")
    return np.array(image)


def capacity_bits(cover_array):
    """How many payload bits this image holds. One bit per pixel value."""
    return int(cover_array.size)


def capacity_bytes(cover_array):
    """Usable payload bytes, leaving room for the end marker."""
    total_bits = capacity_bits(cover_array)
    usable = (total_bits - len(END_MARKER)) // 8
    return max(usable, 0)


def text_to_binary(text):
    """Turn a string into a binary string, 8 bits per character, then add the end marker."""
    binary = "".join(format(ord(char), "08b") for char in text)
    binary += END_MARKER
    return binary


def bytes_to_binary(data_bytes):
    """Turn raw bytes into a binary string, then add the end marker."""
    binary = "".join(format(byte, "08b") for byte in data_bytes)
    binary += END_MARKER
    return binary


def _embed_binary(cover_array, binary_payload):
    """Write each bit of binary_payload into the LSB of each pixel value, in order."""
    stego_array = cover_array.copy()
    flat = stego_array.flatten()

    if len(binary_payload) > len(flat):
        raise ValueError(
            "Payload too large for image. "
            f"Need {len(binary_payload)} bits, image holds {len(flat)} bits."
        )

    for i in range(len(binary_payload)):
        # clear the last bit with & 254, then set it to the payload bit
        flat[i] = (flat[i] & 254) | int(binary_payload[i])

    stego_array = flat.reshape(stego_array.shape)
    return stego_array


def hide_text(cover_array, text):
    """Hide a text string in the cover. Returns the stego array."""
    binary_payload = text_to_binary(text)
    return _embed_binary(cover_array, binary_payload)


def hide_file(cover_array, file_path):
    """Hide a whole file in the cover. Stores the file name and size in a small header."""
    with open(file_path, "rb") as f:
        data = f.read()

    name = os.path.basename(file_path).encode("utf-8")
    if len(name) > 65535:
        raise ValueError("File name too long.")

    header = FILE_MAGIC
    header += len(name).to_bytes(2, "big")
    header += name
    header += len(data).to_bytes(8, "big")

    payload = header + data
    binary_payload = bytes_to_binary(payload)
    return _embed_binary(cover_array, binary_payload)


def _read_lsb_bits(stego_array):
    """Read the LSB of every pixel value into one long binary string."""
    flat = stego_array.flatten()
    return "".join(str(int(value) & 1) for value in flat)


def extract_text(stego_array):
    """Read hidden text out of a stego image. Stops at the end marker."""
    binary_data = _read_lsb_bits(stego_array)
    end_index = binary_data.find(END_MARKER)
    if end_index == -1:
        return None

    binary_data = binary_data[:end_index]
    text = ""
    for i in range(0, len(binary_data), 8):
        byte = binary_data[i:i + 8]
        if len(byte) == 8:
            text += chr(int(byte, 2))
    return text


def extract_file(stego_array):
    """
    Read a hidden file out of a stego image.
    Returns a tuple (filename, data_bytes) or None if no file header is found.
    """
    binary_data = _read_lsb_bits(stego_array)
    end_index = binary_data.find(END_MARKER)
    if end_index == -1:
        return None

    binary_data = binary_data[:end_index]
    raw = bytearray()
    for i in range(0, len(binary_data), 8):
        byte = binary_data[i:i + 8]
        if len(byte) == 8:
            raw.append(int(byte, 2))
    raw = bytes(raw)

    if not raw.startswith(FILE_MAGIC):
        return None

    pos = len(FILE_MAGIC)
    name_len = int.from_bytes(raw[pos:pos + 2], "big")
    pos += 2
    name = raw[pos:pos + name_len].decode("utf-8", errors="replace")
    pos += name_len
    data_len = int.from_bytes(raw[pos:pos + 8], "big")
    pos += 8
    data = raw[pos:pos + data_len]
    return name, data


def changed_pixel_count(cover_array, stego_array):
    """Count how many pixel values differ between cover and stego. Slide 35 logic."""
    difference = stego_array.astype(int) - cover_array.astype(int)
    return int(np.count_nonzero(difference))


def first_modified_pixels(cover_array, stego_array, count=20):
    """Return a list of (index, original, stego) for the first changed values. Slide 33."""
    cover_flat = cover_array.flatten()
    stego_flat = stego_array.flatten()
    rows = []
    for i in range(min(count, len(cover_flat))):
        rows.append((i, int(cover_flat[i]), int(stego_flat[i])))
    return rows


def binary_compare(cover_array, stego_array, count=30):
    """Return binary before and after for the first values. Slide 36 logic."""
    cover_flat = cover_array.flatten()
    stego_flat = stego_array.flatten()
    rows = []
    for i in range(min(count, len(cover_flat))):
        rows.append((i, format(int(cover_flat[i]), "08b"), format(int(stego_flat[i]), "08b")))
    return rows


def save_image(array, path):
    """Save a NumPy array as a lossless PNG so the LSBs survive."""
    Image.fromarray(array.astype("uint8")).save(path)


def hide_bytes(cover_array, data_bytes):
    """Hide raw bytes in the cover. Used for encrypted payloads. Returns stego array."""
    binary_payload = bytes_to_binary(data_bytes)
    return _embed_binary(cover_array, binary_payload)


def extract_raw_bytes(stego_array):
    """Read raw bytes back out, stopping at the end marker. Returns bytes or None."""
    binary_data = _read_lsb_bits(stego_array)
    end_index = binary_data.find(END_MARKER)
    if end_index == -1:
        return None
    binary_data = binary_data[:end_index]
    raw = bytearray()
    for i in range(0, len(binary_data), 8):
        byte = binary_data[i:i + 8]
        if len(byte) == 8:
            raw.append(int(byte, 2))
    return bytes(raw)


def difference_map(cover_array, stego_array, amplify=True, grow=2):
    """
    Build an image that marks where the stego differs from the cover.
    Changed pixels show bright, unchanged pixels stay dark.
    grow widens each changed spot by that many pixels in every direction so
    sparse changes stay visible after the image is scaled down for display.
    """
    diff = (cover_array.astype(int) != stego_array.astype(int))
    if diff.ndim == 3:
        diff = diff.any(axis=2)

    # widen each changed spot so single-pixel changes do not vanish when scaled
    if grow > 0:
        widened = diff.copy()
        rows, cols = diff.shape
        ys, xs = np.where(diff)
        for dy in range(-grow, grow + 1):
            for dx in range(-grow, grow + 1):
                ny = np.clip(ys + dy, 0, rows - 1)
                nx = np.clip(xs + dx, 0, cols - 1)
                widened[ny, nx] = True
        diff = widened

    out = np.zeros(cover_array.shape[:2] + (3,), dtype="uint8")
    if amplify:
        # changed spots in bright yellow, the app theme colour
        out[diff] = (242, 194, 0)
    else:
        out[diff] = (255, 255, 255)
    return out


def difference_bars(cover_array, stego_array, width=300, height=120):
    """
    Build a fixed-size view where each changed column shows as a bright vertical
    bar on black. Works for any image shape, including very wide, short images,
    because it does not depend on the image height to stay visible.
    """
    diff = (cover_array.astype(int) != stego_array.astype(int))
    if diff.ndim == 3:
        diff = diff.any(axis=2)
    rows, cols = diff.shape
    # which columns hold any changed pixel
    col_has_change = diff.any(axis=0)

    out = np.zeros((height, width, 3), dtype="uint8")
    for x in range(width):
        src_col = int(x * cols / width)
        if src_col < cols and col_has_change[src_col]:
            out[:, x] = (242, 194, 0)
    return out


def self_test():
    """
    Hide a known string in a fresh image, extract it, and check it matches.
    Returns (passed, detail). No files touched.
    """
    arr = (np.random.rand(64, 64, 3) * 255).astype("uint8")
    secret = "QuickCrypto self test 12345"
    stego = hide_text(arr, secret)
    out = extract_text(stego)
    passed = (out == secret)
    changed = changed_pixel_count(arr, stego)
    detail = f"hid {len(secret)} chars, {changed} pixels changed, extract {'matched' if passed else 'failed'}"
    return passed, detail
