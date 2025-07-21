#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
"""ReActAgent"""
import json
from typing import Dict, Iterator, Any, List

from jiuwen.agent.common.enum import ControllerType, ReActStatus
from jiuwen.agent.common.schema import WorkflowSchema, PluginSchema
from jiuwen.agent.config.react_config import ReActAgentConfig
from jiuwen.core.agent.agent import Agent
from jiuwen.core.agent.controller.react_controller import ReActController, ReActControllerOutput, ReActControllerUtils, \
    ReActControllerInput
from jiuwen.core.agent.handler.base import AgentHandlerImpl, AgentHandlerInputs
from jiuwen.agent.state.react_state import ReActState
from jiuwen.core.agent.task.task import SubTask
from jiuwen.core.component.common.configs.model_config import ModelConfig
from jiuwen.core.context.context import Context
from jiuwen.core.context.controller_context.controller_context_manager import ControllerContextMgr
from jiuwen.core.utils.llm.messages import ToolMessage
from jiuwen.core.utils.tool.base import Tool
from jiuwen.core.workflow.base import Workflow


REACT_AGENT_STATE_KEY = "react_agent_state"

def create_react_agent_config(agent_id: str,
                              agent_version: str,
                              description: str,
                              workflows: List[WorkflowSchema],
                              plugins: List[PluginSchema],
                              model: ModelConfig,
                              prompt_template: List[Dict]):
    config = ReActAgentConfig(id=agent_id,
                              version=agent_version,
                              description=description,
                              workflows=workflows,
                              plugins=plugins,
                              model=model,
                              prompt_template=prompt_template)
    return config


def create_react_agent(agent_config: ReActAgentConfig,
                       workflows: List[Workflow] = None,
                       tools: List[Tool] = None):
    agent = ReActAgent(agent_config)
    agent.bind_workflows(workflows)
    agent.bind_tools(tools)
    return agent


class ReActAgent(Agent):
    def __init__(self, agent_config: ReActAgentConfig):
        super().__init__(agent_config)
        self._state = None

    def _init_controller(self):
        if self._config.controller_type != ControllerType.ReActController:
            raise NotImplementedError("")
        return ReActController(self._config, self._controller_context_manager)

    def _init_agent_handler(self):
        return AgentHandlerImpl(self._config)

    def _init_controller_context_manager(self) -> ControllerContextMgr:
        return ControllerContextMgr(self._config)

    def invoke(self, inputs: Dict, context: Context) -> Dict:
        context.set_controller_context_manager(self._controller_context_manager)
        self._load_state_from_context(context)
        controller_output = ReActControllerOutput()
        while self._state.current_iteration < self._config.constrain.max_iteration:
            controller_output = self._controller.invoke(ReActControllerInput(**inputs), context)
            self._state.handle_llm_response_event(controller_output.llm_output, controller_output.sub_tasks)
            self._store_state_to_context(context)
            if controller_output.should_continue:
                completed_sub_tasks = self._execute_sub_tasks(context)
            else:
                break
            self._state.handle_tool_invoked_event(completed_sub_tasks)
            self._state.increment_iteration()
            self._store_state_to_context(context)

        self._state.handle_react_completed_event(controller_output.llm_output.content)
        self._store_state_to_context(context)
        return dict(output=self._state.final_result)

    def stream(self, inputs: Dict, context: Context) -> Iterator[Any]:
        pass

    def _execute_sub_tasks(self, context: Context):
        to_exec_sub_tasks = self._state.sub_tasks
        completed_sub_tasks = []
        for st in to_exec_sub_tasks:
            inputs = AgentHandlerInputs(context=context, name=st.func_name, arguments=st.func_args)
            exec_result = self._agent_handler.invoke(st.sub_task_type, inputs)
            st.result = json.dumps(exec_result, ensure_ascii=False) if isinstance(exec_result, dict) else exec_result
            completed_sub_tasks.append(st)
        self._update_chat_history_in_context(completed_sub_tasks, context)
        return completed_sub_tasks

    def _load_state_from_context(self, context: Context):
        state_dict = context.state.get(REACT_AGENT_STATE_KEY)
        if state_dict:
            self._state = ReActState.deserialize(state_dict)
        else:
            self._state = ReActState()

    def _store_state_to_context(self, context):
        state_dict = self._state.serialize()
        context.state.update({REACT_AGENT_STATE_KEY: state_dict})
        context.state.commit()

    @staticmethod
    def _update_chat_history_in_context(completed_sub_tasks: List[SubTask], context):
        current_messages = ReActControllerUtils.get_dialogue_history_from_context(context)
        tool_messages = [ToolMessage(content=sub_task.result, tool_call_id=sub_task.id) for sub_task in completed_sub_tasks]
        ReActControllerUtils.set_dialogue_history_to_context(current_messages + tool_messages, context)
