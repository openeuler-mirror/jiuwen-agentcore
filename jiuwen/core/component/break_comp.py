#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from abc import abstractmethod, ABC
from typing import Iterator, AsyncIterator

from jiuwen.core.component.base import WorkflowComponent
from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Executable, Input, Output


class LoopController(ABC):
    @abstractmethod
    def break_loop(self):
        raise NotImplementedError()

    @abstractmethod
    def is_broken(self) -> bool:
        raise NotImplementedError()


class BreakComponent(WorkflowComponent, Executable):

    def __init__(self):
        super().__init__()
        self._loop_controller = None

    def interrupt(self, message: dict):
        pass

    def set_controller(self, loop_controller: LoopController):
        self._loop_controller = loop_controller

    def to_executable(self) -> Executable:
        return self

    def invoke(self, inputs: Input, context: Context) -> Output:
        if self._loop_controller is None:
            raise RuntimeError('Loop controller not initialized')
        self._loop_controller.break_loop()
        return {}

    async def ainvoke(self, inputs: Input, context: Context) -> Output:
        return await asyncio.get_running_loop().run_in_executor(
            None, partial(self.invoke, context), inputs)

    def stream(self, inputs: Input, context: Context) -> Iterator[Output]:
        yield self.invoke(inputs, context)

    async def astream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        yield await self.ainvoke(inputs, context)
