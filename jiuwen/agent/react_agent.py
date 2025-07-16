#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
"""ReActAgent"""
from typing import Dict, Iterator, Any

from jiuwen.agent.config.react_config import ReActAgentConfig
from jiuwen.agent.context.controller_context_manager import ControllerContextMgr
from jiuwen.agent.controller.react_controller import ReActController, ReActControllerOutput
from jiuwen.core.agent.agent import Agent
from jiuwen.core.agent.handler.base import AgentHandlerImpl
from jiuwen.agent.state.react_state import ReActState
from jiuwen.core.context.config import Config
from jiuwen.core.context.context import Context
from jiuwen.core.context.memory.base import InMemoryState


class ReActAgent(Agent):
    def __init__(self, agent_config: ReActAgentConfig):
        super().__init__(agent_config)
        self._state = ReActState()

    def _init_controller(self):
        return ReActController(self._config, self._controller_context_manager)

    def _init_agent_handler(self):
        return AgentHandlerImpl()

    def _init_controller_context_manager(self) -> ControllerContextMgr:
        context = Context(config=Config(), state=InMemoryState(), store=None, tracer=None)
        return ControllerContextMgr(self._config, context)

    def invoke(self, inputs: Dict) -> Dict:
        while self._state.current_iteration < self._config.constrain.max_iteration:
            controller_output: ReActControllerOutput = self._controller.invoke(inputs)
            if not controller_output.should_continue:
                break

            self._execute_sub_tasks(controller_output.sub_tasks)
            self._state.current_iteration += 1

        return dict(output=self._state.final_result)

    def stream(self, inputs: Dict) -> Iterator[Any]:
        pass

    def _execute_sub_tasks(self, sub_tasks):
        pass
