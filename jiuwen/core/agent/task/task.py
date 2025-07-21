import uuid
from typing import Any, Dict, Optional, List, Union

from pydantic import BaseModel, Field

from jiuwen.agent.common.enum import SubTaskType, TaskStatus


class SubTask(BaseModel):
    id: str = Field(default="")
    sub_task_type: SubTaskType = Field(default=SubTaskType.UNDEFINED)
    func_name: str = Field(default="")
    func_args: dict = Field(default_factory=dict)
    result: Optional[str] = Field(default=None)


class Task:
    def __init__(self, payload: Dict[str, Any], task_id: Optional[str] = None):
        self.id: str = task_id or str(uuid.uuid4())
        self.payload: Dict[str, Any] = payload
        self.sub_tasks: List[SubTask] = []
        self.status: TaskStatus = TaskStatus.PENDING

    def add_sub_task(self, sub_task: SubTask) -> str:
        if not sub_task.id:  # 若调用方没给 id，自动生成
            sub_task.id = f"{self.id}_{len(self.sub_tasks)}"
        self.sub_tasks.append(sub_task)
        return sub_task.id
