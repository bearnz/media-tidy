"""Read a video's frame height straight from the container header (mkv / mp4 / avi), stdlib only."""
import os, re, struct

HEAD, TAIL = 4 << 20, 16 << 20


def _chunks(path):
    size = os.path.getsize(path)
    with open(path, 'rb') as f:
        head = f.read(HEAD)
        if size <= HEAD:
            return [head]
        f.seek(max(HEAD, size - TAIL))
        return [head, f.read()]          # mp4 'moov' is often at the end


def _mkv(data):
    # PixelWidth (0xB0) followed shortly by PixelHeight (0xBA), each a 1-2 byte uint.
    for m in re.finditer(rb'\xb0([\x81\x82])', data):
        wl = m[1][0] - 0x80
        w = int.from_bytes(data[m.end():m.end() + wl], 'big')
        rest = data[m.end() + wl:m.end() + wl + 12]
        h = re.search(rb'\xba([\x81\x82])', rest)
        if h:
            hl = h[1][0] - 0x80
            hv = int.from_bytes(rest[h.end():h.end() + hl], 'big')
            if 100 < w < 8000 and 100 < hv < 5000:
                return hv
    return None


def _mp4(data):
    best = None
    for m in re.finditer(rb'tkhd', data):
        p = m.end()
        ver = data[p] if p < len(data) else 0
        off = p + 4 + (32 if ver == 1 else 20) + 8 + 8 + 36   # times/ids/duration, reserved, layer..volume, matrix
        if off + 8 <= len(data):
            w, h = struct.unpack('>II', data[off:off + 8])
            w, h = w >> 16, h >> 16
            if 100 < w < 8000 and 100 < h < 5000:
                best = max(best or 0, h)
    return best


def _avi(data):
    i = data.find(b'avih')
    if i >= 0 and i + 48 <= len(data):
        w, h = struct.unpack('<II', data[i + 8 + 32:i + 8 + 40])
        if 100 < w < 8000 and 100 < h < 5000:
            return h
    return None


def height(path):
    ext = os.path.splitext(path)[1].lower()
    fn = {'.mkv': _mkv, '.mp4': _mp4, '.m4v': _mp4, '.avi': _avi}.get(ext)
    if not fn:
        return None
    for chunk in _chunks(path):
        h = fn(chunk)
        if h:
            return h
    return None
