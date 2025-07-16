#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
"""State of ReActAgent"""
from typing import Optional, List

from pydantic import BaseModel, Field

from jiuwen.controller.common.sub_task import SubTask
from jiuwen.controller.common.enum import ReActStatus
from jiuwen.core.utils.llm.messages import BaseMessage


class ReActState(BaseModel):
    current_iteration: int = Field(default=0)
    final_result: str = Field(default="")
    llm_output: Optional[BaseMessage] = Field(default=None)
    sub_tasks: List[SubTask] = Field(default_factory=list)
    status: ReActStatus = Field(default=ReActStatus.INIT)
