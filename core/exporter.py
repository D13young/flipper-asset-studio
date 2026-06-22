import struct
import os
import zipfile
from pathlib import Path
from typing import List, Union
from PIL import Image, ImageOps

try:
    import heatshrink2
    HEATSHRINK_AVAILABLE = True
except ImportError:
    HEATSHRINK_AVAILABLE = False
    print("⚠️ heatshrink2 не установлен. Сжатие .bm/.bmx будет пропущено.")


class FlipperExporter:
    """
    Экспортер в форматы .bm/.bmx, совместимые с asset_packer.py из Momentum-Firmware.

    Формат .bm (convert_bm):
      [flag: 1B] — 0x01 = сжато heatshrink, 0x00 = raw
      Если сжато (flag=0x01):
        [padd: 1B] (always 0x00)
        [len_lo: 1B][len_hi: 1B] — длина compressed_data
        [compressed_heatshrink_data]
      Если не сжато (flag=0x00):
        [raw_xbm_bytes]

    Формат .bmx (convert_bmx):
      [width: 4B LE][height: 4B LE][convert_bm_output]
    """

    @staticmethod
    def _image_to_xbm_bytes(img_1bit: Image.Image) -> bytes:
        """Конвертирует 1-бит PIL Image в XBM byte array как в asset_packer.py.

        Вход: белые пиксели = 255/True, чёрные = 0/False
        Выход: XBM формат (black=1, white=0, MSB-first)
        """
        import io
        with io.BytesIO() as output:
            # Инвертируем: black=1, white=0 (как XBM)
            img_inv = ImageOps.invert(img_1bit.convert("1"))
            img_inv.save(output, format="XBM")
            xbm = output.getvalue()

        # Парсим XBM как в asset_packer.py
        f = io.StringIO(xbm.decode().strip())
        data = f.read().strip().replace("\n", "").replace(" ", "").split("=")[1][:-1]
        data_str = data[1:-1].replace(",", " ").replace("0x", "")
        data_bin = bytearray.fromhex(data_str)
        return bytes(data_bin)

    @staticmethod
    def _xbm_bytes_to_bm(xbm_bytes: bytes, compress: bool = True) -> bytes:
        """Упаковывает XBM bytes в формат .bm как в asset_packer.py.

        Params:
            xbm_bytes: сырые XBM байты (black=1, white=0)
            compress: использовать heatshrink сжатие

        Returns:
            .bm содержимое
        """
        if compress and HEATSHRINK_AVAILABLE:
            data_encoded_str = heatshrink2.compress(xbm_bytes, window_sz2=8, lookahead_sz2=4)
            data_enc = bytearray(data_encoded_str)
            data_enc = bytearray([len(data_enc) & 0xFF, len(data_enc) >> 8]) + data_enc

            if len(data_enc) + 2 < len(xbm_bytes) + 1:
                return b"\x01\x00" + data_enc
            else:
                return b"\x00" + xbm_bytes
        else:
            return b"\x00" + xbm_bytes

    @staticmethod
    def _make_bm_from_image(img_1bit: Image.Image, compress: bool = True) -> bytes:
        """Создаёт .bm контент из 1-бит PIL Image."""
        xbm_bytes = FlipperExporter._image_to_xbm_bytes(img_1bit)
        return FlipperExporter._xbm_bytes_to_bm(xbm_bytes, compress=compress)

    @staticmethod
    def _make_bmx_from_image(img_1bit: Image.Image, compress: bool = True) -> bytes:
        """Создаёт .bmx контент из 1-бит PIL Image (ширина/высота из image)."""
        width, height = img_1bit.size
        bm_data = FlipperExporter._make_bm_from_image(img_1bit, compress=compress)
        header = struct.pack("<II", width, height)  # width 4B LE, height 4B LE
        return header + bm_data

    @staticmethod
    def _make_bm_from_bytes(
        raw_1bit_bytes: bytes,
        width: int,
        height: int,
        compress: bool = True,
    ) -> bytes:
        """Создаёт .bm из голых packed-байтов (white=1, MSB-first).

        XBM генерируем через PIL (convert("1") + ImageOps.invert + save(format="XBM")).
        """
        import numpy as np
        import io

        w = int(width)
        h = int(height)
        expected_bits = w * h
        expected_bytes = (expected_bits + 7) // 8

        buf = bytes(raw_1bit_bytes)
        if len(buf) < expected_bytes:
            buf = buf + b"\x00" * (expected_bytes - len(buf))
        elif len(buf) > expected_bytes:
            buf = buf[:expected_bytes]

        arr = np.frombuffer(buf, dtype=np.uint8)
        bits = np.unpackbits(arr, bitorder="big")[:expected_bits]
        bits = bits.reshape(h, w).astype(np.uint8)

        # Создаём PIL '1' изображение: white=1, black=0.
        # В PIL при save(format="XBM") будет применён XBM-специфичный порядок бит.
        img = Image.fromarray((bits * 255).astype(np.uint8), mode="L").convert("1")

        with io.BytesIO() as output:
            img_inv = ImageOps.invert(img)
            img_inv.save(output, format="XBM")
            xbm = output.getvalue()

        f = io.StringIO(xbm.decode().strip())
        data = f.read().strip().replace("\n", "").replace(" ", "").split("=")[1][:-1]
        data_str = data[1:-1].replace(",", " ").replace("0x", "")
        xbm_bytes = bytes(bytearray.fromhex(data_str))

        return FlipperExporter._xbm_bytes_to_bm(xbm_bytes, compress=compress)


    @staticmethod
    def _make_bmx_from_bytes(
        raw_1bit_bytes: bytes,
        width: int,
        height: int,
        compress: bool = True,
    ) -> bytes:
        """Создаёт .bmx из голых packed-байтов (white=1, MSB-first)."""
        bm_data = FlipperExporter._make_bm_from_bytes(
            raw_1bit_bytes, width, height, compress=compress
        )
        header = struct.pack("<II", width, height)
        return header + bm_data

    @classmethod
    def export_animation(
        cls,
        frames: List[bytes],
        meta_txt: str,
        manifest_txt: str,
        anim_name: str,
        output_dir: Union[str, Path],
        compressed: bool = True,
        create_zip: bool = False,
    ) -> Path:
        out = Path(output_dir)
        anim_dir = out / anim_name
        anim_dir.mkdir(parents=True, exist_ok=True)

        width = 128
        height = 64

        ext = "bmx" if compressed else "bm"
        for i, frame_data in enumerate(frames):
            frame_path = anim_dir / f"frame_{i}.{ext}"
            if compressed:
                bmx = cls._make_bmx_from_bytes(
                    raw_1bit_bytes=frame_data,
                    width=width,
                    height=height,
                    compress=True,
                )
                frame_path.write_bytes(bmx)
            else:
                bm = cls._make_bm_from_bytes(
                    raw_1bit_bytes=frame_data,
                    width=width,
                    height=height,
                    compress=False,
                )
                frame_path.write_bytes(bm)

        (anim_dir / "meta.txt").write_text(meta_txt, encoding="utf-8")
        (anim_dir / "manifest.txt").write_text(manifest_txt, encoding="utf-8")

        if create_zip:
            zip_path = out / f"{anim_name}_pack.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(anim_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(out)
                        zf.write(file_path, arcname)
            return zip_path

        return anim_dir


