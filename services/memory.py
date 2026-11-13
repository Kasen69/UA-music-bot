"""Утиліти оптимізації оперативної пам'яті для контейнерів (Render, Koyeb)."""

import gc
import logging

logger = logging.getLogger(__name__)


def free_memory():
    """
    Примусово збирає сміття в Python та повертає вільні сторінки пам'яті
    ядру операційної системи Linux через malloc_trim.
    """
    gc.collect()
    try:
        import ctypes
        libc = ctypes.CDLL("libc.so.6")
        libc.malloc_trim(0)
    except Exception:
        # На Windows або системах без glibc malloc_trim відсутній
        pass
