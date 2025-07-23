#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Iterator, AsyncIterator, Self, Union, Callable

from langgraph.constants import END, START

from jiuwen.core.component.base import WorkflowComponent
from jiuwen.core.component.break_comp import BreakComponent, LoopController
from jiuwen.core.component.condition.condition import Condition, AlwaysTrue, FuncCondition, INDEX
from jiuwen.core.component.condition.expression import ExpressionCondition
from jiuwen.core.component.loop_callback.loop_callback import LoopCallback
from jiuwen.core.component.loop_callback.loop_id import LoopIdCallback
from jiuwen.core.component.set_variable_comp import SetVariableComponent
from jiuwen.core.context.config import WorkflowConfig
from jiuwen.core.context.context import Context, ContextSetter, ExecutableContext
from jiuwen.core.context.utils import NESTED_PATH_SPLIT
from jiuwen.core.graph.base import Graph
from jiuwen.core.graph.executable import Output, Input, Executable
from jiuwen.core.workflow.base import BaseWorkFlow


class EmptyExecutable(Executable):
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

    def skip_trace(self) -> bool:
        return True


class LoopGroup(BaseWorkFlow, Executable):

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
        if isinstance(context, ExecutableContext) and isinstance(context.parent_context, ExecutableContext):
            if self.compiled is None:
                self.compiled = self.compile(context.parent_context.parent_context)
            await self.compiled.invoke(inputs, context.parent_context.parent_context)
        return None

    async def stream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        yield await self.invoke(inputs, context)

    async def collect(self, inputs: AsyncIterator[Input], contex: Context) -> Output:
        pass

    async def transform(self, inputs: AsyncIterator[Input], context: Context) -> AsyncIterator[Output]:
        pass

    async def interrupt(self, message: dict):
        pass

    def skip_trace(self) -> bool:
        return True

    def graph_invoker(self) -> bool:
        return True

BROKEN = "_broken"
FIRST_IN_LOOP = "_first_in_loop"

CONDITION_NODE_ID = "condition"
BODY_NODE_ID = "body"


class LoopComponent(WorkflowComponent, LoopController, ContextSetter, Executable):

    def __init__(self, node_id: str, body: Executable, new_graph: Graph,
                 condition: Union[str, Callable[[], bool], Condition] = None,
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
        self._context_root = node_id

        if break_nodes:
            for break_node in break_nodes:
                break_node.set_controller(self)

        loop_id_callback = LoopIdCallback(node_id)

        self._callbacks: list[LoopCallback] = []

        self.register_callback(loop_id_callback)
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
        self._context.state.update_comp({self._context_root + NESTED_PATH_SPLIT + BROKEN: False})
        self._context.state.update_io({self._context_root + NESTED_PATH_SPLIT + INDEX: -1})
        self._condition.init()
        self._context.state.commit()

    def to_executable(self) -> Executable:
        return self

    def register_callback(self, callback: LoopCallback):
        self._callbacks.append(callback)

    def __call__(self, *args, **kwargs) -> list[str]:
        in_loop = [BODY_NODE_ID]
        out_loop = [END]

        first_in_loop = self.first_in_loop()
        if first_in_loop:
            self.init()
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
            self._context.state.update_io({self._context_root + NESTED_PATH_SPLIT + INDEX: self._context.state.get_io(
                self._context_root + NESTED_PATH_SPLIT + INDEX) + 1})
            return in_loop

        self._context.state.update_comp({self._context_root + NESTED_PATH_SPLIT + FIRST_IN_LOOP: True})
        self.init()
        return out_loop

    def first_in_loop(self) -> bool:
        self._context.state.update_io({self._context_root + NESTED_PATH_SPLIT + INDEX: -1})
        index = self._context.state.get_io(self._context_root + NESTED_PATH_SPLIT + INDEX)
        if index is None or index == -1:
            return True
        return False

    def is_broken(self) -> bool:
        _is_broken = self._context.state.get_comp(self._context_root + NESTED_PATH_SPLIT + BROKEN)
        if isinstance(_is_broken, bool):
            return _is_broken
        return False

    def break_loop(self):
        self._context.state.update_comp({self._context_root + NESTED_PATH_SPLIT + BROKEN: True})

    async def invoke(self, inputs: Input, context: Context) -> Output:
        for context_setter in self._context_setters:
            context_setter.set_context(context)

        compiled = self._graph.compile(self._context)
        if isinstance(context, ExecutableContext):
            if isinstance(self._body, LoopGroup):
                self._body.compiled = self._body.compile(context.parent_context)
            await compiled.invoke(inputs, context.parent_context)
        return None

    async def stream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        yield await self.invoke(inputs, context)

    async def collect(self, inputs: AsyncIterator[Input], contex: Context) -> Output:
        pass

    async def transform(self, inputs: AsyncIterator[Input], context: Context) -> AsyncIterator[Output]:
        pass

    async def interrupt(self, message: dict):
        pass

    def graph_invoker(self) -> bool:
        return True