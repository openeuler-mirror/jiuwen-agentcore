#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import AsyncIterator

from jiuwen.core.component.base import WorkflowComponent
from jiuwen.core.context.context import Context
from jiuwen.core.graph.base import INPUTS_KEY, CONFIG_KEY
from jiuwen.core.graph.executable import Executable, Input, Output
from jiuwen.core.workflow.base import Workflow


class ExecWorkflowComponent(WorkflowComponent, Executable):
    def __init__(self, node_id: str, sub_workflow: Workflow):
        super().__init__()
        self.node_id = node_id
        self._sub_workflow = sub_workflow

    async def invoke(self, inputs: Input, context: Context) -> Output:
        return await self._sub_workflow.sub_invoke(inputs.get(INPUTS_KEY), context, inputs.get(CONFIG_KEY))

    async def stream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        raise RuntimeError("ExecWorkflowComponent does not have streaming capability")

    async def collect(self, inputs: AsyncIterator[Input], contex: Context) -> Output:
        pass

    async def transform(self, inputs: AsyncIterator[Input], context: Context) -> AsyncIterator[Output]:
        pass

    async def interrupt(self, message: dict):
        pass

    def to_executable(self) -> Executable:
        return self

    def graph_invoker(self) -> bool:
        return True