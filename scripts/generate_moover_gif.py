#!/usr/bin/env python3
"""Generate Moover's animated ASCII-style grazing GIF without dependencies."""

from __future__ import annotations

from pathlib import Path


GLYPHS = {
    " ": ["000", "000", "000", "000", "000", "000", "000"],
    "'": ["1", "1", "0", "0", "0", "0", "0"],
    ",": ["0", "0", "0", "0", "0", "1", "1"],
    "(": ["01", "10", "10", "10", "10", "10", "01"],
    ")": ["10", "01", "01", "01", "01", "01", "10"],
    "/": ["0001", "0010", "0010", "0100", "0100", "1000", "1000"],
    "\\": ["1000", "0100", "0100", "0010", "0010", "0001", "0001"],
    "_": ["0000", "0000", "0000", "0000", "0000", "0000", "1111"],
    "^": ["010", "101", "000", "000", "000", "000", "000"],
    "|": ["1", "1", "1", "1", "1", "1", "1"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "e": ["00000", "01110", "10001", "11111", "10000", "10001", "01110"],
    "o": ["00000", "01110", "10001", "10001", "10001", "10001", "01110"],
    "r": ["00000", "10110", "11001", "10000", "10000", "10000", "10000"],
    "v": ["00000", "10001", "10001", "10001", "01010", "01010", "00100"],
    "w": ["00000", "10001", "10001", "10101", "10101", "10101", "01010"],
}


FRAMES = [
    [
        "      Moover",
        "",
        "  ^__^",
        "  (oo)\\_______",
        "  (__)\\       )\\/\\",
        "      ||----w |",
        "      ||     ||",
        "",
        " ''  ,,  vv  ,,  ''",
    ],
    [
        "      Moover",
        "",
        "   ^__^",
        "   (oo)\\_______",
        "   (__)\\       )\\/\\",
        "       ||----w |",
        "       ||     ||",
        "",
        "   ,,  vv  ''  ,,  vv",
    ],
    [
        "      Moover",
        "",
        "    ^__^",
        "    (oo)\\_______",
        "    (__)\\       )\\/\\",
        "        ||----w |",
        "        ||     ||",
        "",
        " vv  ''  ,,  vv  ''",
    ],
    [
        "      Moover",
        "",
        "     __",
        "    (oo)\\_______",
        "    (__)\\       )\\/\\",
        "        ||----w |",
        "        ||     ||",
        "      ^__^",
        " ,,  vv  ''  ,,  vv",
    ],
]


WIDTH = 640
HEIGHT = 360
SCALE = 4
CHAR_SPACING = 2
LINE_SPACING = 8
X_OFFSET = 72
Y_OFFSET = 46

BG = 0
TEXT = 1
GRASS_BG = 2
GRASS = 3
PALETTE = [
    (229, 245, 210),
    (28, 42, 25),
    (190, 226, 155),
    (69, 122, 54),
]


def glyph_for(char: str) -> list[str]:
    if char == "-":
        return ["0000", "0000", "0000", "1111", "0000", "0000", "0000"]
    return GLYPHS.get(char, GLYPHS[" "])


def draw_glyph(pixels: list[int], x: int, y: int, char: str, color: int) -> int:
    glyph = glyph_for(char)
    glyph_width = len(glyph[0])
    for row, line in enumerate(glyph):
        for col, value in enumerate(line):
            if value != "1":
                continue
            for dy in range(SCALE):
                for dx in range(SCALE):
                    px = x + (col * SCALE) + dx
                    py = y + (row * SCALE) + dy
                    if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                        pixels[(py * WIDTH) + px] = color
    return (glyph_width * SCALE) + CHAR_SPACING


def draw_text_frame(lines: list[str]) -> list[int]:
    pixels = [BG] * (WIDTH * HEIGHT)
    for y in range(HEIGHT - 90, HEIGHT):
        for x in range(WIDTH):
            pixels[(y * WIDTH) + x] = GRASS_BG

    y = Y_OFFSET
    for line in lines:
        x = X_OFFSET
        for char in line:
            color = GRASS if char in {"'", ",", "v"} and y > 230 else TEXT
            x += draw_glyph(pixels, x, y, char, color)
        y += (7 * SCALE) + LINE_SPACING
    return pixels


def pack_sub_blocks(data: bytes) -> bytes:
    output = bytearray()
    for index in range(0, len(data), 255):
        block = data[index : index + 255]
        output.append(len(block))
        output.extend(block)
    output.append(0)
    return bytes(output)


def lzw_encode(indices: list[int], min_code_size: int = 2) -> bytes:
    clear_code = 1 << min_code_size
    end_code = clear_code + 1
    next_code = end_code + 1
    code_size = min_code_size + 1
    dictionary = {(index,): index for index in range(clear_code)}
    bits = []

    def emit(code: int) -> None:
        for bit in range(code_size):
            bits.append((code >> bit) & 1)

    emit(clear_code)
    phrase: tuple[int, ...] = ()
    for index in indices:
        candidate = phrase + (index,)
        if candidate in dictionary:
            phrase = candidate
            continue

        emit(dictionary[phrase])
        if next_code < 4096:
            dictionary[candidate] = next_code
            next_code += 1
            if next_code == (1 << code_size) and code_size < 12:
                code_size += 1
        phrase = (index,)

    if phrase:
        emit(dictionary[phrase])
    emit(end_code)

    output = bytearray()
    for index in range(0, len(bits), 8):
        byte = 0
        for offset, bit in enumerate(bits[index : index + 8]):
            byte |= bit << offset
        output.append(byte)
    return bytes(output)


def write_gif(path: Path, frames: list[list[int]]) -> None:
    data = bytearray()
    data.extend(b"GIF89a")
    data.extend(WIDTH.to_bytes(2, "little"))
    data.extend(HEIGHT.to_bytes(2, "little"))
    data.append(0b11110001)
    data.append(0)
    data.append(0)
    for red, green, blue in PALETTE:
        data.extend(bytes([red, green, blue]))

    data.extend(b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00")

    for frame in frames:
        data.extend(b"\x21\xf9\x04\x00")
        data.extend((45).to_bytes(2, "little"))
        data.extend(b"\x00\x00")
        data.extend(b"\x2c\x00\x00\x00\x00")
        data.extend(WIDTH.to_bytes(2, "little"))
        data.extend(HEIGHT.to_bytes(2, "little"))
        data.append(0)
        data.append(2)
        data.extend(pack_sub_blocks(lzw_encode(frame)))

    data.extend(b"\x3b")
    path.write_bytes(data)


def main() -> None:
    output = Path("assets/moover-grazing.gif")
    output.parent.mkdir(exist_ok=True)
    write_gif(output, [draw_text_frame(frame) for frame in FRAMES])
    print(f"Generated {output}")


if __name__ == "__main__":
    main()
