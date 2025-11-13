import asyncio
from dataclasses import dataclass, field
from typing import Callable, Optional
from aiogram.types import Message


@dataclass
class ProcessTask:
    task_id: str
    message: Message
    handler: Callable
    priority: int = 0
    timestamp: float = field(default_factory=lambda: asyncio.get_event_loop().time())


class ProcessQueue:
    def __init__(self, min_delay: float = 3.0):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.min_delay = min_delay
        self.current_task: Optional[ProcessTask] = None
        self.is_running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def add(self, task: ProcessTask):
        await self.queue.put(task)

        print(f"➕ Задача добавлена в очередь: {task.message.document.file_name}")
        print(f"📊 Размер очереди: {self.queue.qsize()}")

    def get_queue_size(self) -> int:
        return self.queue.qsize()

    async def _worker(self):
        print("🔄 Воркер очереди запущен")

        while self.is_running:
            try:
                task = await self.queue.get()

                async with self._lock:
                    self.current_task = task
                    file_name = task.message.document.file_name

                    print(f"\n{'='*60}")
                    print(f"🔄 Начинаем обработку: {file_name}")
                    print(f"📊 Осталось в очереди: {self.queue.qsize()}")
                    print(f"{'='*60}\n")

                    try:
                        await task.handler(task.message)
                        print(f"\n✅ Завершено: {file_name}\n")

                    except Exception as e:
                        print(f"\n❌ Ошибка при обработке {file_name}: {e}\n")

                    finally:
                        self.current_task = None
                        self.queue.task_done()

                        if self.queue.qsize() > 0:
                            print(
                                f"⏳ Пауза {self.min_delay}с перед следующей задачей..."
                            )
                            await asyncio.sleep(self.min_delay)

            except asyncio.CancelledError:
                print("⚠️ Воркер остановлен")
                break
            except Exception as e:
                print(f"❌ Критическая ошибка в воркере: {e}")
                await asyncio.sleep(5)

    async def start(self):
        if self.is_running:
            print("⚠️ Очередь уже запущена")
            return

        self.is_running = True
        self._worker_task = asyncio.create_task(self._worker())
        print("✅ Очередь запущена")

    async def stop(self):
        self.is_running = False

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        print("🛑 Очередь остановлена")

    async def wait_completion(self):
        await self.queue.join()


_global_queue: Optional[ProcessQueue] = None


def init_process_queue(min_delay: float = 3.0) -> ProcessQueue:
    global _global_queue
    _global_queue = ProcessQueue(min_delay=min_delay)
    return _global_queue


def get_process_queue() -> ProcessQueue:
    if _global_queue is None:
        raise RuntimeError()
    return _global_queue
