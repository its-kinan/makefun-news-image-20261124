#!/usr/bin/env python3
"""news-image-20261124 entry: copy the validated front page to the output.

Reads entry.png from this repository's root, runs a full PNG chunk-walk
validation (magic, IHDR first, every chunk CRC, IEND last, 1024x1024,
under 1 MiB), then writes the exact bytes to
$MAKEFUN_OUTPUT_DIR/entry.png (default: out/entry.png).

Standard library only. No network, no clock, no randomness: the two
grader runs produce byte-identical output.
"""
import os
import struct
import sys
import zlib

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 1048576
EXPECT_W, EXPECT_H = 1024, 1024


def fail(msg):
    print("main.py: error: " + msg, file=sys.stderr)
    sys.exit(1)


def check_png(data):
    if len(data) < 8 or data[:8] != PNG_MAGIC:
        fail("not a PNG file (bad magic)")
    if len(data) > MAX_BYTES:
        fail("file is %d bytes, over the 1 MiB limit" % len(data))
    pos = 8
    seen_ihdr = False
    seen_idat = False
    seen_iend = False
    width = height = None
    while pos < len(data):
        if pos + 8 > len(data):
            fail("truncated chunk header at offset %d" % pos)
        length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
        if pos + 12 + length > len(data):
            fail("truncated chunk %r at offset %d" % (ctype, pos))
        body = data[pos + 8:pos + 8 + length]
        crc_stored, = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
        crc_actual = zlib.crc32(ctype)
        crc_actual = zlib.crc32(body, crc_actual)
        if crc_actual != crc_stored:
            fail("bad CRC in chunk %r at offset %d" % (ctype, pos))
        if not seen_ihdr:
            if ctype != b"IHDR":
                fail("first chunk is %r, expected IHDR" % ctype)
            if length != 13:
                fail("IHDR is %d bytes, expected 13" % length)
            width, height, depth, ctype_id, comp, filt, inter = struct.unpack(
                ">IIBBBBB", body)
            if (width, height) != (EXPECT_W, EXPECT_H):
                fail("image is %dx%d, expected 1024x1024" % (width, height))
            if (depth, ctype_id, comp, filt, inter) != (8, 2, 0, 0, 0):
                fail("unexpected IHDR fields: depth=%d color=%d comp=%d "
                     "filter=%d interlace=%d" % (depth, ctype_id, comp, filt, inter))
            seen_ihdr = True
        elif ctype == b"IDAT":
            seen_idat = True
        elif ctype == b"IEND":
            if length != 0:
                fail("IEND carries %d bytes, expected 0" % length)
            if pos + 12 + length != len(data):
                fail("trailing bytes after IEND")
            seen_iend = True
            break
        pos += 12 + length
    if not seen_ihdr:
        fail("no IHDR chunk found")
    if not seen_idat:
        fail("no IDAT chunk found")
    if not seen_iend:
        fail("no IEND chunk found")
    return width, height


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "entry.png")
    try:
        with open(src, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        fail("cannot read entry.png: %s" % exc)
    width, height = check_png(data)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    out_path = os.path.join(out_dir, "entry.png")
    try:
        os.makedirs(out_dir, exist_ok=True)
        with open(out_path, "wb") as fh:
            fh.write(data)
    except OSError as exc:
        fail("cannot write %s: %s" % (out_path, exc))
    # Round-trip check: the bytes on disk must be exactly the bytes
    # validated above, so a partial write can never pass silently.
    try:
        with open(out_path, "rb") as fh:
            written = fh.read()
    except OSError as exc:
        fail("cannot re-read %s: %s" % (out_path, exc))
    if written != data:
        fail("round-trip mismatch on %s" % out_path)
    print("wrote %s (%dx%d, %d bytes)" % (out_path, width, height, len(data)))


if __name__ == "__main__":
    main()
