#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
import asyncio
from dataclasses import dataclass, Field
from enum import Enum
from functools import partial
from typing import Self, Dict, Any, Union, AsyncIterator, Iterator

from pydantic import BaseModel

from jiuwen.core.common.exception.exception import JiuWenBaseException
from jiuwen.core.component.base import WorkflowComponent, StartComponent, EndComponent
from jiuwen.core.context.context import Context
from jiuwen.core.graph.base import Graph, Router
from jiuwen.core.graph.executable import Executable, Input, Output


class WorkflowConfig(BaseModel):
    metadata: BaseModel


class WorkflowOutput(BaseModel):
    result: str


class WorkflowChunk(BaseModel):
    chunk_id: str
    payload: str
    metadata: Dict[str, Any]
    is_final: bool


class Workflow:
    def __init__(self, workflow_config: WorkflowConfig, graph: Graph = None):
        self._graph = graph
        self._workflow_config = workflow_config
        self._comp_io_schemas: dict[str, tuple[dict, dict]] = dict()
        self._stream_edges: dict[str, list[str]] = dict()
        self._end_comp_id: str = ""

    def add_workflow_comp(
            self,
            comp_id: str,
            workflow_comp: Union[Executable, WorkflowComponent],
            *,
            wait_for_all: bool = False,
            inputs_schema: dict = None,
            outputs_schema: dict = None
    ) -> Self:
        if not isinstance(workflow_comp, WorkflowComponent):
            workflow_comp = self._convert_to_component(workflow_comp)
        workflow_comp.add_component(graph=self._graph, node_id=comp_id, wait_for_all=wait_for_all)
        self._comp_io_schemas[comp_id] = (inputs_schema, outputs_schema)
        return self

    def set_start_comp(
            self,
            start_comp_id: str,
            component: StartComponent,
            inputs_schema: dict = None,
            output_schema: dict = None
    ) -> Self:
        self._graph.add_node(start_comp_id, component)
        self._graph.start_node(start_comp_id)
        self._comp_io_schemas[start_comp_id] = (inputs_schema, output_schema)
        return self

    def set_end_comp(
            self,
            end_comp_id: str,
            component: EndComponent,
            inputs_schema: dict = None,
            output_schema: dict = None
    ) -> Self:
        self._graph.add_node(end_comp_id, component)
        self._graph.end_node(end_comp_id)
        self._comp_io_schemas[end_comp_id] = (inputs_schema, output_schema)
        self._end_comp_id = end_comp_id
        return self

    def add_connection(self, src_comp_id: str, target_comp_id: str) -> Self:
        self._graph.add_edge(source_node_id=src_comp_id, target_node_id=target_comp_id)
        return self

    def add_stream_connection(self, src_comp_id: str, target_comp_id: str) -> Self:
        self._graph.add_edge(source_node_id=src_comp_id, target_node_id=target_comp_id)
        if target_comp_id not in self._stream_edges:
            self._stream_edges[src_comp_id] = [target_comp_id]
        else:
            self._stream_edges[src_comp_id].append(target_comp_id)
        return self

    def add_conditional_connection(self, src_comp_id: str, router: Router) -> Self:
        self._graph.add_conditional_edges(source_node_id=src_comp_id, router=router)
        return self

    def invoke(self, inputs: Input, context: Context) -> Output:
        if not context.init(io_schemas=self._comp_io_schemas, stream_edges=self._stream_edges,
                            workflow_config=self._workflow_config):
            return None
        compiled_graph = self._graph.compile(context)
        context.state.set_user_inputs(inputs)
        compiled_graph.invoke(inputs, context)
        return context.state.get_outputs(self._end_comp_id)

    async def ainvoke(self, inputs: Input, context: Context) -> Output:
        return await asyncio.get_running_loop().run_in_executor(
            None, partial(self.invoke, context), inputs
        )

    def stream(
            self,
            inputs: Input,
            context: Context,
            stream_modes: list[str] = None
    ) -> Iterator[WorkflowChunk]:
        if not context.init(io_schemas=self._comp_io_schemas, stream_edges=self._stream_edges,
                            workflow_config=self._workflow_config, stream_modes=stream_modes):
            raise JiuWenBaseException(1, "failed to init context")
        compiled_graph = self._graph.compile(context)
        context.state.set_user_inputs(inputs)
        yield from compiled_graph.stream(inputs, context)

    async def astream(
            self,
            inputs: Input,
            context: Context,
            stream_modes: list[str] = None
    ) -> AsyncIterator[WorkflowChunk]:
        if not context.init(io_schemas=self._comp_io_schemas, stream_edges=self._stream_edges,
                            workflow_config=self._workflow_config, stream_modes=stream_modes):
            raise JiuWenBaseException(1, "failed to init context")
        compiled_graph = self._graph.compile(context)
        context.state.set_user_inputs(inputs)
        yield await compiled_graph.astream(inputs, context)

    def _convert_to_component(self, executable: Executable) -> WorkflowComponent:
        pass
