"""Convert a 2 Ship 2 Harkinian HD texture pack (.o2r) into hd_textures.bin for the console.

Each replacement in the pack is named after the decomp asset it replaces. The asset XMLs say where
that texture is in the ROM and how it's encoded; the original is decoded exactly as the renderer's
TMEM decoder would (src/gfx/tmem.cpp) and hashed (gfx::hd_texture_hash), so the renderer can
recognize it when the game draws it. The game doesn't always decode a texture the way the XML
describes it, so each one is also hashed the other ways it may be decoded (decode_variants). The
HD image is scaled down to at most kMaxScale times the original (at 720p an N64 pixel is 3 screen
pixels, so the HUD drawn at its usual size gets one texel per pixel; more resolution only costs the
console memory).

usage: python -I tools/build_hd_pack.py <pack.o2r> <ROM .z64> <out hd_textures.bin> [--decomp DIR]

The ROM is the NTSC-U 1.0 ROM, as dumped or decompressed (tools/decompress_mm.py). The asset
definitions come from the Majora's Mask decomp (zeldaret/mm, at Zelda64Recomp's lib/mm-decomp
commit); --decomp names a checkout of it, by default Zelda64Recomp's submodule.

Output, big-endian: "MMHD", version 2, count, then count entries sorted by hash (u64 hash, u16
width and height as decoded, u16 HD width and height, u32 offset of the HD image, u16 rows of the
decoded texture the image covers, u16 0), then the images' texels as u32 0xAARRGGBB. Entries for
one texture share its image; rows past those it covers come from the decoded texture.
"""
import ast
import collections
import glob
import os
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decompress_mm import decompress, yaz0_decompress, FILE_TABLE_OFFSET, UNCOMPRESSED_SIZE  # noqa: E402

from PIL import Image

DECOMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'external', 'Zelda64Recomp', 'lib', 'mm-decomp')
kMaxScale = 3
kResourceHeader = 0x40
kExtraRows = 4
kAliases = {'i8': ('ia8',), 'ia8': ('i8',), 'i4': ('ia4',), 'ia4': ('i4',), 'rgba16': ('ia16',), 'ia16': ('rgba16',)}

# --- The ROM's files -----------------------------------------------------------------------------

def rom_files(rom):
    names = ast.literal_eval(open(os.path.join(DECOMP, 'tools', 'disasm', 'dma_filenames.txt')).read())
    files = {}
    for i, name in enumerate(names):
        vstart, vend = struct.unpack_from('>II', rom, FILE_TABLE_OFFSET + i * 16)
        if vend > vstart:
            files[name] = rom[vstart:vend]
    return files


def unarchive(data):
    """A yar archive's entries, each Yaz0-compressed, decompressed back to back (decompress_yars.py)."""
    first = struct.unpack_from('>I', data, 0)[0]
    if first == 0:
        return b''
    spans = [(first, first + struct.unpack_from('>I', data, 4)[0])]
    off = 4
    while off < first - 4:
        a, b = struct.unpack_from('>II', data, off)
        spans.append((a + first, b + first))
        off += 4
    return b''.join(yaz0_decompress(data[s:e]) for s, e in spans)


def file_bytes(files, name, cache={}):
    if name not in cache:
        if name.endswith('.unarchive'):
            base = files.get(name[:-len('.unarchive')])
            cache[name] = unarchive(base) if base is not None else None
        else:
            cache[name] = files.get(name)
    return cache[name]

# --- Asset definitions ---------------------------------------------------------------------------

def texture_defs():
    by_name = collections.defaultdict(list)
    for path in glob.glob(os.path.join(DECOMP, 'assets', 'xml', '**', '*.xml'), recursive=True):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for f in root.iter('File'):
            for t in f.iter('Texture'):
                d = dict(t.attrib)
                d['file'] = f.get('Name')
                by_name[d['Name']].append(d)
    return by_name


def pick_def(defs, pack_path):
    """The definition a pack entry replaces, by name, preferring the file its path names."""
    parts = pack_path.split('/')
    hits = defs.get(parts[-1], [])
    folders = parts[1:-1]
    for d in hits:
        if any(d['file'] == f or d['file'].startswith(f + '.') for f in folders):
            return d
    return hits[0] if len(hits) == 1 else None

# --- Decoding, as Tmem::decode_tile ----------------------------------------------------------------

def argb(a, r, g, b):
    return (a << 24) | (r << 16) | (g << 8) | b


def expand5(v):
    return (v << 3) | (v >> 2)


def rgba16(c):
    return argb(0xFF if c & 1 else 0, expand5((c >> 11) & 0x1F), expand5((c >> 6) & 0x1F), expand5((c >> 1) & 0x1F))


def decode(fmt, w, h, data, tlut):
    out = []
    if fmt == 'rgba32':
        for i in range(w * h):
            r, g, b, a = data[i * 4:i * 4 + 4]
            out.append(argb(a, r, g, b))
    elif fmt in ('rgba16', 'ia16'):
        for i in range(w * h):
            c = (data[i * 2] << 8) | data[i * 2 + 1]
            out.append(rgba16(c) if fmt == 'rgba16' else argb(c & 0xFF, c >> 8, c >> 8, c >> 8))
    else:
        bits = 8 if fmt.endswith('8') else 4
        row = (w * bits + 7) // 8
        for t in range(h):
            for s in range(w):
                if bits == 8:
                    v = data[t * row + s]
                else:
                    b = data[t * row + s // 2]
                    v = (b & 0xF) if s & 1 else (b >> 4)
                if fmt.startswith('ci'):
                    out.append(rgba16((tlut[v * 2] << 8) | tlut[v * 2 + 1]))
                elif fmt.startswith('ia'):
                    if bits == 8:
                        i, a = (v >> 4) * 0x11, (v & 0xF) * 0x11
                    else:
                        i, a = ((v >> 1) * 0xFF) // 7, 0xFF if v & 1 else 0
                    out.append(argb(a, i, i, i))
                else:
                    i = v if bits == 8 else v * 0x11
                    out.append(argb(i, i, i, i))
    return out


def decode_variants(fmt, h):
    """The ways the game may decode a texture the XML describes as fmt, h rows high: as written,
    as the other formats of the same texel size (the day on the clock is i8 in the XML and drawn as
    ia8), and with up to kExtraRows more rows (the clock's border, 48 rows, is loaded as 50)."""
    fmts = [fmt] + [f for f in kAliases.get(fmt, ()) if f != fmt]
    return [(f, h + k) for k in range(kExtraRows + 1) for f in fmts]


def texture_bytes(fmt, w, h):
    bits = {'rgba32': 32, 'rgba16': 16, 'ia16': 16, 'ia8': 8, 'i8': 8, 'ci8': 8}.get(fmt, 4)
    return h * ((w * bits + 7) // 8)


def hd_texture_hash(w, h, texels):
    """gfx::hd_texture_hash: FNV-1a's step over 32-bit words, independent of byte order."""
    m = 0xFFFFFFFFFFFFFFFF
    x = 0xCBF29CE484222325
    for v in [w, h] + texels:
        x = ((x ^ v) * 0x100000001B3) & m
    return x

# --- The pack ------------------------------------------------------------------------------------

def hd_image(blob):
    """A pack texture: (width, height, RGBA image), or None if it isn't a raw HD image."""
    fmt_type, w, h, flags = struct.unpack_from('<IIII', blob, kResourceHeader)
    size = struct.unpack_from('<I', blob, kResourceHeader + 24)[0]
    start = kResourceHeader + 28
    if not flags & 1 or size != w * h * 4 or len(blob) < start + size:
        return None
    return Image.frombytes('RGBA', (w, h), blob[start:start + size])


def main(pack_path, rom_path, out_path):
    rom = open(rom_path, 'rb').read()
    if len(rom) != UNCOMPRESSED_SIZE:
        rom = bytes(decompress(bytearray(rom)))
    files = rom_files(rom)
    defs = texture_defs()
    pack = zipfile.ZipFile(pack_path)
    entries = {}  # hash -> (width, height decoded, rows the image covers, HD width, HD height, image)
    images = []
    textures = 0
    skipped = collections.Counter()
    for name in sorted(pack.namelist()):
        if name.endswith('/'):
            continue
        d = pick_def(defs, name)
        if d is None:
            skipped['not in the decomp'] += 1
            continue
        fmt, ow, oh = d['Format'].lower(), int(d['Width']), int(d['Height'])
        data = file_bytes(files, d['file'])
        off = int(d['Offset'], 16)
        nbytes = texture_bytes(fmt, ow, oh)
        if data is None or off + nbytes > len(data):
            skipped['not in the ROM'] += 1
            continue
        tlut = None
        if fmt.startswith('ci'):
            if 'TlutOffset' not in d:
                skipped['palette unknown'] += 1
                continue
            t = int(d['TlutOffset'], 16)
            tlut = data[t:t + (32 if fmt == 'ci4' else 512)]
        img = hd_image(pack.read(name))
        if img is None:
            skipped['not an HD image'] += 1
            continue
        scale = min(kMaxScale, max(1, round(img.width / ow)))
        tw, th = ow * scale, oh * scale
        if (tw, th) != img.size:
            img = img.resize((tw, th), Image.BOX)
        keys = set()
        for f, h in decode_variants(fmt, oh):
            n = texture_bytes(f, ow, h)
            if off + n > len(data):
                continue
            key = hd_texture_hash(ow, h, decode(f, ow, h, data[off:off + n], tlut))
            if key not in entries:
                keys.add((key, h))
        if not keys:
            skipped['same original as another'] += 1
            continue
        px = img.tobytes()
        texels = bytearray(tw * th * 4)
        texels[0::4] = px[3::4]  # A
        texels[1::4] = px[0::4]  # R
        texels[2::4] = px[1::4]  # G
        texels[3::4] = px[2::4]  # B
        images.append(bytes(texels))
        for key, h in keys:
            entries[key] = (ow, h, oh, tw, th, len(images) - 1)
        textures += 1

    keys = sorted(entries)
    header = struct.pack('>4sII', b'MMHD', 2, len(keys))
    table = bytearray()
    base = len(header) + len(keys) * 24
    offsets = []
    pos = base
    for texels in images:
        offsets.append(pos)
        pos += len(texels)
    for k in keys:
        ow, h, rows, tw, th, image = entries[k]
        table += struct.pack('>QHHHHIHH', k, ow, h, tw, th, offsets[image], rows, 0)
    with open(out_path, 'wb') as f:
        f.write(header + table)
        for texels in images:
            f.write(texels)
    print('%d textures (%d ways the game may decode them), %.1f MB' % (textures, len(keys), pos / 1e6))
    for why, n in skipped.items():
        print('skipped %d: %s' % (n, why))


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 5 and args[3] == '--decomp':
        DECOMP = args[4]
        args = args[:3]
    if len(args) != 3:
        sys.exit(__doc__)
    main(*args)
