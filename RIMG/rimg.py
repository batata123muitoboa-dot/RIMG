import struct
import zlib
from PIL import Image

MAGIC = b"RIMG"

VERSION = 3

COMPRESSION_RAW = 0
COMPRESSION_RLE = 1
COMPRESSION_PREDICTIVE = 2
COMPRESSION_FILTERED = 3
COMPRESSION_PLANAR = 4

PIXEL_RGBA8888 = 1

HEADER_FORMAT = "<4sBBBBIII"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


# ============================================================
# RLE - RIMG v1
# ============================================================

def encode_rle(pixels):
    output = bytearray()

    if not pixels:
        return output

    current = pixels[0]
    count = 1

    for pixel in pixels[1:]:
        if pixel == current and count < 0xFFFFFFFF:
            count += 1
        else:
            output += struct.pack("<I", count)
            output += bytes(current)

            current = pixel
            count = 1

    output += struct.pack("<I", count)
    output += bytes(current)

    return output


def decode_rle(data, pixel_count):
    pixels = bytearray()
    offset = 0

    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError("RIMG: RLE corrompido")

        count = struct.unpack_from("<I", data, offset)[0]
        offset += 4

        pixel = data[offset:offset + 4]
        offset += 4

        if len(pixel) != 4:
            raise ValueError("RIMG: pixel RLE incompleto")

        pixels += pixel * count

        if len(pixels) > pixel_count * 4:
            raise ValueError("RIMG: RLE excede o tamanho da imagem")

    if len(pixels) != pixel_count * 4:
        raise ValueError("RIMG: quantidade de pixels inválida")

    return bytes(pixels)


# ============================================================
# PREDICTIVE - RIMG v2
# ============================================================

def encode_predictive(raw_data):
    if not raw_data:
        return b""

    predicted = bytearray(len(raw_data))
    previous = 0

    for i, value in enumerate(raw_data):
        predicted[i] = (value - previous) & 0xFF
        previous = value

    return zlib.compress(bytes(predicted), level=6)


def decode_predictive(data, expected_size):
    predicted = zlib.decompress(data)

    if len(predicted) != expected_size:
        raise ValueError(
            "RIMG: tamanho dos dados preditivos inválido"
        )

    raw_data = bytearray(expected_size)
    previous = 0

    for i, value in enumerate(predicted):
        raw_data[i] = (value + previous) & 0xFF
        previous = raw_data[i]

    return bytes(raw_data)


# ============================================================
# FILTROS - RIMG v3
# ============================================================

FILTER_NONE = 0
FILTER_SUB = 1
FILTER_UP = 2
FILTER_AVERAGE = 3
FILTER_PAETH = 4

def encode_planar(raw_data, width, height):
    pixels = len(raw_data) // 4

    r = bytearray()
    g = bytearray()
    b = bytearray()
    a = bytearray()

    for i in range(pixels):
        p = i * 4
        r.append(raw_data[p])
        g.append(raw_data[p + 1])
        b.append(raw_data[p + 2])
        a.append(raw_data[p + 3])

    channels = [r, g, b, a]
    output = bytearray()

    for channel in channels:
        filtered = encode_filtered(
            bytes(channel),
            width,
            height
        )

        output += struct.pack("<I", len(filtered))
        output += filtered

    return zlib.compress(
        bytes(output),
        level=9
    )


def decode_planar(data, width, height):
    decoded = zlib.decompress(data)

    offset = 0
    channels = []

    expected_channel_size = width * height

    for _ in range(4):
        if offset + 4 > len(decoded):
            raise ValueError(
                "RIMG: dados planares corrompidos"
            )

        size = struct.unpack_from(
            "<I",
            decoded,
            offset
        )[0]

        offset += 4

        channel_data = decoded[
            offset:offset + size
        ]

        offset += size

        channel = decode_filtered(
            channel_data,
            width,
            height
        )

        if len(channel) != expected_channel_size:
            raise ValueError(
                "RIMG: canal inválido"
            )

        channels.append(channel)

    r, g, b, a = channels

    raw_data = bytearray(
        expected_channel_size * 4
    )

    for i in range(expected_channel_size):
        p = i * 4

        raw_data[p] = r[i]
        raw_data[p + 1] = g[i]
        raw_data[p + 2] = b[i]
        raw_data[p + 3] = a[i]

    return bytes(raw_data)

def paeth_predictor(a, b, c):
    """
    a = esquerda
    b = cima
    c = diagonal
    """

    p = a + b - c

    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)

    if pa <= pb and pa <= pc:
        return a

    if pb <= pc:
        return b

    return c


def filter_row(row, previous_row, bytes_per_pixel, filter_type):
    result = bytearray(len(row))

    for i in range(len(row)):
        current = row[i]

        left = (
            row[i - bytes_per_pixel]
            if i >= bytes_per_pixel
            else 0
        )

        up = (
            previous_row[i]
            if previous_row is not None
            else 0
        )

        upper_left = (
            previous_row[i - bytes_per_pixel]
            if previous_row is not None and i >= bytes_per_pixel
            else 0
        )

        if filter_type == FILTER_NONE:
            value = current

        elif filter_type == FILTER_SUB:
            value = current - left

        elif filter_type == FILTER_UP:
            value = current - up

        elif filter_type == FILTER_AVERAGE:
            value = current - ((left + up) // 2)

        elif filter_type == FILTER_PAETH:
            predictor = paeth_predictor(
                left,
                up,
                upper_left
            )

            value = current - predictor

        else:
            raise ValueError("RIMG: filtro desconhecido")

        result[i] = value & 0xFF

    return bytes(result)


def unfilter_row(
    filtered_row,
    previous_row,
    bytes_per_pixel,
    filter_type
):
    row = bytearray(len(filtered_row))

    for i in range(len(filtered_row)):
        value = filtered_row[i]

        left = (
            row[i - bytes_per_pixel]
            if i >= bytes_per_pixel
            else 0
        )

        up = (
            previous_row[i]
            if previous_row is not None
            else 0
        )

        upper_left = (
            previous_row[i - bytes_per_pixel]
            if previous_row is not None and i >= bytes_per_pixel
            else 0
        )

        if filter_type == FILTER_NONE:
            current = value

        elif filter_type == FILTER_SUB:
            current = value + left

        elif filter_type == FILTER_UP:
            current = value + up

        elif filter_type == FILTER_AVERAGE:
            current = value + ((left + up) // 2)

        elif filter_type == FILTER_PAETH:
            predictor = paeth_predictor(
                left,
                up,
                upper_left
            )

            current = value + predictor

        else:
            raise ValueError("RIMG: filtro desconhecido")

        row[i] = current & 0xFF

    return bytes(row)


def filter_score(data):
    """
    Mede quão fácil é para o compressor
    comprimir os dados.

    Valores próximos de zero são melhores.
    """

    return sum(
        min(value, 256 - value)
        for value in data
    )


def encode_filtered(raw_data, width, height):
    bytes_per_pixel = 4
    row_size = width * bytes_per_pixel

    output = bytearray()

    previous_row = None

    for y in range(height):
        start = y * row_size
        end = start + row_size

        row = raw_data[start:end]

        best_filter = None
        best_filtered = None
        best_score = None

        for filter_type in range(5):
            filtered = filter_row(
                row,
                previous_row,
                bytes_per_pixel,
                filter_type
            )

            score = filter_score(filtered)

            if best_score is None or score < best_score:
                best_score = score
                best_filter = filter_type
                best_filtered = filtered

        # 1 byte indicando qual filtro foi usado
        output.append(best_filter)

        output += best_filtered

        previous_row = row

    return zlib.compress(bytes(output), level=6)


def decode_filtered(data, width, height):
    decoded = zlib.decompress(data)

    bytes_per_pixel = 4
    row_size = width * bytes_per_pixel

    expected_size = height * (row_size + 1)

    if len(decoded) != expected_size:
        raise ValueError(
            "RIMG: tamanho dos dados filtrados inválido"
        )

    raw_data = bytearray()

    offset = 0
    previous_row = None

    for _ in range(height):
        filter_type = decoded[offset]
        offset += 1

        filtered_row = decoded[
            offset:offset + row_size
        ]

        offset += row_size

        row = unfilter_row(
            filtered_row,
            previous_row,
            bytes_per_pixel,
            filter_type
        )

        raw_data += row

        previous_row = row

    return bytes(raw_data)


# ============================================================
# SALVAR RIMG
# ============================================================

def save_rimg(filename, image):
    image = image.convert("RGBA")

    width, height = image.size
    raw_data = image.tobytes()

    # ----------------------------
    # RLE
    # ----------------------------

    pixels = [
        raw_data[i:i + 4]
        for i in range(0, len(raw_data), 4)
    ]

    rle_data = encode_rle(pixels)

    # ----------------------------
    # Predictive v2
    # ----------------------------

    predictive_data = encode_predictive(raw_data)

    # ----------------------------
    # Filtered v3
    # ----------------------------

    filtered_data = encode_filtered(
        raw_data,
        width,
        height
    )

    planar_data = encode_planar(
    raw_data,
    width,
    height
)

    # ----------------------------
    # Escolhe o menor
    # ----------------------------

    options = [
    (COMPRESSION_RAW, raw_data),
    (COMPRESSION_RLE, rle_data),
    (COMPRESSION_PREDICTIVE, predictive_data),
    (COMPRESSION_FILTERED, filtered_data),
    (COMPRESSION_PLANAR, planar_data),
]

    compression, data = min(
        options,
        key=lambda option: len(option[1])
    )

    # ----------------------------
    # Header
    # ----------------------------

    header = struct.pack(
        HEADER_FORMAT,
        MAGIC,
        VERSION,
        compression,
        PIXEL_RGBA8888,
        0,
        width,
        height,
        len(data),
    )

    with open(filename, "wb") as f:
        f.write(header)
        f.write(data)

    print(f"RIMG criado: {filename}")
    print(f"Dimensão: {width}x{height}")
    print()
    print("Compressões:")
    print(f"  RAW:        {len(raw_data):,} bytes")
    print(f"  RLE:        {len(rle_data):,} bytes")
    print(f"  Predictive: {len(predictive_data):,} bytes")
    print(f"  Filtered:   {len(filtered_data):,} bytes")
    print(f"  Planar:     {len(planar_data):,} bytes")
    print()
    print(f"Escolhida:   {compression}")
    print(f"RIMG final:  {len(data):,} bytes")


# ============================================================
# CARREGAR RIMG
# ============================================================

def load_rimg(filename):
    with open(filename, "rb") as f:
        header = f.read(HEADER_SIZE)

        if len(header) != HEADER_SIZE:
            raise ValueError("RIMG: header incompleto")

        (
            magic,
            version,
            compression,
            pixel_format,
            reserved,
            width,
            height,
            data_size,
        ) = struct.unpack(
            HEADER_FORMAT,
            header
        )

        if magic != MAGIC:
            raise ValueError(
                "Não é um arquivo RIMG"
            )

        if version > VERSION:
            raise ValueError(
                f"Versão RIMG não suportada: {version}"
            )

        if pixel_format != PIXEL_RGBA8888:
            raise ValueError(
                "Formato de pixel não suportado"
            )

        data = f.read(data_size)

        if len(data) != data_size:
            raise ValueError(
                "RIMG: dados incompletos"
            )

    pixel_count = width * height
    expected_size = pixel_count * 4

    # ----------------------------
    # RAW
    # ----------------------------

    if compression == COMPRESSION_RAW:

        if len(data) != expected_size:
            raise ValueError(
                "RIMG: tamanho RAW inválido"
            )

        raw_data = data

    # ----------------------------
    # RLE
    # ----------------------------

    elif compression == COMPRESSION_RLE:

        raw_data = decode_rle(
            data,
            pixel_count
        )

    # ----------------------------
    # Predictive
    # ----------------------------

    elif compression == COMPRESSION_PREDICTIVE:

        raw_data = decode_predictive(
            data,
            expected_size
        )

    # ----------------------------
    # Filtered
    # ----------------------------

    elif compression == COMPRESSION_FILTERED:

        raw_data = decode_filtered(
            data,
            width,
            height
        )

        if len(raw_data) != expected_size:
            raise ValueError(
                "RIMG: tamanho dos dados filtrados inválido"
            )

    else:
        raise ValueError(
            "RIMG: compressão desconhecida"
        )

    return Image.frombytes(
        "RGBA",
        (width, height),
        raw_data
    )


# ============================================================
# CONVERSORES
# ============================================================

def png_to_rimg(input_file, output_file):
    image = Image.open(input_file)

    save_rimg(
        output_file,
        image
    )


def rimg_to_png(input_file, output_file):
    image = load_rimg(input_file)

    image.save(
        output_file
    )


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 4:
        print("Uso:")
        print()
        print(
            "  python rimg.py "
            "png2rimg entrada.png saida.rimg"
        )

        print(
            "  python rimg.py "
            "rimg2png entrada.rimg saida.png"
        )

        sys.exit(1)

    command = sys.argv[1]
    input_file = sys.argv[2]
    output_file = sys.argv[3]

    if command == "png2rimg":

        png_to_rimg(
            input_file,
            output_file
        )

    elif command == "rimg2png":

        rimg_to_png(
            input_file,
            output_file
        )

    else:
        print("Comando desconhecido")