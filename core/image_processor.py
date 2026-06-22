import numpy as np
from PIL import Image
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt
from typing import Optional, Dict, Any
from pathlib import Path
from numpy.typing import NDArray


class FlipperImageProcessor:
    # Фиксированные размеры берутся из валидатора (используются и для UI JPG crop)
    VALID_ICON_SIZES = {
        (10, 10), (12, 12), (14, 14), (16, 16),
        (32, 32), (46, 49), (64, 64), (97, 61), (128, 64)
    }

    """Обработчик изображений под спецификацию Flipper Zero."""

    # В некоторых валидных bm/bmx (или конкретных пайплайнах экспорта) порядок бит внутри байта
    # может быть инвертирован относительно numpy.pack/unpackbits.
    # Включено для устранения «строчных/побитовых» артефактов на предпросмотре.
    REVERSE_BITS_WITHIN_BYTE = False

    WIDTH = 128

    HEIGHT = 64
    BYTES_PER_FRAME = (WIDTH * HEIGHT) // 8  # 1024 байта

    @classmethod
    def load_and_validate(cls, path: str) -> Optional[Image.Image]:
        p = Path(path)
        if not p.exists() or p.suffix.lower() != ".png":
            raise ValueError(f"Файл не найден или не является PNG: {path}")

        try:
            img = Image.open(p).convert("RGBA")
            if img.width == 0 or img.height == 0:
                raise ValueError("Изображение пустое")
            return img
        except Exception as e:
            raise RuntimeError(f"Ошибка чтения изображения: {e}") from e

    @classmethod
    def preprocess(cls, img: Image.Image, dither_level: int = 1) -> Image.Image:
        """Центрирование, ресайз/кроп и конвертация в 1-бит под 128x64.

        dither_level:

          0 = без дизеринга
          1 = Floyd-Steinberg
          2/3 = сейчас (в зависимости от Pillow) трактуются как Floyd-Steinberg,
              чтобы обеспечить наличие “уровня” в UI. Алгоритмы/силу можно расширить позже.
        """

        img.thumbnail((cls.WIDTH, cls.HEIGHT), Image.Resampling.LANCZOS)

        canvas = Image.new("L", (cls.WIDTH, cls.HEIGHT), 0)
        offset_x = (cls.WIDTH - img.width) // 2
        offset_y = (cls.HEIGHT - img.height) // 2
        canvas.paste(img, (offset_x, offset_y))

        dither_level = int(dither_level)
        if dither_level <= 0:
            mode = Image.Dither.NONE
        else:
            # Pillow пока не даёт “силу” Floyd-Steinberg как параметр.
            # Используем Floyd-Steinberg для уровней 1..3.
            mode = Image.Dither.FLOYDSTEINBERG

        return canvas.convert("1", dither=mode)

    @classmethod
    def pack_to_flipper_bytes(cls, img_1bit: Image.Image) -> bytes:
        """Упаковка 1-бит изображения в bytes Flipper (MSB-first, white=1)."""
        arr = np.array(img_1bit, dtype=np.uint8)
        arr = (arr > 0).astype(np.uint8)  # 0/1, white=1

        arr2 = arr.reshape(cls.HEIGHT, cls.WIDTH)
        packed = np.packbits(arr2, axis=1, bitorder="big")
        return packed.tobytes()

    @classmethod
    def pack_to_xbm_bytes(cls, img_1bit: Image.Image) -> bytes:
        """Упаковка 1-бит изображения в XBM-формат как в asset_packer.py.

        Формат как в convert_bm:
        - Чёрный пиксель = 1, белый = 0
        - MSB-first within byte (пиксель 0 = бит 7 байта 0)
        - Scanlines packed: byte 0 = pixels 0-7, byte 1 = pixels 8-15, ...
        """
        arr = np.array(img_1bit, dtype=np.uint8)
        # img_1bit: white=255/True, black=0/False
        # XBM (через ImageOps.invert): black=1, white=0
        arr = (arr == 0).astype(np.uint8)  # black(0/False) -> 1, white(255/True) -> 0
        arr = arr.reshape(-1, cls.WIDTH)
        packed = np.packbits(arr, axis=1, bitorder="big")
        return packed.tobytes()

    @classmethod
    def bytes_to_preview(
        cls,
        data: bytes,
        width: int | None = None,
        height: int | None = None,
        scale: int = 3,
        *,
        bitorder: str = "big",
        invert_bits: bool = False,
    ) -> QPixmap:

        """Конвертация сырых байтов Flipper → QPixmap для GUI.

        Для произвольных width/height нужно, чтобы в data были байты/битсет под эту сетку.
        """
        w = cls.WIDTH if width is None else int(width)
        h = cls.HEIGHT if height is None else int(height)

        raw = np.frombuffer(data, dtype=np.uint8)
        bits = np.unpackbits(raw, bitorder=bitorder)
        if invert_bits:
            bits = 1 - bits

        # Часто у Flipper packed-битов встречается реверс внутри каждого байта.
        # При «горизонтальных» артефактах это может быть единственной верной правкой.
        if getattr(cls, "REVERSE_BITS_WITHIN_BYTE", False):
            bits = bits.reshape(-1, 8)[:, ::-1].reshape(-1)

        expected_bits = h * w

        if bits.size < expected_bits:
            raise ValueError(
                f"Invalid data length for preview: need {expected_bits} bits, got {bits.size} bits"
            )

        bits = bits[:expected_bits].reshape(h, w)

        img_bytes = (bits * 255).astype(np.uint8).tobytes()
        qimg = QImage(img_bytes, w, h, QImage.Format.Format_Grayscale8)

        # Строго в размер: без KeepAspectRatio, чтобы не терялись края.
        return QPixmap.fromImage(qimg).scaled(
            w * scale,
            h * scale,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

    @classmethod
    def pack_pixels_to_flipper_bytes(
        cls,
        pixels: "NDArray[np.uint8] | NDArray[np.bool_] | list[list[int]]",
        width: int | None = None,
        height: int | None = None,
    ) -> bytes:
        """Упаковка матрицы 0/1 в bytes Flipper (MSB-first, white=1) для произвольных w/h."""
        w = cls.WIDTH if width is None else int(width)
        h = cls.HEIGHT if height is None else int(height)

        arr = np.array(pixels, dtype=np.uint8)
        if arr.shape != (h, w):
            raise ValueError(f"Invalid pixels shape: expected {(h, w)}, got {arr.shape}")

        arr = (arr > 0).astype(np.uint8)
        packed = np.packbits(arr, axis=1, bitorder="big")
        return packed.tobytes()

    @classmethod
    def pack_pixels_to_xbm_bytes(
        cls,
        pixels: "NDArray[np.uint8] | NDArray[np.bool_] | list[list[int]]",
        width: int | None = None,
        height: int | None = None,
    ) -> bytes:
        """Упаковка матрицы 0/1 в XBM-формат (black=1, white=0, MSB-first) для произвольных w/h."""
        w = cls.WIDTH if width is None else int(width)
        h = cls.HEIGHT if height is None else int(height)

        arr = np.array(pixels, dtype=np.uint8)
        if arr.shape != (h, w):
            raise ValueError(f"Invalid pixels shape: expected {(h, w)}, got {arr.shape}")

        # XBM: 1 = black (pixel value 0), 0 = white (pixel value 1)
        arr = (arr == 0).astype(np.uint8)
        packed = np.packbits(arr, axis=1, bitorder="big")
        return packed.tobytes()

    @classmethod
    def pack_pixels_to_flipper(
        cls,
        pixels: "NDArray[np.uint8] | NDArray[np.bool_] | list[list[int]]",
        width: int | None = None,
        height: int | None = None,
        scale: int = 3,
    ) -> Dict[str, Any]:
        w = cls.WIDTH if width is None else int(width)
        h = cls.HEIGHT if height is None else int(height)
        raw_bytes = cls.pack_pixels_to_flipper_bytes(pixels, width=w, height=h)
        preview = cls.bytes_to_preview(raw_bytes, width=w, height=h, scale=scale)
        return {
            "processed_size": (w, h),
            "byte_length": len(raw_bytes),
            "bytes": raw_bytes,
            "preview": preview,
        }

    @classmethod
    def process_png(cls, path: str, dither_level: int = 1) -> Dict[str, Any]:
        img = cls.load_and_validate(path)
        img_1bit = cls.preprocess(img, dither_level=dither_level)

        raw_bytes = cls.pack_to_flipper_bytes(img_1bit)
        preview = cls.bytes_to_preview(raw_bytes, width=cls.WIDTH, height=cls.HEIGHT)
        return {
            "original_size": img.size,
            "processed_size": (cls.WIDTH, cls.HEIGHT),
            "byte_length": len(raw_bytes),
            "bytes": raw_bytes,
            "preview": preview,
            "dither_level": int(dither_level),
        }


    # ---------------- JPG crop/export ----------------

    @classmethod
    def _load_image_any(cls, path: str) -> Image.Image:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {path}")

        try:
            img = Image.open(p)
            if img.width == 0 or img.height == 0:
                raise ValueError("Image has zero size")
            return img.convert("RGBA")
        except Exception as e:
            raise RuntimeError(f"Failed to load image: {e}") from e
        if not p.exists():
            raise FileNotFoundError(f"File not found: {path}")

        try:
            img = Image.open(p)
            if img.width == 0 or img.height == 0:
                raise ValueError("Image has zero size")
            return img.convert("RGBA")
        except Exception as e:
            raise RuntimeError(f"Failed to load image: {e}") from e

    @classmethod
    def _crop_and_resize_to_target(
        cls,
        img: Image.Image,
        output_w: int,
        output_h: int,
        *,
        mode: str = "center_crop",
    ) -> Image.Image:
        output_w = int(output_w)
        output_h = int(output_h)
        if output_w <= 0 or output_h <= 0:
            raise ValueError("output_w/output_h must be > 0")

        mode = str(mode)
        if mode not in {"center_crop", "contain"}:
            raise ValueError("mode must be one of: center_crop, contain")

        src_w, src_h = img.size
        if src_w <= 0 or src_h <= 0:
            raise ValueError("Invalid source image size")

        src_ratio = src_w / src_h
        dst_ratio = output_w / output_h

        if mode == "center_crop":
            if src_ratio > dst_ratio:
                scale = output_h / src_h
            else:
                scale = output_w / src_w

            new_w = max(1, int(round(src_w * scale)))
            new_h = max(1, int(round(src_h * scale)))
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            left = (new_w - output_w) // 2
            top = (new_h - output_h) // 2
            return resized.crop((left, top, left + output_w, top + output_h)).convert("RGBA")

        scale = min(output_w / src_w, output_h / src_h)
        new_w = max(1, int(round(src_w * scale)))
        new_h = max(1, int(round(src_h * scale)))
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        canvas = Image.new("RGBA", (output_w, output_h), (0, 0, 0, 255))
        offset_x = (output_w - new_w) // 2
        offset_y = (output_h - new_h) // 2
        canvas.paste(resized, (offset_x, offset_y))
        return canvas

    @classmethod
    def preview_crop(
        cls,
        input_path: str,
        output_w: int,
        output_h: int,
        *,
        mode: str = "center_crop",
        scale: int = 3,
    ) -> QPixmap:
        img = cls._load_image_any(input_path)
        out_img = cls._crop_and_resize_to_target(img, output_w, output_h, mode=mode)

        qimg = QImage(out_img.tobytes("raw", "RGBA"), out_img.size[0], out_img.size[1], QImage.Format.Format_RGBA8888)
        pm = QPixmap.fromImage(qimg)
        return pm.scaled(
            int(output_w) * scale,
            int(output_h) * scale,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

    @classmethod
    def export_jpg_custom_crop_to_png(
        cls,
        *,
        input_path: str,
        output_path: str,
        output_w: int,
        output_h: int,
        crop_left: int,
        crop_top: int,
        crop_right: int,
        crop_bottom: int,
        mode: str = "center_crop",
    ) -> Path:
        """Экспорт PNG по произвольному crop-rect исходного изображения.

        crop_left/crop_top/crop_right/crop_bottom — координаты в пикселях исходника.
        Далее результат ресайзится/вписывается в (output_w, output_h).

        Параметр mode оставлен для совместимости, но обрезка идет строго по crop-rect.
        """

        del mode  # обрезка строго по рамке

        img = cls._load_image_any(input_path)
        src_w, src_h = img.size

        l = int(crop_left)
        t = int(crop_top)
        r = int(crop_right)
        b = int(crop_bottom)

        if r < l:
            l, r = r, l
        if b < t:
            t, b = b, t

        l = max(0, min(src_w, l))
        r = max(0, min(src_w, r))
        t = max(0, min(src_h, t))
        b = max(0, min(src_h, b))

        if r - l < 1 or b - t < 1:
            raise ValueError("Invalid crop rect: too small")

        cropped = img.crop((l, t, r, b)).convert("RGBA")

        # Подгоняем cropped под target output_w/output_h.
        # center_crop/contain здесь определяет способ подгонки после crop.
        out_img = cls._crop_and_resize_to_target(
            cropped,
            output_w,
            output_h,
            mode="contain",
        )

        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_img.convert("RGBA").save(out_p, format="PNG")
        return out_p