#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from abc import ABC
from typing import Self, Union, Any, AsyncIterator, Iterator, Hashable, Callable, Awaitable

from langchain_core.runnables import Runnable

from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Executable, Output, Input


class ExecutableGraph(Executable[Input, Output]):
    def invoke(self, inputs: Input, context: Context) -> Output:
        pass

    async def ainvoke(self, inputs: Input, context: Context) -> Output:
        pass

    def stream(self, inputs: Input, context: Context) -> Iterator[Output]:
        pass

    async def astream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
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