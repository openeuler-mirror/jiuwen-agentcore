#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
"""enum constants"""

from enum import Enum


class ControllerType(Enum):
    ReActController = "react"
    WorkflowController = "workflow"
    Undefined = "undefined"


class SubTaskType(Enum):
    PLUGIN = "plugin"
    WORKFLOW = "workflow"
    MCP = "mcp"
    UNDEFINED = "undefined"


class ReActStatus(Enum):
    INITIALIZED = "initialized"
    LLM_RESPONSE = "llm_response"
    TOOL_INVOKED = "tool_invoked"
    COMPLETED = "completed"
