#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import uuid
from typing import Union, Self, AsyncIterator, Any, Callable

from langgraph.constants import INTERRUPT
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.pregel.loop import PregelLoop

from jiuwen.core.common.constants.constant import INTERACTIVE_INPUT
from jiuwen.core.context.context import Context
from jiuwen.core.graph.base import Graph, Router, ExecutableGraph
from jiuwen.core.graph.executable import Executable, Input, Output
from jiuwen.core.graph.graph_state import GraphState
from jiuwen.core.graph.interrupt.interactive_input import InteractiveInput
from jiuwen.core.graph.vertex import Vertex
from jiuwen.graph.checkpoint.memory import InMemoryCheckpointer


class AfterProcessor:
    def __init__(self, after_tick: Callable[..., Any]):
        self._after_tick = after_tick

    def after_tick(self, loop: PregelLoop, context: Context) -> None:
        context.state.commit()
        return self._after_tick(loop)


after_processor: AfterProcessor = AfterProcessor(PregelLoop.after_tick)


def after_tick(self) -> None:
    context = self.checkpointer.ctx
    return after_processor.after_tick(self, context)


PregelLoop.after_tick = after_tick


class PregelGraph(Graph):

    def __init__(self):
        self.pregel: StateGraph = StateGraph(GraphState)
        self.compiledStateGraph = None
        self.edges: list[Union[str, list[str]], str] = []
        self.waits: set[str] = set()
        self.nodes: list[Vertex] = []
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
            self.checkpoint_saver = InMemoryCheckpointer()
            self.compiledStateGraph = self.pregel.compile(checkpointer=self.checkpoint_saver)

        self.checkpoint_saver.register_context(context)
        return CompiledGraph(self.compiledStateGraph, self.checkpoint_saver)

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
    def __init__(self, compiled_state_graph: CompiledStateGraph,
                 checkpoint_saver: InMemoryCheckpointer) -> None:
        self._compiled_state_graph = compiled_state_graph
        self._checkpoint_saver = checkpoint_saver

    async def _invoke(self, inputs: Input, context: Context, config: Any = None) -> Output:
        is_main = False
        if config is None:
            is_main = True
            config = {"configurable": {"thread_id": context.session_id}}

            if isinstance(inputs, InteractiveInput) and self._checkpoint_saver:
                self._checkpoint_saver.register_context(context)
                self._checkpoint_saver.register_input(inputs)

                self._checkpoint_saver.recover(config)
            else:
                context.state.set_user_inputs(inputs)
                context.state.commit()
        graph_inputs = None if isinstance(inputs, InteractiveInput) else {"source_node_id": []}

        try:
            result = await self._compiled_state_graph.ainvoke(graph_inputs,
                                                              config=config,
                                                              checkpoint_during=False)
        except:
            if is_main:
                self._checkpoint_saver.save(config)
            raise

        if result.get(INTERRUPT) is None and self._checkpoint_saver:
            executable_context = context.create_executable_context("")
            executable_context.state.update_comp({INTERACTIVE_INPUT: None})
            executable_context.state.commit()
            self._checkpoint_saver.delete_thread(context.session_id)
        else:
            if is_main:
                self._checkpoint_saver.save(config)

    async def stream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        async for chunk in self._compiled_state_graph.astream({"source_node_id": []}):
            yield chunk

    async def interrupt(self, message: dict):
        return
