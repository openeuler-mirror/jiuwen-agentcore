#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Union, Self, Iterator, AsyncIterator

from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from jiuwen.core.context.context import Context
from jiuwen.core.graph.base import Graph, Router, ExecutableGraph
from jiuwen.core.graph.executable import Executable, Input, Output
from jiuwen.core.graph.graph_state import GraphState
from jiuwen.core.graph.vertex import Vertex


class PregelGraph(Graph):
    def __init__(self):
        self.pregel: StateGraph = StateGraph(GraphState)
        self.compiledStateGraph = None
        self.edges: list[Union[str, list[str]], str] = []
        self.waits: set[str] = set()
        self.nodes: list[Vertex] = []

    def start_node(self, node_id: str) -> Self:
        self.pregel.set_entry_point(node_id)
        return self

    def end_node(self, node_id: str) -> Self:
        self.pregel.set_finish_point(node_id)
        return self

    def add_node(self, node_id: str, node: Executable, *, wait_for_all: bool = False) -> Self:
        vertex_node = Vertex(node_id, node)
        self.nodes.append(vertex_node)
        self.pregel.add_node(node_id, vertex_node)
        if wait_for_all:
            self.waits.add(node_id)
        return self

    def add_edge(self, source_node_id: Union[str, list[str]], target_node_id: str) -> Self:
        self.edges.append((source_node_id, target_node_id))
        return self

    def add_conditional_edges(self, source_node_id: str, router: Router) -> Self:
        self.pregel.add_conditional_edges(source_node_id, router)
        return self

    def compile(self, context: Context) -> ExecutableGraph:
        for node in self.nodes:
            node.init(context)
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
    def __init__(self, compiledStateGraph: CompiledStateGraph):
        self._compiledStateGraph = compiledStateGraph

    def invoke(self, inputs: Input, context: Context) -> Output:
        return self._compiledStateGraph.invoke({"source_node_id": None})

    def stream(self, inputs: Input, context: Context) -> Iterator[Output]:
        return self._compiledStateGraph.stream({"source_node_id": None})

    async def ainvoke(self, inputs: Input, context: Context) -> Output:
        return self._compiledStateGraph.ainvoke({"source_node_id": None})

    async def astream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        return self._compiledStateGraph.astream({"source_node_id": None})

    def interrupt(self, message: dict):
        return
