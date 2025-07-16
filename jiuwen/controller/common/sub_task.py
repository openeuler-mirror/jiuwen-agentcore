#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
"""sub-task constants"""

from pydantic import BaseModel, Field

from jiuwen.controller.common.enum import SubTaskType


class SubTask(BaseModel):
    id: str = Field(default="")
    sub_task_type: SubTaskType = Field(default=SubTaskType.UNDEFINED)
    func_name: str = Field(default="")
    func_args: dict = Field(default_factory=dict)
