import struct
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

        # output_folder обязан быть путём (Path/str), а не результатом process_png.
        # Если снаружи прилетает dict — это ошибка прокидывания аргументов.
        if isinstance(output_folder, dict):
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

            # Если для passport static есть исходные PNG пути — делаем точный pipeline
            # Momentum: Pillow.convert("1") -> ImageOps.invert -> save(..., format="XBM")
            # и только потом собираем .bm/.bmx через уже существующие конверторы.
            if frames_paths and len(frames_paths) == 1:
                png_path = frames_paths[0]
                img = FlipperImageProcessor.load_and_validate(png_path)
                # Применяем dither как в UI/процессинге: 0 => без дизеринга
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

                # asset_packer convert_bm делает heatshrink поверх XBM bytes
                bm_data = FlipperExporter._xbm_bytes_to_bm(xbm_bytes, compress=True)
                if compress:
                    # .bmx контейнер: header(<II) + convert_bm output
                    bmx_data = struct.pack("<II", width, height) + bm_data
                    file_path.write_bytes(bmx_data)
                else:
                    file_path.write_bytes(bm_data)

                return file_path

            # fallback: старый путь (через уже упакованные bytes)
            if compress:
                bmx_data = FlipperExporter._make_bmx_from_bytes(
                    frames_bytes[0], width, height, compress=True
                )
                file_path.write_bytes(bmx_data)
            else:
                # Momentum expects .bm payload to be heatshrink-compressed (flag=0x01)
                bm_data = FlipperExporter._make_bm_from_bytes(
                    frames_bytes[0], width, height, compress=True
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
                    # Momentum expects .bm payload to be heatshrink-compressed (flag=0x01)
                    bm_data = FlipperExporter._make_bm_from_bytes(
                        frame_data, width, height, compress=True
                    )
                    frame_path.write_bytes(bm_data)

            return output_folder