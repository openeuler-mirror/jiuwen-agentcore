from typing import List, Union, Iterator, Any, Dict

from pydantic import Field

from jiuwen.agent.common.enum import SubTaskType
from jiuwen.core.agent.controller.base import Controller, ControllerOutput, ControllerInput
from jiuwen.core.agent.task.sub_task import SubTask


class Message:
    ...


class WorkflowControllerOutput(ControllerOutput):
    sub_tasks: List[SubTask] = Field(default_factory=list)
    messages: Any = Field(default_factory=list)


class WorkflowControllerInput(ControllerInput):
    workflow_inputs: dict = Field(default_factory=dict)


class WorkflowController(Controller):
    """
    根据输入生成 WorkflowControllerOutput
    """

    @staticmethod
    def _filter_inputs(schema: dict, user_data: dict) -> dict:
        """
        根据 schema 过滤并校验用户输入
        :param schema:   workflow.inputs 的 schema，形如 {"query": {"type": "string", "required": True}}
        :param user_data: 用户实际传入的数据，形如 {"query": "你好", "foo": "bar"}
        :return: 仅保留 schema 中声明的字段
        :raises KeyError: 缺失必填字段时抛出
        """
        if not schema:
            return {}

        required_fields = {
            k for k, v in schema.items()
            if isinstance(v, dict) and v.get("required") is True
        }

        filtered = {}
        for k in schema:
            if k not in user_data:
                if k in required_fields:
                    raise KeyError(f"缺少必填参数: {k}")
                continue
            filtered[k] = user_data[k]

        return filtered

    def invoke(
            self, inputs: Dict, context
    ) -> WorkflowControllerOutput:
        if len(self._config.workflows) > 1:
            raise NotImplementedError("Multi-workflow not implemented yet")

        workflow = self._config.workflows[0]

        filtered_inputs = self._filter_inputs(
            schema=workflow.inputs or {},
            user_data=inputs
        )

        sub_tasks = [
            SubTask(
                sub_task_type=SubTaskType.WORKFLOW,
                func_name=workflow.name,
                func_id=f"{workflow.id}_{workflow.version}",
                func_args=filtered_inputs,
            )
        ]

        return WorkflowControllerOutput(is_task=True, sub_tasks=sub_tasks)

    def should_continue(self, output: WorkflowControllerOutput) -> bool:
        """
        当且仅当 output 是 Task 时继续下一轮
        """
        return not output.is_task
