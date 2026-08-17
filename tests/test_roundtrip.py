"""Round-trip тесты экспортера/декодера (без GUI-части).

Покрывает B3: экспорт -> запись файла -> декод -> сравнение битов.

Формат — канонический Flipper/asset_packer (PIL XBM): по-строчно, LSB-first
внутри байта. Round-trip тождественен и для 128x64, и для 46x49.
"""
import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from core.image_processor import FlipperImageProcessor as IP
from core.exporter import FlipperExporter as E
from core.bm_bmx_decoder import FlipperBmBmxDecoder as D


def make_1bit_image(w: int, h: int, seed=int(0)) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = (rng.random((h, w)) > 0.6).astype(np.uint8)  # white=1
    return Image.fromarray((arr * 255).astype(np.uint8), mode="L")


class RoundTrip128x64Test(unittest.TestCase):
    def _assert_roundtrip(self, factory, decode, compress):
        w, h = 128, 64
        img = make_1bit_image(w, h, seed=42)
        fb = IP.pack_to_flipper_bytes(img, output_w=w, output_h=h)
        payload = factory(fb, w, h, compress=compress)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "frame.bin"
            p.write_bytes(payload)
            ww, hh, preview = decode(str(p))
        self.assertEqual((ww, hh), (w, h))
        self.assertEqual(len(preview), len(fb))
        self.assertTrue(
            np.array_equal(np.frombuffer(preview, np.uint8), np.frombuffer(fb, np.uint8)),
            "128x64 round-trip должен быть тождественным (B3)",
        )

    def test_bm_compressed(self):
        self._assert_roundtrip(E._make_bm_from_bytes, D.decode_bm, compress=True)

    def test_bm_raw(self):
        self._assert_roundtrip(E._make_bm_from_bytes, D.decode_bm, compress=False)

    def test_bmx_compressed(self):
        self._assert_roundtrip(E._make_bmx_from_bytes, D.decode_bmx, compress=True)

    def test_bmx_raw(self):
        self._assert_roundtrip(E._make_bmx_from_bytes, D.decode_bmx, compress=False)


class RoundTrip46x49Test(unittest.TestCase):
    """46x49: ширина не кратна 8, по-строчный паддинг. После фикса B3/46x49
    round-trip тождественен — раньше тут были «вертикальные полосы»."""

    def _assert_roundtrip(self, factory, decode, compress):
        w, h = 46, 49
        img = make_1bit_image(w, h, seed=7)
        fb = IP.pack_to_flipper_bytes(img, output_w=w, output_h=h)
        payload = factory(fb, w, h, compress=compress)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "frame.bin"
            p.write_bytes(payload)
            ww, hh, preview = decode(str(p))
        self.assertEqual((ww, hh), (w, h))
        self.assertEqual(len(preview), len(fb))
        self.assertTrue(
            np.array_equal(np.frombuffer(preview, np.uint8), np.frombuffer(fb, np.uint8)),
            "46x49 round-trip должен быть тождественным (по-строчная упаковка)",
        )

    def test_bm_compressed(self):
        self._assert_roundtrip(E._make_bm_from_bytes, D.decode_bm, compress=True)

    def test_bm_raw(self):
        self._assert_roundtrip(E._make_bm_from_bytes, D.decode_bm, compress=False)

    def test_bmx_compressed(self):
        self._assert_roundtrip(E._make_bmx_from_bytes, D.decode_bmx, compress=True)

    def test_bmx_raw(self):
        self._assert_roundtrip(E._make_bmx_from_bytes, D.decode_bmx, compress=False)


class RealFilePreviewTest(unittest.TestCase):
    """Превью файла в формате Flipper/asset_packer convert_bm: LSB-first
    внутри байта, по-строчный паддинг, black=1.
    Раньше для 46x49 получались «вертикальные полосы» из-за плоской упаковки.
    """

    def _build_real_bmx(self, arr, w, h):
        """Собирает .bmx так, как это делает asset_packer.convert_bm.
        arr: white=1 матрица. Внутри: XBM bytes = black=1, LSB-first, per-row."""
        import heatshrink2 as _hs
        black = (1 - arr).astype(np.uint8)
        xbm = np.packbits(black, axis=1, bitorder="little").tobytes()
        enc = _hs.compress(xbm, window_sz2=8, lookahead_sz2=4)
        payload = b"\x01\x00" + bytes([len(enc) & 0xFF, len(enc) >> 8]) + bytes(enc)
        return struct.pack("<II", w, h) + payload

    def test_46x49_real_file_preview(self):
        w, h = 46, 49
        rng = np.random.default_rng(3)
        arr = (rng.random((h, w)) > 0.5).astype(np.uint8)  # white=1
        bmx = self._build_real_bmx(arr, w, h)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "passport_bad_46x49.bmx"
            p.write_bytes(bmx)
            ww, hh, preview = D.decode_bmx(str(p))
        # Ожидаемое превью: по-строчный белый-мап исходной картинки.
        expected = np.packbits(arr, axis=1, bitorder="little").tobytes()
        self.assertEqual((ww, hh), (w, h))
        self.assertEqual(len(preview), len(expected))
        self.assertTrue(
            np.array_equal(np.frombuffer(preview, np.uint8), np.frombuffer(expected, np.uint8)),
            "Превью настоящего 46x49 .bmx должно совпадать с ожидаемым (без полос)",
        )

    def test_128x64_real_file_preview(self):
        w, h = 128, 64
        rng = np.random.default_rng(4)
        arr = (rng.random((h, w)) > 0.5).astype(np.uint8)
        bmx = self._build_real_bmx(arr, w, h)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "frame_0.bmx"
            p.write_bytes(bmx)
            ww, hh, preview = D.decode_bmx(str(p))
        expected = np.packbits(arr, axis=1, bitorder="little").tobytes()
        self.assertEqual((ww, hh), (w, h))
        self.assertTrue(
            np.array_equal(np.frombuffer(preview, np.uint8), np.frombuffer(expected, np.uint8)),
            "128x64 тоже должен декодироваться без реверса (LSB-first)",
        )


if __name__ == "__main__":
    unittest.main()