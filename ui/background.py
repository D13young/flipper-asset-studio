from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot


class _Bridge(QObject):
    """Живёт в потоке UI: через него к нам из воркера приходят результаты
    (QueuedConnection), чтобы колбэки гарантированно выполнялись в UI-потоке."""

    done = pyqtSignal(object)
    err = pyqtSignal(str)


class _Worker(QObject):
    done = pyqtSignal(object)
    err = pyqtSignal(str)

    def __init__(self, fn, args, kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    @pyqtSlot()
    def run(self):
        try:
            self.done.emit(self._fn(*self._args, **self._kwargs))
        except Exception as e:  # noqa: BLE001 - показываем ошибку пользователю
            self.err.emit(f"{type(e).__name__}: {e}")


class BackgroundRunner:
    """Запускает fn(*args, **kwargs) в отдельном потоке.

    on_done(result) — успешное завершение;
    on_error(message) — исключение (опционально).
    Оба колбэка вызываются в потоке UI: сигналы воркера прогоняются через
    внутренний _Bridge (QueuedConnection). Ссылки на (thread, worker)
    удерживаются до завершения задачи, иначе GC удалит worker раньше
    запуска потока.
    """

    def __init__(self, parent=None):
        self._parent = parent
        self._jobs: set[tuple[QThread, _Worker, _Bridge]] = set()

    def run(self, fn, on_done, on_error=None, args=(), kwargs=None):
        thread = QThread(self._parent)
        worker = _Worker(fn, tuple(args), dict(kwargs or {}))
        bridge = _Bridge(self._parent)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        def _finish(*_):
            self._jobs.discard((thread, worker, bridge))
            thread.quit()

        worker.done.connect(bridge.done)
        bridge.done.connect(on_done)
        bridge.done.connect(_finish)
        worker.err.connect(bridge.err)
        if on_error is not None:
            bridge.err.connect(on_error)
        bridge.err.connect(_finish)

        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(bridge.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._jobs.add((thread, worker, bridge))
        thread.start()

    def shutdown(self):
        """Останавливает все запущенные потоки (вызывается при закрытии окна)."""
        for thread, _worker, _bridge in list(self._jobs):
            thread.quit()
            thread.wait(2000)
        self._jobs.clear()
