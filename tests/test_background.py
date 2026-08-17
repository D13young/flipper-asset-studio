"""Тесты фонового исполнителя BackgroundRunner (A2).

Требует QApplication (гоняем в offscreen). Проверяет, что результат и ошибка
доставляются в поток UI, и что поток корректно завершается.
"""
import os
import sys
import time
import threading
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication

from ui.background import BackgroundRunner


def _spin(pred, timeout=8.0):
    loop = QEventLoop()
    deadline = time.time() + timeout
    timer = QTimer()
    timer.timeout.connect(
        lambda: loop.quit() if pred() or time.time() > deadline else None
    )
    timer.start(15)
    loop.exec()
    timer.stop()
    return pred()


class BackgroundRunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication(sys.argv)

    def _spin_run(self, fn, *, args=(), kwargs=None):
        runner = BackgroundRunner()
        done = []
        errs = []
        runner.run(fn, on_done=lambda r: done.append(r),
                   on_error=lambda m: errs.append(m), args=args, kwargs=kwargs)
        _spin(lambda: done or errs)
        runner.shutdown()
        return done, errs

    def test_result_delivered(self):
        done, errs = self._spin_run(lambda: 42)
        self.assertEqual(done, [42])
        self.assertEqual(errs, [])

    def test_worker_thread_is_not_ui_thread(self):
        seen_thread = []

        def job():
            import threading
            seen_thread.append(threading.current_thread())
            return "ok"

        done, _ = self._spin_run(job)
        self.assertEqual(done, ["ok"])
        self.assertTrue(seen_thread)
        self.assertIsNot(seen_thread[0], threading.main_thread())

    def test_error_delivered(self):
        done, errs = self._spin_run(lambda: 1 / 0)
        self.assertEqual(done, [])
        self.assertTrue(errs and "ZeroDivisionError" in errs[0])

    def test_args_kwargs_passed(self):
        done, _ = self._spin_run(
            lambda a, b: a + b, args=(2,), kwargs={"b": 3}
        )
        self.assertEqual(done, [5])

    def test_multiple_sequential_jobs(self):
        runner = BackgroundRunner()
        results = []
        for i in range(3):
            runner.run(lambda i=i: i * 10, on_done=lambda r: results.append(r))
        _spin(lambda: len(results) == 3)
        runner.shutdown()
        self.assertEqual(sorted(results), [0, 10, 20])


if __name__ == "__main__":
    unittest.main()