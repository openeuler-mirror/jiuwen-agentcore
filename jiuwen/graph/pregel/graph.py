#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import uuid
from typing import Union, Self, AsyncIterator, Any, Callable

from langgraph.constants import INTERRUPT
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.pregel.loop import PregelLoop

from jiuwen.core.context.context import Context
from jiuwen.core.graph.base import Graph, Router, ExecutableGraph
from jiuwen.core.graph.executable import Executable, Input, Output
from jiuwen.core.graph.graph_state import GraphState
from jiuwen.core.graph.interrupt.interactive_input import InteractiveInput
from jiuwen.core.graph.vertex import Vertex
from jiuwen.graph.checkpoint.memory import JiuwenInMemoryCheckpointSaver


class AfterProcessor:
    def __init__(self, after_tick: Callable[..., Any]):
        self._after_tick = after_tick

    def after_tick(self, loop: PregelLoop, thread_id: str) -> None:
        context = PregelGraph.context_mapping[thread_id]
        context.state.commit()
        return self._after_tick(loop)


after_processor: AfterProcessor = AfterProcessor(PregelLoop.after_tick)


def after_tick(self) -> None:
    thread_id = self.config["configurable"]["thread_id"]
    return after_processor.after_tick(self, thread_id)


PregelLoop.after_tick = after_tick


class PregelGraph(Graph):
    context_mapping: dict[str, Context] = {}

    def __init__(self):
        self.pregel: StateGraph = StateGraph(GraphState)
        self.compiledStateGraph = None
        self.edges: list[Union[str, list[str]], str] = []
        self.waits: set[str] = set()
        self.nodes: list[Vertex] = []
        self.thread_id = None
        self.checkpoint_saver = None

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
            self.thread_id = str(uuid.uuid4())
            self.checkpoint_saver = JiuwenInMemoryCheckpointSaver()
            self.compiledStateGraph = self.pregel.compile(checkpointer=self.checkpoint_saver)

        self.context_mapping[self.thread_id] = context
        self.checkpoint_saver.register_context(context)
        return CompiledGraph(self.compiledStateGraph, self.thread_id, self.checkpoint_saver)

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
    def __init__(self, compiled_state_graph: CompiledStateGraph, thread_id: str,
                 checkpoint_saver: JiuwenInMemoryCheckpointSaver) -> None:
        self._compiled_state_graph = compiled_state_graph
        self._thread_id = thread_id
        self._checkpoint_saver = checkpoint_saver

    async def _invoke(self, inputs: Input, context: Context, config: Any = None) -> Output:
        config = {"configurable": {"thread_id": self._thread_id}} if config is None else config
        if isinstance(inputs, InteractiveInput):
            self._checkpoint_saver.register_context(context)
            self._checkpoint_saver.register_input(inputs)
            result = await self._compiled_state_graph.ainvoke(None,
                                                              config=config,
                                                              checkpoint_during=False)
        else:
            context.state.set_user_inputs(inputs)
            context.state.commit()
            result = await self._compiled_state_graph.ainvoke({"source_node_id": []},
                                                              config,
                                                              checkpoint_during=False)
        if result.get(INTERRUPT) is None:
            self._checkpoint_saver.delete_thread(self._thread_id)
        else:
            result = None

    async def stream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        async for chunk in self._compiled_state_graph.astream({"source_node_id": []}):
            yield chunk

    async def interrupt(self, message: dict):
        return
