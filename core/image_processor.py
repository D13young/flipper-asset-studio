import numpy as np
from PIL import Image, ImageSequence
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt
from typing import Optional, Dict, Any
from pathlib import Path
from numpy.typing import NDArray


class FlipperImageProcessor:
    VALID_ICON_SIZES = {
        (10, 10), (12, 12), (14, 14), (16, 16),
        (32, 32), (46, 49), (64, 64), (97, 61), (128, 64)
    }

    """Обработчик изображений под спецификацию Flipper Zero."""

    WIDTH = 128

    HEIGHT = 64
    BYTES_PER_FRAME = (WIDTH * HEIGHT) // 8

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
    def preprocess(
        cls,
        img: Image.Image,
        dither_level: int = 1,
        *,
        output_w: int | None = None,
        output_h: int | None = None,
    ) -> Image.Image:

        w = cls.WIDTH if output_w is None else int(output_w)
        h = cls.HEIGHT if output_h is None else int(output_h)

        img = img.convert("RGBA")
        img.thumbnail((w, h), Image.Resampling.LANCZOS)

        canvas = Image.new("L", (w, h), 0)
        img_l = img.convert("L")
        offset_x = (w - img_l.width) // 2
        offset_y = (h - img_l.height) // 2
        canvas.paste(img_l, (offset_x, offset_y))



        dither_level = int(dither_level)
        if dither_level <= 0:
            mode = Image.Dither.NONE
        else:
            mode = Image.Dither.FLOYDSTEINBERG

        return canvas.convert("1", dither=mode)

    @classmethod
    def pack_to_flipper_bytes(
        cls,
        img_1bit: Image.Image,
        *,
        output_w: int | None = None,
        output_h: int | None = None,
    ) -> bytes:
        """Упаковка 1-бит изображения в bytes Flipper (LSB-first, white=1) под output_w x output_h.

        Первый пиксель строки — младший бит байта (LSB-first).
        """
        w = cls.WIDTH if output_w is None else int(output_w)
        h = cls.HEIGHT if output_h is None else int(output_h)

        arr = np.array(img_1bit, dtype=np.uint8)
        arr = (arr > 0).astype(np.uint8)

        arr2 = arr.reshape(h, w)
        packed = np.packbits(arr2, axis=1, bitorder="little")
        return packed.tobytes()


    @classmethod
    def bytes_to_preview(
        cls,
        data: bytes,
        width: int | None = None,
        height: int | None = None,
        scale: int = 3,
        *,
        bitorder: str = "little",
        invert_bits: bool = False,
    ) -> QPixmap:

        """Конвертация сырых байтов Flipper → QPixmap для GUI."""
        
        w = cls.WIDTH if width is None else int(width)
        h = cls.HEIGHT if height is None else int(height)

        row_bytes = (w + 7) // 8
        expected_bytes = row_bytes * h

        raw = np.frombuffer(data, dtype=np.uint8)
        if raw.size < expected_bytes:
            raw = np.concatenate([raw, np.zeros(expected_bytes - raw.size, dtype=raw.dtype)])
        elif raw.size > expected_bytes:
            raw = raw[:expected_bytes]

        bits = np.unpackbits(raw.reshape(h, row_bytes), axis=1, bitorder=bitorder)[:, :w]
        if invert_bits:
            bits = 1 - bits

        img_bytes = (bits * 255).astype(np.uint8).tobytes()
        qimg = QImage(img_bytes, w, h, w, QImage.Format.Format_Grayscale8)

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
        """Упаковка матрицы 0/1 в bytes Flipper (LSB-first, white=1) для произвольных w/h."""
        w = cls.WIDTH if width is None else int(width)
        h = cls.HEIGHT if height is None else int(height)

        arr = np.array(pixels, dtype=np.uint8)
        if arr.shape != (h, w):
            raise ValueError(f"Invalid pixels shape: expected {(h, w)}, got {arr.shape}")

        arr = (arr > 0).astype(np.uint8)
        packed = np.packbits(arr, axis=1, bitorder="little")
        return packed.tobytes()

    @classmethod
    def _png_to_bytes(
        cls,
        img: Image.Image,
        dither_level: int,
        output_w: int | None,
        output_h: int | None,
    ) -> bytes:
        img_1bit = cls.preprocess(
            img,
            dither_level=dither_level,
            output_w=output_w,
            output_h=output_h,
        )
        return cls.pack_to_flipper_bytes(
            img_1bit,
            output_w=output_w,
            output_h=output_h,
        )

    @classmethod
    def process_png_to_bytes(
        cls,
        path: str,
        dither_level: int = 1,
        *,
        output_w: int | None = None,
        output_h: int | None = None,
    ) -> bytes:
        return cls._png_to_bytes(
            cls.load_and_validate(path), int(dither_level), output_w, output_h
        )

    @classmethod
    def process_png(
        cls,
        path: str,
        dither_level: int = 1,
        *,
        output_w: int | None = None,
        output_h: int | None = None,
    ) -> Dict[str, Any]:
        img = cls.load_and_validate(path)
        raw_bytes = cls._png_to_bytes(img, int(dither_level), output_w, output_h)

        w = cls.WIDTH if output_w is None else int(output_w)
        h = cls.HEIGHT if output_h is None else int(output_h)
        preview = cls.bytes_to_preview(raw_bytes, width=w, height=h)
        return {
            "original_size": img.size,
            "processed_size": (w, h),
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

        del mode

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

    # ---------------- GIF crop/export ----------------

    @classmethod
    def export_gif_frames_custom_crop_to_png(
        cls,
        *,
        input_path: str,
        output_dir: str,
        output_w: int,
        output_h: int,
        crop_left: int,
        crop_top: int,
        crop_right: int,
        crop_bottom: int,
        mode: str = "center_crop",
    ) -> list[Path]:

        del mode

        p = Path(input_path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {input_path}")
        if p.suffix.lower() != ".gif":
            raise ValueError(f"Файл не является GIF: {input_path}")

        out_dir_p = Path(output_dir)
        out_dir_p.mkdir(parents=True, exist_ok=True)

        img = Image.open(p)
        if img.width == 0 or img.height == 0:
            img.close()
            raise ValueError("GIF has zero size")

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
            img.close()
            raise ValueError("Invalid crop rect: too small")

        saved: list[Path] = []
        try:
            for index, frame in enumerate(ImageSequence.Iterator(img)):
                frame = frame.convert("RGBA")

                if frame.size != (src_w, src_h):
                    frame = frame.resize((src_w, src_h), Image.Resampling.BILINEAR)

                cropped = frame.crop((l, t, r, b))

                out_img = cls._crop_and_resize_to_target(
                    cropped,
                    output_w,
                    output_h,
                    mode="contain",
                )

                out_path = out_dir_p / f"{p.stem}_{int(output_w)}x{int(output_h)}_{index:03d}.png"
                out_img.convert("RGBA").save(out_path, format="PNG")
                saved.append(out_path)
        finally:
            img.close()

        return saved