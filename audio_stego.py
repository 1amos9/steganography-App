import os
import wave
import numpy as np

END_MARKER = "1111111111111110"
FILE_MAGIC = b"CSF1"


def _read_wav(path):
    """Read a WAV into a NumPy int16 array plus its parameters."""
    with wave.open(path, "rb") as w:
        params = w.getparams()
        frames = w.readframes(w.getnframes())
    if params.sampwidth != 2:
        raise ValueError("Use a 16 bit WAV file.")
    samples = np.frombuffer(frames, dtype=np.int16).copy()
    return samples, params


def _write_wav(path, samples, params):
    """Write a NumPy int16 array back to a WAV with the same parameters."""
    with wave.open(path, "wb") as w:
        w.setparams(params)
        w.writeframes(samples.astype(np.int16).tobytes())


def capacity_bytes(path):
    """How many payload bytes a WAV holds. One bit per sample."""
    samples, _ = _read_wav(path)
    return max((len(samples) - len(END_MARKER)) // 8, 0)


def _embed(samples, binary_payload):
    """Write payload bits into the LSB of each sample, in order."""
    if len(binary_payload) > len(samples):
        raise ValueError(
            f"Payload too large. Need {len(binary_payload)} bits, "
            f"audio holds {len(samples)} bits.")
    out = samples.copy()
    for i in range(len(binary_payload)):
        # work on the unsigned view of the 16 bit value, set the low bit
        value = int(out[i]) & 0xFFFF
        value = (value & 0xFFFE) | int(binary_payload[i])
        # bring it back into signed int16 range
        out[i] = np.int16(value - 0x10000 if value >= 0x8000 else value)
    return out


def hide_text_in_wav(in_path, text, out_path):
    """Hide a text string in a WAV file."""
    samples, params = _read_wav(in_path)
    binary = "".join(format(ord(c), "08b") for c in text) + END_MARKER
    stego = _embed(samples, binary)
    _write_wav(out_path, stego, params)
    return out_path


def hide_file_in_wav(in_path, file_path, out_path):
    """Hide a whole file in a WAV file, with a name and size header."""
    samples, params = _read_wav(in_path)
    with open(file_path, "rb") as f:
        data = f.read()
    name = os.path.basename(file_path).encode("utf-8")
    header = FILE_MAGIC + len(name).to_bytes(2, "big") + name + len(data).to_bytes(8, "big")
    payload = header + data
    binary = "".join(format(b, "08b") for b in payload) + END_MARKER
    stego = _embed(samples, binary)
    _write_wav(out_path, stego, params)
    return out_path


def _read_lsb(samples):
    """Read the LSB of every sample into one binary string."""
    return "".join(str(int(s) & 1) for s in samples)


def extract_text_from_wav(path):
    """Read hidden text out of a WAV. Stops at the end marker."""
    samples, _ = _read_wav(path)
    bits = _read_lsb(samples)
    end = bits.find(END_MARKER)
    if end == -1:
        return None
    bits = bits[:end]
    text = ""
    for i in range(0, len(bits), 8):
        byte = bits[i:i + 8]
        if len(byte) == 8:
            text += chr(int(byte, 2))
    return text


def extract_file_from_wav(path):
    """Read a hidden file out of a WAV. Returns (name, data) or None."""
    samples, _ = _read_wav(path)
    bits = _read_lsb(samples)
    end = bits.find(END_MARKER)
    if end == -1:
        return None
    bits = bits[:end]
    raw = bytearray()
    for i in range(0, len(bits), 8):
        byte = bits[i:i + 8]
        if len(byte) == 8:
            raw.append(int(byte, 2))
    raw = bytes(raw)
    if not raw.startswith(FILE_MAGIC):
        return None
    pos = len(FILE_MAGIC)
    name_len = int.from_bytes(raw[pos:pos + 2], "big"); pos += 2
    name = raw[pos:pos + name_len].decode("utf-8", errors="replace"); pos += name_len
    data_len = int.from_bytes(raw[pos:pos + 8], "big"); pos += 8
    return name, raw[pos:pos + data_len]
