"""Тесты экспортера: формат битов, .bm/.bmx, export_animation (T3, T4)."""
import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from core.image_processor import FlipperImageProcessor as IP
from core.exporter import FlipperExporter as E
from core.bm_bmx_decoder import FlipperBmBmxDecoder as D


class BitPackingTest(unittest.TestCase):
    def test_pack_128x64_length(self):
        img = Image.new("L", (128, 64), 255)
        fb = IP.pack_to_flipper_bytes(img)
        self.assertEqual(len(fb), 128 * 64 // 8)

    def test_pack_46x49_per_row_length(self):
        # 46 ширина -> 6 байт/строка (пер-роу паддинг), 49 строк -> 294 байта
        img = Image.new("L", (46, 49), 255)
        fb = IP.pack_to_flipper_bytes(img, output_w=46, output_h=49)
        self.assertEqual(len(fb), 294)

    def test_pack_white_is_zero_byte(self):
        # Все белые -> white=1 во всех битах -> байты 0xFF
        img = Image.new("L", (128, 64), 255)
        fb = IP.pack_to_flipper_bytes(img)
        self.assertEqual(fb, b"\xff" * (128 * 64 // 8))

    def test_pack_black_is_zero_byte(self):
        # Все чёрные -> white=0 во всех битах -> байты 0x00
        img = Image.new("L", (128, 64), 0)
        fb = IP.pack_to_flipper_bytes(img)
        self.assertEqual(fb, b"\x00" * (128 * 64 // 8))

    def test_bm_flag_for_compressed_and_raw(self):
        fb = b"\xff" + b"\x00" * 1023
        compressed = E._make_bm_from_bytes(fb, 128, 64, compress=True)
        raw = E._make_bm_from_bytes(fb, 128, 64, compress=False)
        self.assertEqual(compressed[0], 0x01, "сжатый .bm должен иметь flag=0x01")
        self.assertEqual(raw[0], 0x00, "raw .bm должен иметь flag=0x00")
        # raw: [0x00] + xbm-байты той же длины (128x64 даёт реверс внутри байта —
        # точное равенство байтов проверяется round-trip тестом через decode).
        self.assertEqual(len(raw[1:]), len(fb))

    def test_bmx_header(self):
        fb = b"\xff" + b"\x00" * 1023
        bmx = E._make_bmx_from_bytes(fb, 128, 64, compress=False)
        w, h = struct.unpack("<II", bmx[0:8])
        self.assertEqual((w, h), (128, 64))
        self.assertEqual(bmx[8], 0x00)  # .bm payload flag


class ExportAnimationTest(unittest.TestCase):
    def _frames(self, n=2):
        return [bytes(bytearray([i + 1])) + b"\x00" * 1023 for i in range(n)]

    def test_structure_and_txt_files(self):
        meta = "Filetype: Flipper Animation\nVersion: 1\n"
        manifest = "Filetype: Flipper Animation Manifest\nName: Test\n"
        frames = self._frames()
        with tempfile.TemporaryDirectory() as td:
            out = E.export_animation(
                frames, meta, manifest, "MyAnim", td,
                compressed=False, create_zip=False,
            )
            d = Path(out)
            self.assertEqual((d / "frame_0.bm").exists(), True)
            self.assertEqual((d / "frame_1.bm").exists(), True)
            self.assertEqual((d / "meta.txt").read_text(), meta)
            self.assertEqual((d / "manifest.txt").read_text(), manifest)

    def test_manifest_not_written_inside_anim_dir(self):
        with tempfile.TemporaryDirectory() as td:
            out = E.export_animation(
                b"\xff" * 1024, "meta", "man", "MyAnim", td,
                compressed=False, create_zip=False,
                manifest_in_anim_dir=False,
            )
            self.assertEqual((Path(out) / "manifest.txt").exists(), False)

    def test_bmx_container_when_compressed(self):
        with tempfile.TemporaryDirectory() as td:
            out = E.export_animation(
                b"\xff" * 1024, "meta", "man", "MyAnim", td,
                compressed=True, create_zip=False,
                manifest_in_anim_dir=False,
            )
            self.assertEqual((Path(out) / "frame_0.bmx").exists(), True)
            w, h, _ = D.decode_bmx(str(Path(out) / "frame_0.bmx"))
            self.assertEqual((w, h), (128, 64))

    def test_create_zip(self):
        with tempfile.TemporaryDirectory() as td:
            out = E.export_animation(
                b"\xff" * 1024, "meta", "man", "MyAnim", td,
                compressed=False, create_zip=True, manifest_in_anim_dir=False,
            )
            self.assertEqual(Path(out).suffix, ".zip")
            self.assertEqual(Path(out).exists(), True)


if __name__ == "__main__":
    unittest.main()