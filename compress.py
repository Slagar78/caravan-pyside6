import binascii
from util import *

def basicDecompression(self, rom, source, addr):
    """Распаковка байтового формата (Java BasicGraphicsDecoder.decode)."""
    if isinstance(source, str):
        raw_data = binascii.unhexlify(source[addr*2:])
    else:
        rom.file.seek(addr)
        raw_data = rom.file.read(0x10000)  # с запасом, терминатор остановит

    data = bytearray(raw_data)
    output = bytearray()
    ptr = 0
    done = False

    while not done and ptr + 2 <= len(data):
        # Читаем командное слово BIG-ENDIAN (первый байт старший)
        cmd = (data[ptr] << 8) | data[ptr + 1]
        ptr += 2

        for i in range(16):
            if ptr + 2 > len(data):
                done = True
                break

            # Операнд тоже BIG-ENDIAN
            operand = (data[ptr] << 8) | data[ptr + 1]
            ptr += 2

            if (cmd & (1 << (15 - i))) != 0:          # Repeat
                if operand == 0:
                    done = True
                    break

                repeats = operand & 0x1F
                word_idx = (operand - repeats) >> 5
                cnt = 33 - repeats

                if word_idx == 1:
                    if len(output) >= 2:
                        b1, b2 = output[-2], output[-1]
                        output.extend([b1, b2] * cnt)
                else:
                    src = len(output) - word_idx * 2
                    if src >= 0:
                        for _ in range(cnt):
                            output.extend(output[src:src + 2])
                            src += 2
            else:                                      # Copy word
                # Порядок байт: сначала старший (первый), потом младший (второй)
                output.append((operand >> 8) & 0xFF)   # старший байт
                output.append(operand & 0xFF)          # младший байт

    # Байты -> нибблы (старший ниббл первого байта – первый пиксель)
    nibbles = []
    for b in output:
        nibbles.append(f"{(b >> 4) & 0xF:x}")   # старший ниббл
        nibbles.append(f"{b & 0xF:x}")          # младший ниббл
    pixels = "".join(nibbles)
    return pixels, ""


def basic_compress_hex(pixels_hex):
    """Сжатие нибблов в байтовый формат (Java BasicGraphicsDecoder.encode)."""
    assert len(pixels_hex) % 2 == 0
    byte_data = bytearray()
    for i in range(0, len(pixels_hex), 2):
        high = int(pixels_hex[i], 16)
        low  = int(pixels_hex[i+1], 16)
        byte_data.append((high << 4) | low)

    output_words = []
    cmd_idx = 0
    cmd_cursor = 0
    input_ptr = 0
    prev_word = None

    while input_ptr < len(byte_data):
        if cmd_cursor % 16 == 0:
            cmd_idx = len(output_words)
            output_words.append(0)
            cmd_cursor = 0

        # ФИКС: Big-endian – первый байт старший, второй младший
        hi = byte_data[input_ptr]
        lo = byte_data[input_ptr+1] if input_ptr+1 < len(byte_data) else 0
        cur_word = (hi << 8) | lo

        # Повторения
        repeats = 0
        if cur_word == prev_word:
            t = input_ptr
            while t < len(byte_data) and repeats < 33:
                hi_t = byte_data[t]
                lo_t = byte_data[t+1] if t+1 < len(byte_data) else 0
                if ((hi_t << 8) | lo_t) != prev_word:
                    break
                repeats += 1
                t += 2

        # Копирование цепочки
        copy_len = 0
        copy_src = 0
        src = input_ptr - 4
        while src >= 0:
            cur_len = 0
            s, d = src, input_ptr
            while True:
                hi_s = byte_data[s]
                lo_s = byte_data[s+1] if s+1 < len(byte_data) else 0
                hi_d = byte_data[d]
                lo_d = byte_data[d+1] if d+1 < len(byte_data) else 0
                if ((hi_s << 8) | lo_s) != ((hi_d << 8) | lo_d):
                    break
                cur_len += 1
                if cur_len == 33:
                    break
                s += 2
                d += 2
                if d >= len(byte_data):
                    break
            if cur_len > copy_len:
                copy_len = cur_len
                copy_src = src
            src -= 2

        if repeats > 1 or copy_len > 1:
            if repeats >= copy_len:
                val = 33 - repeats
                w = 0x0020 | val
                output_words.append(w)
                input_ptr += 2 * repeats
            else:
                start_offset = (input_ptr - copy_src) // 2
                seq_len = 33 - copy_len
                w = (start_offset << 5) | seq_len
                output_words.append(w)
                input_ptr += 2 * copy_len
            output_words[cmd_idx] |= (0x8000 >> cmd_cursor)
        else:
            output_words.append(cur_word)
            input_ptr += 2

        # ФИКС: prev_word тоже big-endian
        if input_ptr >= 2:
            hi_p = byte_data[input_ptr-2]
            lo_p = byte_data[input_ptr-1] if input_ptr-1 < len(byte_data) else 0
            prev_word = (hi_p << 8) | lo_p
        else:
            prev_word = None

        cmd_cursor += 1

    if cmd_cursor > 0:
        output_words[cmd_idx] |= (0x8000 >> cmd_cursor)

    output_words.append(0)

    # Упаковываем слова BIG-ENDIAN (старший байт первым)
    result = bytearray()
    for w in output_words:
        result.append((w >> 8) & 0xFF)   # старший байт
        result.append(w & 0xFF)          # младший байт
    return result.hex()
    

def stackDecompression(self, rom, source, addr=0):
    done = False
    reader = addr
    pixels = ""
    raw_bytes = ""
    offset_strings = []
    cmd_str = ""
    barrel = ""

    if isinstance(source, str):
        func = lambda pos, num: source[pos*2:pos*2+num*2]
    else:
        func = rom.getBytes

    pixel_stack = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f"]
    tile_ctr = 0

    tile_command = ""
    pixel_barrel = ""
    pixels = ""
    raw_pixels = ""

    while not done:
        command = ""
        cmd_ctr = 4
        tile_barrel = ""

        while cmd_ctr > 0:
            if not barrel:
                raw_barrel = func(reader, 2)
                raw_bytes += raw_barrel + " "
                barrel = "".join([bin(int(c, 16), 4) for c in raw_barrel])
                reader += 2

            for bit in barrel:
                command += bit
                barrel = barrel[1:]

                if command == "0":
                    tile_barrel += "0"
                elif command.startswith("10") and len(command) == 3:
                    tile_barrel += str(int(command[2]) + 1)
                    command = command[:2] + " " + command[2:]
                elif command == "110":
                    tile_barrel += "4"
                elif command == "1110":
                    tile_barrel += "8"
                elif command.startswith("1111") and len(command) == 8:
                    tile_barrel += hex(int(command[4:], 2))[2:]
                    command = command[:4] + " " + command[4:]
                else:
                    continue

                cmd_str += tile_barrel[-1] + ": " + command + "\n"
                cmd_ctr -= 1
                command = ""

                if cmd_ctr == 0:
                    cmd_str += "TILE: " + tile_barrel + "\n\n"
                    break

        tile_barrel = "".join([bin(int(c, 16), 4) for c in tile_barrel])

        for tile_bit in tile_barrel:
            cmd_ctr = 4
            pixel_barrel = ""

            if tile_bit == "0":
                while cmd_ctr > 0:
                    if not barrel:
                        raw_barrel = func(reader, 2)
                        raw_bytes += raw_barrel + " "
                        barrel = "".join([bin(int(c, 16), 4) for c in raw_barrel])
                        reader += 2

                    for bit in barrel:
                        command += bit
                        barrel = barrel[1:]

                        if command == "00":
                            pass
                        elif command == "01":
                            pixel_stack.insert(0, pixel_stack.pop(1))
                        elif command == "100":
                            pixel_stack.insert(0, pixel_stack.pop(2))
                        elif command == "101":
                            pixel_stack.insert(0, pixel_stack.pop(3))
                        elif command == "110":
                            pixel_stack.insert(0, pixel_stack.pop(4))
                        elif command.startswith("111") and (len(command) == 10 or (len(command)%2 == 1 and command.find("0") != -1)):
                            offset = "".join([command[s] for s in range(len(command)-1, 2, -1)]).zfill(7)
                            val = 0
                            tog = 0
                            for i in offset[1:]:
                                val += int(i) * (tog+1)
                                tog ^= 1
                            val += 5
                            val += int(offset[0])
                            pixel_stack.insert(0, pixel_stack.pop(val))
                            command = command[:3] + " " + command[3:]
                        else:
                            continue

                        pixel_barrel += pixel_stack[0]
                        cmd_str += pixel_barrel[-1] + ": " + command + "\n"
                        cmd_ctr -= 1
                        command = ""

                        if cmd_ctr == 0:
                            cmd_str += "PIXELS: " + pixel_barrel + "\n\n"
                            break

                pixels += pixel_barrel
                raw_pixels += pixel_barrel

            else:
                ctr = 11
                offset = ""

                while ctr > 0:
                    if not barrel:
                        raw_barrel = func(reader, 2)
                        raw_bytes += raw_barrel + " "
                        barrel = "".join([bin(int(c, 16), 4) for c in raw_barrel])
                        reader += 2

                    offset += barrel[0]
                    barrel = barrel[1:]
                    ctr -= 1

                real_offset = int(offset, 2)*4
                total = 0
                bit = "0"

                if real_offset == 0:
                    done = True
                    break

                start = len(raw_pixels)

                while bit == "0":
                    if not barrel:
                        raw_barrel = func(reader, 2)
                        raw_bytes += raw_barrel + " "
                        barrel = "".join([bin(int(c, 16), 4) for c in raw_barrel])
                        reader += 2

                    if real_offset == 4:
                        pixels += raw_pixels[-real_offset:]
                        raw_pixels += raw_pixels[-real_offset:]
                    else:
                        pixels += raw_pixels[-real_offset:-real_offset+4]
                        raw_pixels += raw_pixels[-real_offset:-real_offset+4]

                    total += 1
                    bit = barrel[0]
                    barrel = barrel[1:]

                if real_offset == 4:
                    pixels += raw_pixels[-real_offset:]
                    raw_pixels += raw_pixels[-real_offset:]
                else:
                    pixels += raw_pixels[-real_offset:-real_offset+4]
                    raw_pixels += raw_pixels[-real_offset:-real_offset+4]

                offset_strings.append((real_offset//2, total+1, " ".join([raw_pixels[i:i+4] for i in range(start, len(raw_pixels), 4)])+" ", offset))

    return pixels, raw_bytes