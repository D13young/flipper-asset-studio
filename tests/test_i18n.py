"""Консистентность локализации (I1):
- RU и EN словари содержат одинаковые ключи;
- каждый ключ, используемый в коде через tr()/trf(), присутствует в обоих словарях;
- плейсхолдеры {param} в значениях RU/EN совпадают (trf не должен падать).
"""
import re
import unittest
from pathlib import Path

from ui.i18n import STRINGS, LANG_RU, LANG_EN, tr, set_language


ROOT = Path(__file__).resolve().parent.parent
SOURCE_GLOB = ["ui/*.py", "core/*.py", "main.py"]


def _keys_used_in_code() -> set[str]:
    keys: set[str] = set()
    for glob in SOURCE_GLOB:
        for path in ROOT.glob(glob):
            text = path.read_text(encoding="utf-8")
            # tr("key") и trf(\n  "key", ...) — включая многострочные вызовы
            for m in re.finditer(r'trf?\(\s*"([^"]+)"', text, re.S):
                keys.add(m.group(1))
    return keys


def _placeholders(value: str) -> set[str]:
    return set(re.findall(r"\{(\w+)\}", value))


class I18nConsistencyTest(unittest.TestCase):
    def test_ru_en_key_parity(self):
        self.assertEqual(
            set(STRINGS[LANG_RU].keys()),
            set(STRINGS[LANG_EN].keys()),
            "RU и EN словари должны содержать одинаковые ключи",
        )

    def test_all_code_keys_present_in_both_dicts(self):
        missing_ru = sorted(_keys_used_in_code() - set(STRINGS[LANG_RU]))
        missing_en = sorted(_keys_used_in_code() - set(STRINGS[LANG_EN]))
        self.assertEqual(missing_ru, [], f"Нет ключей в RU словаре: {missing_ru}")
        self.assertEqual(missing_en, [], f"Нет ключей в EN словаре: {missing_en}")

    def test_placeholders_match_between_languages(self):
        for key in STRINGS[LANG_RU]:
            ru = STRINGS[LANG_RU][key]
            en = STRINGS[LANG_EN][key]
            self.assertEqual(
                _placeholders(ru), _placeholders(en),
                f"Плейсхолдеры не совпадают для ключа '{key}'",
            )

    def test_no_english_only_values_in_ru(self):
        # Ключевые строки навигации/интерфейса обязаны быть переведены на русский
        # (не должны совпадать с английскими значениями).
        for key in ("nav.create", "nav.icons", "tab.animation", "tb.import",
                    "tb.export", "anim.btn_add", "val.btn_validate", "dlg.error"):
            self.assertNotEqual(
                STRINGS[LANG_RU][key], STRINGS[LANG_EN][key],
                f"Значение '{key}' в RU словаре не переведено",
            )

    def test_fallback_tr_returns_ru(self):
        set_language(LANG_RU)
        self.assertEqual(tr("nav.create"), STRINGS[LANG_RU]["nav.create"])
        self.assertEqual(tr("no_such_key_xyz"), "no_such_key_xyz")


if __name__ == "__main__":
    unittest.main()