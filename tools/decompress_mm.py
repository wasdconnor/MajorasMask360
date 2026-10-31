"""Decompress a Majora's Mask NTSC-U 1.0 ROM into mm.us.rev1.rom_uncompressed.z64.

Same logic as zeldaret/mm tools/fixbaserom.py, with a built-in Yaz0 decoder
so no third-party packages are needed.

usage: python -I decompress_mm.py <input.z64> <output.z64>
"""
import hashlib
import struct
import sys

UNCOMPRESSED_SIZE = 0x2F00000
FILE_TABLE_OFFSET = 0x1A500
COMPRESSED_MD5 = "2a0a8acb61538235bc1094d297fb6556"
UNCOMPRESSED_MD5 = "f46493eaa0628827dbd6ad3ecd8d65d6"


def yaz0_decompress(src):
    assert src[:4] == b"Yaz0", "not a Yaz0 block"
    size = struct.unpack_from(">I", src, 4)[0]
    dst = bytearray(size)
    s, d = 16, 0
    while d < size:
        header = src[s]
        s += 1
        for bit in range(7, -1, -1):
            if d >= size:
                break
            if header & (1 << bit):
                dst[d] = src[s]
                s += 1
                d += 1
            else:
                b1, b2 = src[s], src[s + 1]
                s += 2
                dist = ((b1 & 0xF) << 8 | b2) + 1
                count = b1 >> 4
                if count == 0:
                    count = src[s] + 0x12
                    s += 1
                else:
                    count += 2
                start = d - dist
                for i in range(count):
                    dst[d] = dst[start + i]
                    d += 1
    return bytes(dst)


def calc_crc_6105(rom):
    mask = 0xFFFFFFFF
    t1 = t2 = t3 = t4 = t5 = t6 = 0xDF26F436
    for pos in range(0x1000, 0x101000, 4):
        d = struct.unpack_from(">I", rom, pos)[0]
        r = ((d << (d & 0x1F)) & mask) | (d >> (-(d & 0x1F) & 0x1F))
        t6d = (t6 + d) & mask
        if t6d < t6:
            t4 = (t4 + 1) & mask
        t6 = t6d
        t3 ^= d
        t5 = (t5 + r) & mask
        t2 = t2 ^ r if t2 > d else t2 ^ t6 ^ d
        t1 = (t1 + (struct.unpack_from(">I", rom, 0x0750 + (pos & 0xFF))[0] ^ d)) & mask
    return struct.pack(">II", t6 ^ t4 ^ t3, t5 ^ t2 ^ t1)


def decompress(rom):
    """The decompressed ROM, from the NTSC-U 1.0 ROM's bytes (exits on any other input)."""
    if rom[0] != 0x80:
        sys.exit("expected a big-endian .z64 ROM")
    if hashlib.md5(rom).hexdigest() != COMPRESSED_MD5:
        sys.exit("input is not the NTSC-U 1.0 ROM")

    out = bytearray(UNCOMPRESSED_SIZE)
    new_dmadata = bytearray()
    addr = FILE_TABLE_OFFSET
    while True:
        v_start, v_end, p_start, p_end = struct.unpack_from(">IIII", rom, addr)
        if not (v_start or v_end or p_start or p_end):
            break
        addr += 0x10
        if p_start == 0xFFFFFFFF and p_end == 0xFFFFFFFF:
            new_dmadata += struct.pack(">IIII", v_start, v_end, p_start, p_end)
            continue
        if p_end == 0:
            data = rom[p_start:p_start + v_end - v_start]
        else:
            data = yaz0_decompress(rom[p_start:p_end])
        out[v_start:v_start + len(data)] = data
        new_dmadata += struct.pack(">IIII", v_start, v_end, v_start, 0)

    out[FILE_TABLE_OFFSET:FILE_TABLE_OFFSET + len(new_dmadata)] = new_dmadata
    out[0x10:0x18] = calc_crc_6105(out)
    out[0x2EE8000:UNCOMPRESSED_SIZE] = b"\xFF" * (UNCOMPRESSED_SIZE - 0x2EE8000)

    digest = hashlib.md5(out).hexdigest()
    if digest != UNCOMPRESSED_MD5:
        sys.exit(f"decompressed hash mismatch: {digest}")
    return out


def main(in_path, out_path):
    out = decompress(bytearray(open(in_path, "rb").read()))
    open(out_path, "wb").write(out)
    print(f"wrote {out_path} (md5 {UNCOMPRESSED_MD5})")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
