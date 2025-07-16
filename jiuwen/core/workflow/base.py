#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
import asyncio
from typing import Self, Dict, Any, Union, AsyncIterator, Iterator

from pydantic import BaseModel

from jiuwen.core.common.exception.exception import JiuWenBaseException
from jiuwen.core.common.logging.base import logger
from jiuwen.core.component.base import WorkflowComponent, StartComponent, EndComponent
from jiuwen.core.context.config import CompIOConfig, Transformer
from jiuwen.core.context.context import Context
from jiuwen.core.graph.base import Graph, Router
from jiuwen.core.graph.executable import Executable, Input, Output
from jiuwen.core.stream.base import StreamMode


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
        self._comp_io_configs: dict[str, CompIOConfig] = {}
        self._stream_edges: dict[str, list[str]] = dict()
        self._end_comp_id: str = ""

    def add_workflow_comp(
            self,
            comp_id: str,
            workflow_comp: Union[Executable, WorkflowComponent],
            *,
            wait_for_all: bool = False,
            inputs_schema: dict = None,
            outputs_schema: dict = None,
            inputs_transformer: Transformer = None,
            outputs_transformer: Transformer = None,

    ) -> Self:
        if not isinstance(workflow_comp, WorkflowComponent):
            workflow_comp = self._convert_to_component(workflow_comp)
        workflow_comp.add_component(graph=self._graph, node_id=comp_id, wait_for_all=wait_for_all)
        self._comp_io_configs[comp_id] = CompIOConfig(inputs_schema=inputs_schema, outputs_schema=outputs_schema,
                                                      inputs_transformer=inputs_transformer,
                                                      outputs_transformer=outputs_transformer)
        return self

    def set_start_comp(
            self,
            start_comp_id: str,
            component: StartComponent,
            inputs_schema: dict = None,
            outputs_schema: dict = None,
            inputs_transformer: Transformer = None,
            outputs_transformer: Transformer = None
    ) -> Self:
        self._graph.add_node(start_comp_id, component)
        self._graph.start_node(start_comp_id)
        self._comp_io_configs[start_comp_id] = CompIOConfig(inputs_schema=inputs_schema, outputs_schema=outputs_schema,
                                                            inputs_transformer=inputs_transformer,
                                                            outputs_transformer=outputs_transformer)
        return self

    def set_end_comp(
            self,
            end_comp_id: str,
            component: EndComponent,
            inputs_schema: dict = None,
            outputs_schema: dict = None,
            inputs_transformer: Transformer = None,
            outputs_transformer: Transformer = None
    ) -> Self:
        self._graph.add_node(end_comp_id, component)
        self._graph.end_node(end_comp_id)
        self._comp_io_configs[end_comp_id] = CompIOConfig(inputs_schema=inputs_schema, outputs_schema=outputs_schema,
                                                          inputs_transformer=inputs_transformer,
                                                          outputs_transformer=outputs_transformer)
        self._end_comp_id = end_comp_id
        return self

    def add_connection(self, src_comp_id: str, target_comp_id: str) -> Self:
        self._graph.add_edge(src_comp_id, target_comp_id)
        return self

    def add_stream_connection(self, src_comp_id: str, target_comp_id: str) -> Self:
        self._graph.add_edge(src_comp_id, target_comp_id)
        if target_comp_id not in self._stream_edges:
            self._stream_edges[src_comp_id] = [target_comp_id]
        else:
            self._stream_edges[src_comp_id].append(target_comp_id)
        return self

    def add_conditional_connection(self, src_comp_id: str, router: Router) -> Self:
        self._graph.add_conditional_edges(source_node_id=src_comp_id, router=router)
        return self

    async def invoke(self, inputs: Input, context: Context) -> Output:
        if not context.init(comp_configs=self._comp_io_configs, stream_edges=self._stream_edges,
                            workflow_config=self._workflow_config):
            return None
        logger.info("begin to invoke, input=%s", inputs)
        compiled_graph = self._graph.compile(context)
        await compiled_graph.invoke(inputs, context)
        results = context.state.get_outputs(self._end_comp_id)
        logger.info("end to invoke, results=%s", results)
        return results

    async def stream(
            self,
            inputs: Input,
            context: Context,
            stream_modes: list[StreamMode] = None
    ) -> AsyncIterator[WorkflowChunk]:
        if not context.init(comp_configs=self._comp_io_configs, stream_edges=self._stream_edges,
                            workflow_config=self._workflow_config, stream_modes=stream_modes):
            raise JiuWenBaseException(1, "failed to init context")
        compiled_graph = self._graph.compile(context)
        context.state.set_user_inputs(inputs)
        context.state.commit()

        async def stream_process():
            await compiled_graph.invoke(inputs, context)
            await context.stream_writer_manager.stream_emitter.close()

        asyncio.create_task(stream_process())
        async for chunk in context.stream_writer_manager.stream_output():
            yield chunk

    def _convert_to_component(self, executable: Executable) -> WorkflowComponent:
        pass
