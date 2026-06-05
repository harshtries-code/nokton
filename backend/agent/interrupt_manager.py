import asyncio
import threading


class InterruptError(Exception):
    pass


class InterruptManager:
    def __init__(self):
        self._interrupt = threading.Event()
        self._current_task: asyncio.Task | None = None
        self._current_stream = None

    def cancel(self):
        self._interrupt.set()
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
        if self._current_stream:
            try:
                self._current_stream.close()
            except Exception:
                pass

    def reset(self):
        self._interrupt.clear()
        self._current_task = None
        self._current_stream = None

    def check(self):
        if self._interrupt.is_set():
            raise InterruptError("Operation cancelled by user.")

    def set_current_task(self, task: asyncio.Task):
        self._current_task = task

    def set_current_stream(self, stream):
        self._current_stream = stream

    @property
    def is_interrupted(self) -> bool:
        return self._interrupt.is_set()
