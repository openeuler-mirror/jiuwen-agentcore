#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Union, Self, Iterator, AsyncIterator

from langgraph.graph import StateGraph

from jiuwen.core.graph.base import Graph
from jiuwen.core.graph.state import State
from jiuwen.core.graph.vertex import Vertex


class PregelGraph(Graph):
    def __init__(self):
        self.pregel: StateGraph = StateGraph(State)
        self.compiledStateGraph = None
        self.edges: list[Union[str, list[str]], str] = []
        self.waits: set[str] = set()

    def start_node(self, node_id: str) -> Self:
        self.pregel.set_entry_point(node_id)
        return self

    def end_node(self, node_id: str) -> Self:
        self.pregel.set_finish_point(node_id)
        return self

    def add_node(self, node_id: str, node: Executable, *, wait_for_all: bool = False, inputs: dict = None) -> Self:
        self.pregel.add_node(node_id, Vertex(node_id, node, inputs))
        if wait_for_all:
            self.waits.add(node_id)
        return self

    def add_edge(self, start_node_id: Union[str, list[str]], end_node_id: str) -> Self:
        self.edges.append((start_node_id, end_node_id))
        return self

    def add_conditional_edges(self, source: str, router: Router) -> Self:
        self.pregel.add_conditional_edges(source, router)
        return self

    def compile(self) -> ExecutableGraph:
        if self.compiledStateGraph is None:
            self._pre_compile()
            self.compiledStateGraph = self.pregel.compile()
        return CompiledGraph(self.compiledStateGraph)

    def _pre_compile(self):
        edges: list[Union[str, list[str]], str] = []
        sources: dict[str, list[str]] = {}
        for (source_node_id, target_node_id) in self.edges:
            if target_node_id in self.waits:
                if target_node_id not in sources:
                    sources[target_node_id] = []
                if isinstance(source_node_id, str):
                    sources[target_node_id].append(source_node_id)
                elif isinstance(source_node_id, list):
                    sources[target_node_id].extend(source_node_id)
            else:
                edges.append((source_node_id, target_node_id))
        for (target_node_id, source_node_id) in sources.items():
            self.pregel.add_edge(source_node_id, target_node_id)
        for (source_node_id, target_node_id) in edges:
            self.pregel.add_edge(source_node_id, target_node_id)


class CompiledGraph(ExecutableGraph):
    def __init__(self, compiledStateGraph: CompiledGraph):
        self._compiledStateGraph = compiledStateGraph

    def invoke(self, inputs: Input, context: Context) -> Output:
        return self._compiledStateGraph.invoke({'context': context})

    def stream(self, inputs: Input, context: Context) -> Iterator[Output]:
        return self._compiledStateGraph.stream({'context': context})

    async def ainvoke(self, inputs: Input, context: Context) -> Output:
        return self._compiledStateGraph.ainvoke({'context': context})

    async def astream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        return self._compiledStateGraph.astream({'context': context})
