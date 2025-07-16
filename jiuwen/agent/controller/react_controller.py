#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
"""Controller of ReActAgent"""
from typing import List

from pydantic import BaseModel, Field

from jiuwen.agent.context.controller_context_manager import ControllerContextMgr
from jiuwen.agent.controller.base import Controller, ControllerOutput
from jiuwen.core.agent.handler.base import AgentHandler
from jiuwen.agent.config.base import AgentConfig
from jiuwen.core.agent.task.task import SubTask


class ReActControllerOutput(ControllerOutput):
    should_continue: bool = Field(default=False)
    output: str = Field(default="")
    sub_tasks: List[SubTask] = Field(default_factory=list)


class ReActControllerInput:
    ...


class ReActController(Controller):
    def __init__(self, config: AgentConfig, context_mgr: ControllerContextMgr):
        super().__init__(config, context_mgr)

    def invoke(self, inputs: ReActControllerInput) -> ReActControllerOutput:
        query = inputs.get("query", "")
        chat_history = self._latest_chat_history()
        tools = self._create_tools_metadata()
        llm_inputs = self._create_llm_inputs(query, chat_history, tools)
        result: dict = self._invoke_llm_and_parse_output(llm_inputs)
        self._update_context(result)
        return ReActControllerOutput(**result)

    def set_agent_handler(self, agent_handler: AgentHandler):
        self._agent_handler = agent_handler
