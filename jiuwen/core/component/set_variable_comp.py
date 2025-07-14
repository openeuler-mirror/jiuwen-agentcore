#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import asyncio
from functools import partial
from typing import AsyncIterator, Iterator

from jiuwen.core.component.base import WorkflowComponent
from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Executable, Input, Output


class SetVariableComponent(WorkflowComponent, Executable):
    def __init__(self, context: Context, varivable_mapping: dict[str, Any]):
        self._context = context
        self._varivable_mapping = varivable_mapping

    def invoke(self, inputs: Input, context: Context) -> Output:
        for left, right in self._varivable_mapping.items():
            left_ref_str = get_ref_str(left)
            if left_ref_str == "":
                left_ref_str = left
            if isinstance(right, str):
                ref_str = get_ref_str(right)
                if ref_str == "":
                    self._context.store.write(left_ref_str, self._context.store.read(ref_str))
                    continue
            self._context.store.write(left_ref_str, right)

        return None

    async def ainvoke(self, inputs: Input, context: Context) -> Output:
        return await asyncio.get_running_loop().run_in_executor(
            None, partial(self.invoke, context), inputs
        )

    def stream(self, inputs: Input, context: Context) -> Iterator[Output]:
        yield self.invoke(inputs, context)

    async def astream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        yield await self.ainvoke(inputs, context)

    def interrupt(self, message: dict):
        pass
