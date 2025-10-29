import asyncio
from dataclasses import dataclass
from typing import Optional, Callable, Any


@dataclass
class ProcessTask:

    task_id: str
    message: Any  # message object
    handler: Callable  # функция обработчик
    priority: int = 0


class ProcessQueue:

    def __init__(self, min_delay: float = 3.0):
        self.queue = asyncio.Queue()
        self.min_delay = min_delay
        self.is_running = False
        self.worker_task = None
        self.current_task = None

    async def start(self):
        if not self.is_running:
            self.is_running = True
            self.worker_task = asyncio.create_task(self._worker())
            print("🔄 Очередь обработки запущена (последовательный режим)")

    async def stop(self):
        self.is_running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

    async def add(self, task: ProcessTask):
        await self.queue.put(task)
        doc = task.message.document
        print(
            f"📥 В очередь: {doc.file_name} ({doc.file_size / 1024 / 1024:.1f} МБ) | Позиция: {self.queue.qsize()}"
        )

    def get_queue_size(self) -> int:
        return self.queue.qsize()

    async def _worker(self):
        print("🚀 Воркер запущен")

        while self.is_running:
            try:
                try:
                    task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                self.current_task = task
                doc = task.message.document

                print(f"\n{'='*60}")
                print(f"🔨 Начало обработки: {doc.file_name}")
                print(f"📊 Размер: {doc.file_size / 1024 / 1024:.1f} МБ")
                print(f"📦 В очереди: {self.queue.qsize()}")
                print(f"{'='*60}\n")

                try:
                    await task.handler(task.message)
                except Exception as e:
                    print(f"❌ Ошибка обработки {doc.file_name}: {e}")

                print(f"\n✅ Завершено: {doc.file_name}\n")

                if self.queue.qsize() > 0:
                    print(f"⏳ Пауза {self.min_delay}с перед следующим...")
                    await asyncio.sleep(self.min_delay)

                self.current_task = None
                self.queue.task_done()

            except asyncio.CancelledError:
                print("⏹️ Воркер остановлен")
                break
            except Exception as e:
                print(f"❌ Критическая ошибка в воркере: {e}")
                self.current_task = None
                await asyncio.sleep(1)


process_queue: Optional[ProcessQueue] = None


def init_process_queue(min_delay: float = 3.0) -> ProcessQueue:
    global process_queue
    process_queue = ProcessQueue(min_delay)
    return process_queue


def get_process_queue() -> ProcessQueue:
    if process_queue is None:
        raise RuntimeError("Очередь не инициализирована")
    return process_queue
