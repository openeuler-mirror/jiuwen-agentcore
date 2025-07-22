#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Iterator, AsyncIterator, Self, Union, Callable

from langgraph.constants import END, START

from jiuwen.core.component.base import WorkflowComponent, InnerComponent, ExecGraphComponent
from jiuwen.core.component.break_comp import BreakComponent, LoopController
from jiuwen.core.component.condition.condition import Condition, AlwaysTrue, FuncCondition
from jiuwen.core.component.condition.expression import ExpressionCondition
from jiuwen.core.component.loop_callback.loop_callback import LoopCallback
from jiuwen.core.component.set_variable_comp import SetVariableComponent
from jiuwen.core.context.config import WorkflowConfig
from jiuwen.core.context.context import Context, ContextSetter
from jiuwen.core.context.utils import NESTED_PATH_SPLIT
from jiuwen.core.graph.base import Graph
from jiuwen.core.graph.executable import Output, Input, Executable
from jiuwen.core.workflow.base import BaseWorkFlow


class EmptyExecutable(Executable, InnerComponent):
    async def collect(self, inputs: AsyncIterator[Input], contex: Context) -> Output:
        pass

    async def transform(self, inputs: AsyncIterator[Input], context: Context) -> AsyncIterator[Output]:
        pass

    async def invoke(self, inputs: Input, context: Context) -> Output:
        pass

    async def stream(self, inputs: Input, context: Context) -> Iterator[Output]:
        yield self.invoke(inputs, context)

    def interrupt(self, message: dict):
        return


class LoopGroup(BaseWorkFlow, Executable, InnerComponent, ExecGraphComponent):

    def __init__(self, workflow_config: WorkflowConfig, new_graph: Graph):
        super().__init__(workflow_config, new_graph)
        self.compiled = None

    def start_nodes(self, nodes: list[str]) -> Self:
        for node in nodes:
            self.start_comp(node)
        return self

    def end_nodes(self, nodes: list[str]) -> Self:
        for node in nodes:
            self.end_comp(node)
        return self

    async def invoke(self, inputs: Input, context: Context) -> Output:
        if self.compiled is None:
            self.compiled = self.compile(context)
        await self.compiled.invoke(inputs, context)
        return None

    async def stream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        yield await self.invoke(inputs, context)

    async def collect(self, inputs: AsyncIterator[Input], contex: Context) -> Output:
        pass

    async def transform(self, inputs: AsyncIterator[Input], context: Context) -> AsyncIterator[Output]:
        pass

    async def interrupt(self, message: dict):
        pass


BROKEN = "_broken"
FIRST_IN_LOOP = "_first_in_loop"

CONDITION_NODE_ID = "condition"
BODY_NODE_ID = "body"


class LoopComponent(WorkflowComponent, LoopController, ContextSetter, Executable, InnerComponent, ExecGraphComponent):

    def __init__(self, node_id: str, body: Executable, new_graph: Graph,
                 condition: Union[str, Callable[[], bool], Condition] = None, context_root: str = None,
                 break_nodes: list[BreakComponent] = None, callbacks: list[LoopCallback] = None,
                 set_variable_components: list[SetVariableComponent] = None):
        ContextSetter.__init__(self)
        self._node_id = node_id
        self._body = body

        self._condition: Condition
        if condition is None:
            self._condition = AlwaysTrue()
        elif isinstance(condition, Condition):
            self._condition = condition
        elif isinstance(condition, Callable):
            self._condition = FuncCondition(condition)
        elif isinstance(condition, str):
            self._condition = ExpressionCondition(condition)

        if context_root is None:
            context_root = node_id
        self._context_root = context_root

        if break_nodes:
            for break_node in break_nodes:
                break_node.set_controller(self)

        self._callbacks: list[LoopCallback] = []

        if callbacks:
            for callback in callbacks:
                self.register_callback(callback)

        self._graph = new_graph
        self._graph.add_node(BODY_NODE_ID, self._body)
        self._graph.add_node(CONDITION_NODE_ID, EmptyExecutable())
        self._graph.add_edge(START, CONDITION_NODE_ID)
        self._graph.add_edge(BODY_NODE_ID, CONDITION_NODE_ID)
        self._graph.add_conditional_edges(CONDITION_NODE_ID, self)

        self._context_setters: list[ContextSetter] = [self, self._condition]
        self._context_setters.extend(self._callbacks)
        self._context_setters.extend(set_variable_components)

    def init(self):
        self._context.state.update({self._context_root + NESTED_PATH_SPLIT + BROKEN: False})
        self._context.state.update({self._context_root + NESTED_PATH_SPLIT + FIRST_IN_LOOP: True})
        self._condition.init()

    def to_executable(self) -> Executable:
        return self

    def register_callback(self, callback: LoopCallback):
        self._callbacks.append(callback)

    def __call__(self, *args, **kwargs) -> list[str]:
        in_loop = [BODY_NODE_ID]
        out_loop = [END]

        first_in_loop = self.first_in_loop()
        if first_in_loop:
            self._condition.init()
        continue_loop = False if self.is_broken() else self._condition()

        for callback in self._callbacks:
            if first_in_loop:
                callback.first_in_loop()
            else:
                callback.end_round()
            if continue_loop:
                callback.start_round()
            else:
                callback.out_loop()

        if continue_loop:
            return in_loop

        self.init()
        return out_loop

    def first_in_loop(self) -> bool:
        _first_in_loop = self._context.state.get(self._context_root + NESTED_PATH_SPLIT + FIRST_IN_LOOP)
        if _first_in_loop is None:
            _first_in_loop = True

        if _first_in_loop:
            self._context.state.update({self._context_root + NESTED_PATH_SPLIT + BROKEN: False})
            self._context.state.update({self._context_root + NESTED_PATH_SPLIT + FIRST_IN_LOOP: False})
        return _first_in_loop

    def is_broken(self) -> bool:
        _is_broken = self._context.state.get(self._context_root + NESTED_PATH_SPLIT + BROKEN)
        if isinstance(_is_broken, bool):
            return _is_broken
        return False

    def break_loop(self):
        self._context.state.update({self._context_root + NESTED_PATH_SPLIT + BROKEN: True})

    async def invoke(self, inputs: Input, context: Context) -> Output:
        for context_setter in self._context_setters:
            context_setter.set_context(context.create_executable_context(self._node_id))

        compiled = self._graph.compile(self._context)
        if isinstance(self._body, LoopGroup):
            self._body.compiled = self._body.compile(context)
        await compiled.invoke(inputs, context)
        return None

    async def stream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        yield await self.invoke(inputs, context)

    async def collect(self, inputs: AsyncIterator[Input], contex: Context) -> Output:
        pass

    async def transform(self, inputs: AsyncIterator[Input], context: Context) -> AsyncIterator[Output]:
        pass

    async def interrupt(self, message: dict):
        pass
