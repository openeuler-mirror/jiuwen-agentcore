import threading
from typing import Dict, Any, Optional

from jiuwen.agent.common.enum import TaskStatus
from jiuwen.core.agent.task.task import Task


class TaskManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._tasks: Dict[str, Task] = {}

    def submit(self, payload: Dict[str, Any], task_id: Optional[str] = None) -> str:
        with self._lock:
            task = Task(payload, task_id)
            self._tasks[task.id] = task
            return task.id

    def get(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def update_status(self, task_id: str, status: TaskStatus) -> None:
        with self._lock:
            t = self._tasks.get(task_id)
            if t:
                t.status = status
