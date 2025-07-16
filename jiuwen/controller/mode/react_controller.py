#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
"""Controller of ReActAgent"""
from typing import List

from pydantic import BaseModel, Field

from jiuwen.controller.handler.base import AgentSdk
from jiuwen.controller.common.sub_task import SubTask
from jiuwen.controller.config.base import AgentConfig
from jiuwen.controller.mode.base import Controller
from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Input


class ReActController(Controller):
    def __init__(self, config: AgentConfig):
        super().__init__(config)

    def invoke(self, inputs: Input, context: Context) -> ReActControllerOutput:
        query = inputs.get("query", "")
        chat_history = self._latest_chat_history()
        tools = self._create_tools_metadata()
        llm_inputs = self._create_llm_inputs(query, chat_history, tools)
        result: dict = self._invoke_llm_and_parse_output(llm_inputs)
        self._update_context(result, context)
        return ReActControllerOutput(**result)

    def set_agent_sdk(self, agent_sdk: AgentSdk):
        self._agent_sdk = agent_sdk


class ReActControllerOutput(BaseModel):
    should_continue: bool = Field(default=False)
    output: str = Field(default="")
    sub_tasks: List[SubTask] = Field(default_factory=list)
