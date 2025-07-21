from typing import Any, Optional

from pydantic import BaseModel, Field

from jiuwen.agent.common.enum import SubTaskType


class SubTask(BaseModel):
    id: str = Field(default="")
    sub_task_type: SubTaskType = Field(default=SubTaskType.UNDEFINED)
    func_id: str = Field(default="")
    func_name: str = Field(default="")
    func_args: dict = Field(default_factory=dict)
    result: Optional[str] = Field(default=None)
    sub_task_context: Any = Field(default=None)
