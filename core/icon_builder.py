from __future__ import annotations

import struct
from pathlib import Path
from typing import Dict, List, Tuple
from core.image_processor import FlipperImageProcessor
from core.exporter import FlipperExporter

# Пресеты иконок для вкладки Icons:
#   папка приложения (Name) -> {имя файла (File) -> (ширина, высота)}.
# При выборе папки экспорта создаётся папка с этим именем
# (например out_dir/SubGhz/), а файлы именуются как в File
# (например Fishing_123x52.bmx).
ICON_PRESETS: Dict[str, Dict[str, Tuple[int, int]]] = {
    "Dolphin": {
        "DolphinSuccess_91x55": (91, 55),
    },
    "NFC": {
        "NFC_dolphin_emulation_51x64": (51, 64),
    },
    "RFID": {
        "RFIDDolphinReceive_97x61": (97, 61),
        "RFIDDolphinSend_97x61": (97, 61),
    },
    "SubGhz": {
        "Fishing_123x52": (123, 52),
        "Scanning_123x52": (123, 52),
    },
    "Passport": {
        "passport_128x64": (128, 64),
        "passport_bad_46x49": (46, 49),
        "passport_happy_46x49": (46, 49),
        "passport_okay_46x49": (46, 49),
    },
}


class FlipperIconBuilder:

    """Сборка иконок приложений (Icons) для Asset Pack.

    """

    META_STRUCT_FMT = "<HHBB"

    @classmethod
    def create_binary_meta(cls, width: int, height: int, fps: int, frame_count: int) -> bytes:
        """Создаёт бинарный файл meta"""
        return struct.pack(cls.META_STRUCT_FMT, width, height, fps, frame_count)

    @classmethod
    def export_icon(
        cls,
        frames_bytes: List[bytes],
        width: int,
        height: int,
        fps: int,
        output_folder: Path,
        compress: bool = True,
        *,
        file_basename: str = "icon",
        # Для passport static нужно совпасть с pipeline Momentum (Pillow->XBM),
        # но с учётом UI dither_level.
        frames_paths: List[str] | None = None,
        dither_level: int = 1,

    ) -> Path:

        """
        Экспортирует иконку в папку.
        Если 1 кадр -> просто сохраняет файл (icon.bm или icon.bmx).
        Если >1 кадра -> создаёт папку с кадрами и бинарный meta.

        frames_bytes: список packed bytes (white=1, LSB-first, по-строчно)
        """

        if isinstance(output_folder, dict):
            raise TypeError(
                "export_icon: output_folder должен быть Path/str (например Path(out_dir)/'Icons'/app_name), "
                "а не dict"
            )

        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        ext = "bmx" if compress else "bm"

        if len(frames_bytes) == 1:
            file_path = output_folder / f"{file_basename}.{ext}"

            if frames_paths and len(frames_paths) == 1:
                png_path = frames_paths[0]
                img = FlipperImageProcessor.load_and_validate(png_path)
                img_1bit = FlipperImageProcessor.preprocess(
                    img,
                    dither_level=dither_level,
                    output_w=width,
                    output_h=height,
                )

                from PIL import ImageOps
                img_inv = ImageOps.invert(img_1bit)

                import io
                from PIL import Image
                with io.BytesIO() as output:
                    img_inv.save(output, format="XBM")
                    xbm = output.getvalue()

                import io as _io
                f = _io.StringIO(xbm.decode().strip())
                data = f.read().strip().replace("\n", "").replace(" ", "").split("=")[1][:-1]
                data_str = data[1:-1].replace(",", " ").replace("0x", "")
                xbm_bytes = bytearray.fromhex(data_str)
                xbm_bytes = bytes(xbm_bytes)

                bm_data = FlipperExporter._xbm_bytes_to_bm(xbm_bytes, compress=True)
                if compress:
                    bmx_data = struct.pack("<II", width, height) + bm_data
                    file_path.write_bytes(bmx_data)
                else:
                    file_path.write_bytes(bm_data)

                return file_path

            if compress:
                bmx_data = FlipperExporter._make_bmx_from_bytes(
                    frames_bytes[0], width, height, compress=True
                )
                file_path.write_bytes(bmx_data)
            else:
                bm_data = FlipperExporter._make_bm_from_bytes(
                    frames_bytes[0], width, height, compress=True
                )
                file_path.write_bytes(bm_data)

            return file_path

        else:
            meta_data = cls.create_binary_meta(width, height, fps, len(frames_bytes))
            (output_folder / "meta").write_bytes(meta_data)

            for i, frame_data in enumerate(frames_bytes):
                frame_path = output_folder / f"frame_{i:02}.{ext}"
                if compress:
                    bmx_data = FlipperExporter._make_bmx_from_bytes(
                        frame_data, width, height, compress=True
                    )
                    frame_path.write_bytes(bmx_data)
                else:
                    bm_data = FlipperExporter._make_bm_from_bytes(
                        frame_data, width, height, compress=True
                    )
                    frame_path.write_bytes(bm_data)

            return output_folder