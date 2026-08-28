import struct


_MULAW_BIAS = 0x84


def mulaw_to_pcm16(data: bytes) -> bytes:
    output = bytearray(len(data) * 2)

    for index, value in enumerate(data):
        value = ~value & 0xFF

        sign = value & 0x80
        exponent = (value >> 4) & 0x07
        mantissa = value & 0x0F

        sample = ((mantissa << 3) + _MULAW_BIAS) << exponent
        sample -= _MULAW_BIAS

        if sign:
            sample = -sample

        struct.pack_into("<h", output, index * 2, sample)

    return bytes(output)


def pcm16_to_mulaw(data: bytes) -> bytes:
    output = bytearray(len(data) // 2)

    for index in range(0, len(data), 2):
        sample = struct.unpack_from("<h", data, index)[0]

        sign = 0x80 if sample < 0 else 0

        if sample < 0:
            sample = -sample

        sample += _MULAW_BIAS

        exponent = 7
        mask = 0x4000

        while exponent > 0 and not (sample & mask):
            exponent -= 1
            mask >>= 1

        mantissa = (sample >> (exponent + 3)) & 0x0F

        output[index // 2] = ~(sign | (exponent << 4) | mantissa) & 0xFF

    return bytes(output)