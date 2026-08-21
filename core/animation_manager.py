from typing import List, Dict, Any
from core.image_processor import FlipperImageProcessor

class FlipperAnimationManager:
    def __init__(self):
        self.frames: List[Dict[str, Any]] = []
        self.meta_params = {
            "width": 128, "height": 64,
            "passive_frames": 0, "active_frames": 0,
            "frame_rate": 2, "duration": 3600,
            "active_cycles": 0, "active_cooldown": 0,

            "bubble_slots": 0
        }

    def add_frame(self, png_path: str, dither_level: int = 1):
        data = FlipperImageProcessor.process_png(png_path, dither_level=dither_level)

        self.frames.append({
            "path": png_path,
            "bytes": data["bytes"],
            "preview": data["preview"],
            "dither_level": int(dither_level),
        })
        self.meta_params["passive_frames"] = len(self.frames)

    def add_frame_bytes(self, png_path: str, flipper_bytes: bytes, dither_level: int = 1):
        """Добавить кадр с уже посчитанными bytes.

        Превью строится позже (в UI-потоке), т.к. QPixmap нельзя создавать
        в фоновом потоке. Используется асинхронным импортом кадров.
        """
        self.frames.append({
            "path": png_path,
            "bytes": flipper_bytes,
            "preview": None,
            "dither_level": int(dither_level),
        })
        self.meta_params["passive_frames"] = len(self.frames)

    def reprocess_frames_to_bytes(self, dither_level: int):
        """Пересчитать bytes для всех кадров (БЕЗ QPixmap).

        Возвращает список (path, bytes) для применения в UI-потоке.
        """
        dither_level = int(dither_level)
        out = []
        for f in self.frames:
            p = f.get("path")
            if not p:
                continue
            out.append(
                (p, FlipperImageProcessor.process_png_to_bytes(p, dither_level=dither_level))
            )
        return out

    def reprocess_frames(self, dither_level: int):
        """Пересчитать bytes/preview для всех текущих кадров с новым dither_level."""
        dither_level = int(dither_level)
        for f in self.frames:
            p = f.get("path")
            if not p:
                continue
            data = FlipperImageProcessor.process_png(p, dither_level=dither_level)
            f["bytes"] = data["bytes"]
            f["preview"] = data["preview"]
            f["dither_level"] = dither_level


    def move_frame(self, from_idx: int, to_idx: int):
        if 0 <= from_idx < len(self.frames) and 0 <= to_idx < len(self.frames):
            self.frames.insert(to_idx, self.frames.pop(from_idx))

    def remove_frame(self, idx: int):
        if 0 <= idx < len(self.frames):
            self.frames.pop(idx)
            self.meta_params["passive_frames"] = len(self.frames)

    def get_frame_bytes_list(self) -> List[bytes]:
        return [f["bytes"] for f in self.frames]

    def generate_meta_txt(self) -> str:
        frames_order = " ".join(str(i) for i in range(len(self.frames)))
        return f"""Filetype: Flipper Animation
Version: 1

Width: {self.meta_params['width']}
Height: {self.meta_params['height']}
Passive frames: {self.meta_params['passive_frames']}
Active frames: {self.meta_params['active_frames']}
Frames order: {frames_order}
Active cycles: {self.meta_params['active_cycles']}
Frame rate: {self.meta_params['frame_rate']}
Duration: {self.meta_params['duration']}
Active cooldown: {self.meta_params['active_cooldown']}

Bubble slots: {self.meta_params['bubble_slots']}"""

    def generate_manifest_txt(
        self,
        name: str,
        min_bh: int = 0,
        max_bh: int = 14,
        min_lv: int = 1,
        max_lv: int = 30,
        weight: int = 8,
    ) -> str:
        # Momentum ограничивает Max butthurt сверху — фиксируем поведение.
        max_bh = min(int(max_bh), 14)
        weight = int(weight)
        return f"""Filetype: Flipper Animation Manifest
Version: 1

Name: {name}
Min butthurt: {min_bh}
Max butthurt: {max_bh}
Min level: {min_lv}
Max level: {max_lv}
Weight: {weight}"""

