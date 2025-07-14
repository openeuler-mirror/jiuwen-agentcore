#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import AsyncIterator, Iterator

from jiuwen.core.component.base import WorkflowComponent
from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Executable, Input, Output


class CommonNode(Executable, WorkflowComponent):

    def __init__(self, node_id: str):
        super().__init__()
        self.node_id = node_id

    def invoke(self, inputs: Input, context: Context) -> Output:
        return inputs

    async def ainvoke(self, inputs: Input, context: Context) -> Output:
        pass

    def stream(self, inputs: Input, context: Context) -> Iterator[Output]:
        yield self.invoke(inputs, context)

    async def astream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        yield await self.ainvoke(inputs, context)

    def interrupt(self, message: dict):
        pass

    def to_executable(self) -> Executable:
        return self

class AddTenNode(Executable, WorkflowComponent):

    def __init__(self, node_id: str):
        super().__init__()
        self.node_id = node_id

    def invoke(self, inputs: Input, context: Context) -> Output:
        return {"result": inputs["source"] + 10}

    async def ainvoke(self, inputs: Input, context: Context) -> Output:
        pass

    def stream(self, inputs: Input, context: Context) -> Iterator[Output]:
        yield self.invoke(inputs, context)

    async def astream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        yield await self.ainvoke(inputs, context)

    def interrupt(self, message: dict):
        pass

    def to_executable(self) -> Executable:
        return self