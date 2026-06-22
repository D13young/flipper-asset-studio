import struct
import traceback
from pathlib import Path
from typing import List
from core.image_processor import FlipperImageProcessor
from core.exporter import FlipperExporter


class FlipperIconBuilder:
    """Сборка иконок приложений (Icons) для Asset Pack.

    """

    # Формат бинарного meta для иконок:
    # Width (2B), Height (2B), Frame Rate (1B), Frame Count (1B) = 6 байт
    # Little Endian ("<")
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
    ) -> Path:


        """
        Экспортирует иконку в папку.
        Если 1 кадр -> просто сохраняет файл (icon.bm или icon.bmx).
        Если >1 кадра -> создаёт папку с кадрами и бинарный meta.

        frames_bytes: список packed bytes (white=1, MSB-first)
        """
        # output_folder обязан быть путём (Path/str), а не результатом process_png.
        # Если снаружи прилетает dict — это обычно ошибка прокидывания аргументов.
        if isinstance(output_folder, dict):
            # Логируем контекст, чтобы точно понять откуда прилетает dict
            print("[FlipperIconBuilder.export_icon] output_folder is dict")
            print("type:", type(output_folder))
            try:
                print("keys:", list(output_folder.keys()))
            except Exception:
                pass
            print("stack:\n" + "".join(traceback.format_stack(limit=25)))
            raise TypeError(
                "export_icon: output_folder должен быть Path/str (например Path(out_dir)/'Icons'/app_name), "
                "а не dict"
            )

        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        ext = "bmx" if compress else "bm"

        if len(frames_bytes) == 1:
            # Статическая иконка: просто один файл
            file_path = output_folder / f"{file_basename}.{ext}"


            # Конвертируем в формат asset_packer.py
            if compress:
                bmx_data = FlipperExporter._make_bmx_from_bytes(
                    frames_bytes[0], width, height, compress=True
                )
                file_path.write_bytes(bmx_data)
            else:
                bm_data = FlipperExporter._make_bm_from_bytes(
                    frames_bytes[0], width, height, compress=False
                )
                file_path.write_bytes(bm_data)

            return file_path
        else:
            # Анимированная иконка: папка + кадры + meta
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
                        frame_data, width, height, compress=False
                    )
                    frame_path.write_bytes(bm_data)

            return output_folder