#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field


class WorkflowMetadata(BaseModel):
    name: str = Field(default="")
    id: str = Field(default="")
    version: str = Field(default="")


class WorkflowConfig(BaseModel):
    metadata: Optional[WorkflowMetadata] = Field(default=None)
    comp_configs: Dict[str, Any] = Field(default_factory=dict)
    stream_edges: Dict[str, List[str]] = Field(default_factory=dict)
