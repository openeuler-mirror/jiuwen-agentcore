#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import asyncio
from contextvars import Context
from functools import partial
from typing import Callable, Union, Hashable, Iterator, AsyncIterator

from jiuwen.core.component.base import WorkflowComponent
from jiuwen.core.component.branch_router import BranchRouter
from jiuwen.core.component.condition.condition import Condition
from jiuwen.core.graph.base import Graph
from jiuwen.core.graph.executable import Executable, Input, Output


class BranchComponent(WorkflowComponent, Executable):
    def interrupt(self, message: dict):
        pass

    def __init__(self, context: Context, executable: Executable = None):
        self._router = BranchRouter(context)
        self._executable = executable

    def add_branch(self, condition: Union[str, Callable[[], bool], Condition], target: Union[str, list[str]],
                   branch_id: str = None):
        if isinstance(target, str):
            target = [target]
        self._router.add_branch(condition, target, branch_id=branch_id)

    def router(self) -> Callable[..., Union[Hashable, list[Hashable]]]:
        return self._router

    def to_executable(self) -> Executable:
        return self

    def invoke(self, inputs: Input, context: Context) -> Output:
        if self._executable:
            return self._executable.invoke(inputs, context)
        return inputs

    async def ainvoke(self, inputs: Input, context: Context) -> Output:
        return await asyncio.get_running_loop().run_in_executor(
            None, partial(self.invoke, context), inputs)

    def stream(self, inputs: Input, context: Context) -> Iterator[Output]:
        yield self.invoke(inputs, context)

    async def astream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        yield await self.ainvoke(inputs, context)

    def add_component(self, graph: Graph, node_id: str, wait_for_all: bool = False):
        graph.add_node(node_id, self.to_executable(), wait_for_all=wait_for_all)
        graph.add_conditional_edges(node_id, self.router())
