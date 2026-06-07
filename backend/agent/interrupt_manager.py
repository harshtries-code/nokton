import asyncio


class InterruptError(Exception):
    pass


class InterruptManager:
    def __init__(self):
        self._interrupt = asyncio.Event()
        self._current_stream = None

    def cancel(self):
        self._interrupt.set()
        if self._current_stream is not None:
            try:
                stream = self._current_stream
                if hasattr(stream, "aclose"):
                    aclose = stream.aclose()
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            loop.create_task(aclose)
                    except Exception:
                        pass
                elif hasattr(stream, "close"):
                    stream.close()
                elif hasattr(stream, "response") and hasattr(stream.response, "close"):
                    stream.response.close()
            except Exception:
                pass

    def reset(self):
        self._interrupt.clear()
        self._current_stream = None

    def check(self):
        if self._interrupt.is_set():
            raise InterruptError("Operation cancelled by user.")

    def set_current_stream(self, stream):
        self._current_stream = stream

    @property
    def is_interrupted(self) -> bool:
        return self._interrupt.is_set()
