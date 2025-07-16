#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
"""ReActAgent"""

from jiuwen.controller.config.base import AgentConfig
from jiuwen.controller.config.react_config import ReActAgentConfig
from jiuwen.controller.handler.base import AgentSdk, AgentSdkImpl
from jiuwen.controller.mode.base import Controller
from jiuwen.controller.mode.react_controller import ReActController, ReActControllerOutput
from jiuwen.controller.state.react_state import ReActState
from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Input, Output


class TaskManager:
    pass


class MockAgent:
    def __init__(self, agent_config: AgentConfig):
        self._config = agent_config
        self._controller = self._init_controller()
        self._agent_sdk = self._init_agent_sdk()
        self._task_manager = self._init_task_manager()

    def _init_controller(self):
        return Controller(self._config)

    def _init_agent_sdk(self):
        return AgentSdk()

    def _init_task_manager(self):
        return TaskManager()


class ReActAgent(MockAgent):
    def __init__(self, agent_config: ReActAgentConfig):
        super().__init__(agent_config)
        self._state = ReActState()

    def _init_controller(self):
        return ReActController(self._config)

    def _init_agent_sdk(self):
        return AgentSdkImpl()

    def invoke(self, inputs: Input, context: Context) -> Output:
        self._init_state(context)

        while self._state.current_iteration < self._config.constrain.max_iteration:
            controller_output: ReActControllerOutput = self._controller.invoke(inputs, self._context)
            if not controller_output.should_continue:
                break

            self._execute_sub_tasks(controller_output.sub_tasks)
            self._state.current_iteration += 1

        return dict(output=self._state.final_result)

    async def ainvoke(self, inputs: Input, context: Context) -> Output:
        return dict()

    def _execute_sub_tasks(self, sub_tasks):
        pass

    def _init_state(self, context):
        self._state = ReActState()
        self._context = context
