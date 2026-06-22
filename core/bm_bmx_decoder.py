from __future__ import annotations

import struct
from pathlib import Path
from typing import Tuple

from core.image_processor import FlipperImageProcessor

try:
    import heatshrink2  # type: ignore

    HEATSHRINK_AVAILABLE = True
except ImportError:  # pragma: no cover
    heatshrink2 = None
    HEATSHRINK_AVAILABLE = False


class BM_BMX_DecodeError(ValueError):
    pass


class FlipperBmBmxDecoder:
    """Декодер Flipper .bm/.bmx для предпросмотра.

    Форматы соответствуют asset_packer.py из Momentum-Firmware:

    Формат .bm (convert_bm):
      [flag: 1B] — 0x01 = сжато heatshrink, 0x00 = raw
      Если сжато (flag=0x01):
        [padd: 1B] (always 0x00)
        [len_lo: 1B][len_hi: 1B] — длина compressed_data
        [compressed_heatshrink_data]
      Если не сжато (flag=0x00):
        [raw_xbm_bytes (black=1, white=0, MSB-first)]

    Формат .bmx (convert_bmx):
      [width: 4B LE][height: 4B LE][convert_bm_output]
    """

    @staticmethod
    def _expected_packed_bytes(width: int, height: int) -> int:
        return (int(width) * int(height)) // 8

    @classmethod
    def _decode_bm_bytes_to_xbm(cls, raw: bytes, *, path: str) -> Tuple[int, bytes]:
        """Декодирует .bm контент в XBM bytes (black=1, white=0).

        Returns:
            (flag, xbm_bytes) где flag = 0 (raw) или 1 (compressed)
        """
        if len(raw) < 1:
            raise BM_BMX_DecodeError(f"File too short: {len(raw)} bytes ({path})")

        flag = raw[0]

        if flag == 0x00:
            # Несжатый: [0x00][raw_xbm_bytes]
            return 0, raw[1:]

        elif flag == 0x01:
            # Сжатый: [0x01][0x00][len_lo][len_hi][compressed_data]
            if len(raw) < 4:
                raise BM_BMX_DecodeError(f"Compressed .bm too short: {len(raw)} bytes ({path})")

            if raw[1] != 0x00:
                # Нестандартный padd, но продолжаем
                pass

            enc_len = raw[2] | (raw[3] << 8)

            compressed_data = raw[4:]
            if len(compressed_data) < enc_len:
                compressed_data = compressed_data[:enc_len]

            if not HEATSHRINK_AVAILABLE:
                raise BM_BMX_DecodeError(
                    "Cannot decompress .bm because heatshrink2 is not available. "
                    "Install heatshrink2 or export without compression."
                )

            try:
                xbm_bytes = heatshrink2.decompress(
                    compressed_data, window_sz2=8, lookahead_sz2=4
                )
            except Exception as e:
                raise BM_BMX_DecodeError(
                    f"Failed to decompress .bm payload ({path}): {e}"
                ) from e

            return 1, xbm_bytes

        else:
            # Неизвестный флаг — может быть старый формат или просто данные
            # Пробуем интерпретировать как raw XBM (для обратной совместимости)
            return 0, raw

    @classmethod
    def _xbm_to_preview_bytes(cls, xbm_bytes: bytes, width: int, height: int) -> bytes:
        """Конвертирует XBM bytes (black=1, white=0) в preview bytes (white=1, black=0).

        Также обрезает/дополняет до ожидаемого размера.
        """
        import numpy as np

        expected = cls._expected_packed_bytes(width, height)

        if len(xbm_bytes) < expected:
            # Дополняем нулями (в XBM 0 = white)
            xbm_bytes = xbm_bytes + b"\x00" * (expected - len(xbm_bytes))
        elif len(xbm_bytes) > expected:
            xbm_bytes = xbm_bytes[:expected]

        arr = np.frombuffer(xbm_bytes, dtype=np.uint8)
        bits = np.unpackbits(arr, bitorder="big")

        # XBM: black=1, white=0.
        # Preview для Flipper: white=1, black=0.
        bits = 1 - bits

        # В некоторых пайплайнах порядок битов внутри байта инвертирован.
        # Это даёт характерный эффект «разрезания по вертикали».
        bits = bits.reshape(-1, 8)[:, ::-1].reshape(-1)

        preview_bytes = np.packbits(bits, bitorder="big").tobytes()
        return preview_bytes[:expected]




    @classmethod
    def decode_bm(cls, path: str) -> Tuple[int, int, bytes]:
        """Декодирует .bm файл.

        Returns:
            (width, height, preview_bytes) where preview_bytes has white=1, black=0
        """
        p = Path(path)
        if not p.exists():
            raise BM_BMX_DecodeError(f"File not found: {path}")

        raw = p.read_bytes()

        if len(raw) < 1:
            raise BM_BMX_DecodeError(f"Empty file: {path}")

        # Пробуем декодировать как новый формат
        flag = raw[0]

        # Новый формат: flag 0x00 или 0x01 с достаточной длиной
        if flag in (0x00, 0x01):
            try:
                _, xbm_bytes = cls._decode_bm_bytes_to_xbm(raw, path=path)

                # Определяем размер по длине XBM данных
                xbm_len = len(xbm_bytes)
                # Пробуем стандартные размеры
                candidates = [
                    (128, 64), (128, 52), (128, 32),
                    (96, 64), (112, 64), (72, 64),
                    (64, 64), (46, 49), (32, 32),
                    (16, 16), (14, 14), (12, 12), (10, 10),
                ]
                w, h = 128, 64
                for cw, ch in candidates:
                    if xbm_len == cls._expected_packed_bytes(cw, ch):
                        w, h = cw, ch
                        break
                else:
                    # Fallback: пробуем найти любой совпадающий размер
                    for cw, ch in candidates:
                        expected = cls._expected_packed_bytes(cw, ch)
                        if xbm_len >= expected:
                            w, h = cw, ch
                            xbm_bytes = xbm_bytes[:expected]
                            break

                preview_bytes = cls._xbm_to_preview_bytes(xbm_bytes, w, h)
                return w, h, preview_bytes

            except Exception:
                # Если не смогли декодировать как новый формат — fallback
                pass

        # Fallback: пробуем старый формат (BMX\x00 или просто raw bytes)
        header_size = struct.calcsize("<4sHHH")

        if len(raw) >= header_size:
            magic = raw[:4]
            if magic == b"BMX\x00":
                # Старый .bmx формат — пробуем декодировать
                try:
                    _, width, height, _flags = struct.unpack("<4sHHH", raw[:header_size])
                    payload = raw[header_size:]
                    if HEATSHRINK_AVAILABLE and len(payload) >= 4:
                        enc_data = payload[2:]
                        xbm_bytes = heatshrink2.decompress(
                            enc_data, window_sz2=8, lookahead_sz2=4
                        )
                        preview_bytes = cls._xbm_to_preview_bytes(
                            xbm_bytes, width, height
                        )
                        return int(width), int(height), preview_bytes
                except Exception:
                    pass

        # Fallback: просто raw data, предполагаем 128x64
        candidates = [
            (128, 64), (128, 52), (128, 32),
            (96, 64), (112, 64), (72, 64),
        ]
        for cw, ch in candidates:
            expected = cls._expected_packed_bytes(cw, ch)
            if len(raw) == expected or len(raw) == expected + 1:
                # Возможно это уже preview bytes или XBM без флага
                data = raw[-expected:]
                preview_bytes = cls._xbm_to_preview_bytes(data, cw, ch)
                return cw, ch, preview_bytes

        expected_default = cls._expected_packed_bytes(
            FlipperImageProcessor.WIDTH, FlipperImageProcessor.HEIGHT
        )
        raise BM_BMX_DecodeError(
            f"Unsupported .bm format: {len(raw)} bytes ({path}). "
            f"Expected ~{expected_default} bytes for 128x64."
        )

    @classmethod
    def decode_bmx(cls, path: str) -> Tuple[int, int, bytes]:
        """Декодирует .bmx файл.

        Формат: [width: 4B LE][height: 4B LE][convert_bm_output]

        Returns:
            (width, height, preview_bytes) where preview_bytes has white=1, black=0
        """
        p = Path(path)
        if not p.exists():
            raise BM_BMX_DecodeError(f"File not found: {path}")

        data = p.read_bytes()

        if len(data) < 8:
            raise BM_BMX_DecodeError(
                f"File too short for .bmx: {len(data)} bytes ({path})"
            )

        # Пробуем новый формат: [width: 4B LE][height: 4B LE][bm_content]
        width = struct.unpack("<I", data[0:4])[0]
        height = struct.unpack("<I", data[4:8])[0]

        if width > 0 and height > 0 and width <= 256 and height <= 256:
            # Правдоподобные размеры, декодируем .bm часть
            bm_data = data[8:]

            try:
                _, xbm_bytes = cls._decode_bm_bytes_to_xbm(bm_data, path=path)

                expected = cls._expected_packed_bytes(width, height)
                if len(xbm_bytes) >= expected:
                    xbm_bytes = xbm_bytes[:expected]
                elif len(xbm_bytes) < expected:
                    xbm_bytes = xbm_bytes + b"\x00" * (expected - len(xbm_bytes))

                preview_bytes = cls._xbm_to_preview_bytes(xbm_bytes, width, height)
                return int(width), int(height), preview_bytes
            except Exception as e:
                raise BM_BMX_DecodeError(
                    f"Failed to decode .bm payload in .bmx ({path}): {e}"
                ) from e

        # Fallback: старый формат (BMX\x00 header)
        header_size = struct.calcsize("<4sHHH")
        if len(data) >= header_size:
            try:
                magic, old_w, old_h, _flags = struct.unpack(
                    "<4sHHH", data[:header_size]
                )
                if magic == b"BMX\x00":
                    payload = data[header_size:]
                    if HEATSHRINK_AVAILABLE and len(payload) >= 4:
                        enc_data = payload[2:]
                        xbm_bytes = heatshrink2.decompress(
                            enc_data, window_sz2=8, lookahead_sz2=4
                        )
                        preview_bytes = cls._xbm_to_preview_bytes(
                            xbm_bytes, old_w, old_h
                        )
                        return int(old_w), int(old_h), preview_bytes
            except Exception:
                pass

        raise BM_BMX_DecodeError(
            f"Invalid .bmx container: size={len(data)} bytes, "
            f"first16={data[:16]!r} ({path})"
        )

    @classmethod
    def load_frame_as_pixmap(cls, path: str, *, scale: int = 3):
        suffix = Path(path).suffix.lower()

        if suffix == ".bm":
            w, h, raw = cls.decode_bm(path)
        elif suffix == ".bmx":
            w, h, raw = cls.decode_bmx(path)
        else:
            raise BM_BMX_DecodeError(
                f"Unsupported file extension for BM/BMX preview: {path}"
            )

        pm = FlipperImageProcessor.bytes_to_preview(
            raw, width=w, height=h, scale=scale,
            bitorder="big", invert_bits=False,
        )

        return pm, w, h