#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from abc import ABC, abstractmethod
from typing import Self, Union, Any, AsyncIterator, Hashable, Callable, Awaitable

from langchain_core.runnables import Runnable

from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Executable, Output, Input

INPUTS_KEY = "inputs"
CONFIG_KEY = "config"

class ExecutableGraph(Executable[Input, Output]):
    async def invoke(self, inputs: Input, context: Context) -> Output:
        context.state.set_user_inputs(inputs.get(INPUTS_KEY))
        results = await self._invoke(inputs.get(CONFIG_KEY))
        return results

    async def stream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        pass

    async def collect(self, inputs: AsyncIterator[Input], contex: Context) -> Output:
        pass

    async def transform(self, inputs: AsyncIterator[Input], context: Context) -> AsyncIterator[Output]:
        pass

    async def interrupt(self, message: dict):
        pass

    @abstractmethod
    async def _invoke(self, config: Any = None) -> Output:
       pass


Router = Union[
    Callable[..., Union[Hashable, list[Hashable]]],
    Callable[..., Awaitable[Union[Hashable, list[Hashable]]]],
    Runnable[Any, Union[Hashable, list[Hashable]]],
]


class Graph(ABC):
    def start_node(self, node_id: str) -> Self:
        pass

    def end_node(self, node_id: str) -> Self:
        pass

    def add_node(self, node_id: str, node: Executable, *, wait_for_all: bool = False) -> Self:
        pass

    def add_edge(self, source_node_id: Union[str, list[str]], target_node_id: str) -> Self:
        pass

    def add_conditional_edges(self, source_node_id: str, router: Any) -> Self:
        pass

    def compile(self, context: Context) -> ExecutableGraph:
        pass
