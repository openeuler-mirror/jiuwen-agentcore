#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import asyncio
from functools import partial
from typing import Iterator, AsyncIterator, Self, Union, Callable

from langgraph.constants import END, START

from jiuwen.core.component.base import WorkflowComponent
from jiuwen.core.component.break_comp import BreakComponent, LoopController
from jiuwen.core.component.condition.condition import Condition, AlwaysTrue, FuncCondition
from jiuwen.core.component.condition.expression import ExpressionCondition
from jiuwen.core.component.loop_callback.loop_callback import LoopCallback
from jiuwen.core.context.context import Context
from jiuwen.core.context.utils import NESTED_PATH_SPLIT
from jiuwen.core.graph.base import Graph, Router, ExecutableGraph
from jiuwen.core.graph.executable import Output, Input, Executable
from jiuwen.graph.factory import GraphFactory


class EmptyExecutable(Executable):

    def invoke(self, inputs: Input, context: Context) -> Output:
        pass

    async def ainvoke(self, inputs: Input, context: Context) -> Output:
        return await asyncio.get_running_loop().run_in_executor(
            None, partial(self.invoke, context), inputs)

    def stream(self, inputs: Input, context: Context) -> Iterator[Output]:
        yield self.invoke(inputs, context)

    async def astream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        yield await self.ainvoke(inputs, context)

    def interrupt(self, message: dict):
        return


class LoopGroup:
    def __init__(self, context: Context, graph: Graph = None):
        self._context = context
        self._graph = graph if graph else GraphFactory().create_graph()

    def add_component(self, node_id: str, component: WorkflowComponent, *, wait_for_all: bool = False,
                      inputs_schema: dict = None, outputs_schema: dict = None) -> Self:
        component.add_component(self._graph, node_id, wait_for_all=wait_for_all)
        self._context.config.set_io_schema(node_id, (inputs_schema, outputs_schema))
        return self

    def start_nodes(self, nodes: list[str]) -> Self:
        for node in nodes:
            self._graph.start_node(node)
        return self

    def end_nodes(self, nodes: list[str]) -> Self:
        for node in nodes:
            self._graph.end_node(node)
        return self

    def add_connection(self, start_node_id: Union[str, list[str]], end_node_id: str) -> Self:
        self._graph.add_edge(start_node_id, end_node_id)
        return self

    def add_conditional_connection(self, source: str, router: Router) -> Self:
        self._graph.add_conditional_edges(source, router)
        return self

    def compile(self) -> ExecutableGraph:
        return self._graph.compile(self._context)


BROKEN = "_broken"
FIRST_IN_LOOP = "_first_in_loop"


class LoopComponent(WorkflowComponent, LoopController):

    def __init__(self, context: Context, node_id: str, body: Union[Executable, LoopGroup],
                 condition: Union[str, Callable[[], bool], Condition] = None, context_root: str = None,
                 break_nodes: list[BreakComponent] = None, callbacks: list[LoopCallback] = None, graph: Graph = None):
        super().__init__()
        self._node_id = node_id
        if context is None:
            raise ValueError("context cannot be None")
        if context_root is None:
            context_root = node_id

        self._context = context
        self._callbacks: list[LoopCallback] = []
        self._context_root = context_root

        self._condition: Condition
        if condition is None:
            self._condition = AlwaysTrue()
        elif isinstance(condition, Condition):
            self._condition = condition
        elif isinstance(condition, Callable):
            self._condition = FuncCondition(condition)
        elif isinstance(condition, str):
            self._condition = ExpressionCondition(context, condition)

        if break_nodes:
            for break_node in break_nodes:
                break_node.set_controller(self)

        if callbacks:
            for callback in callbacks:
                self.register_callback(callback)

        condition_node_id = "condition"
        body_node_id = "body"
        self._in_loop = [body_node_id]
        self._out_loop = [END]

        self._graph = graph if graph else GraphFactory().create_graph()
        if isinstance(body, LoopGroup):
            body = body.compile()
        self._graph.add_node(body_node_id, body)
        self._graph.add_node(condition_node_id, EmptyExecutable())
        self._graph.add_edge(START, condition_node_id)
        self._graph.add_edge(body_node_id, condition_node_id)
        self._graph.add_conditional_edges(condition_node_id, self)

        self.init()
        self._compiled = self._graph.compile(self._context)

    def init(self):
        self._context.state.update(self._node_id, {self._context_root + NESTED_PATH_SPLIT + BROKEN: False})
        self._context.state.update(self._node_id, {self._context_root + NESTED_PATH_SPLIT + FIRST_IN_LOOP: True})
        self._condition.init()

    def to_executable(self) -> Executable:
        return self._compiled

    def register_callback(self, callback: LoopCallback):
        self._callbacks.append(callback)

    def __call__(self, *args, **kwargs) -> list[str]:
        continue_loop = False if self.is_broken() else self._condition()
        first_in_loop = self.first_in_loop()

        for callback in self._callbacks:
            if not first_in_loop:
                callback.end_round()
            if continue_loop:
                if first_in_loop:
                    callback.first_in_loop()
                callback.start_round()
            else:
                callback.out_loop()

        self._context.state.io_state.commit()
        self._context.state.global_state.commit()
        if continue_loop:
            return self._in_loop

        self.init()
        return self._out_loop

    def first_in_loop(self) -> bool:
        _first_in_loop = self._context.state.get(self._context_root + NESTED_PATH_SPLIT + FIRST_IN_LOOP)
        if isinstance(_first_in_loop, bool):
            if _first_in_loop:
                self._context.state.update(self._node_id,
                                           {self._context_root + NESTED_PATH_SPLIT + FIRST_IN_LOOP: False})
            return _first_in_loop
        self._context.state.update(self._node_id, {self._context_root + NESTED_PATH_SPLIT + FIRST_IN_LOOP: False})
        return True

    def is_broken(self) -> bool:
        _is_broken = self._context.state.get(self._context_root + NESTED_PATH_SPLIT + BROKEN)
        if isinstance(_is_broken, bool):
            return _is_broken
        return False

    def break_loop(self):
        self._context.state.update(self._node_id, {self._context_root + NESTED_PATH_SPLIT + BROKEN: True})
