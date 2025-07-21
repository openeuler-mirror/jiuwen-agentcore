#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
import asyncio
from typing import Self, Dict, Any, Union, AsyncIterator

from pydantic import BaseModel

from jiuwen.core.common.constants.constant import INTERACTION
from jiuwen.core.common.logging.base import logger
from jiuwen.core.component.base import WorkflowComponent, StartComponent, EndComponent
from jiuwen.core.context.config import CompIOConfig, Transformer
from jiuwen.core.context.context import Context
from jiuwen.core.graph.base import Graph, Router, INPUTS_KEY, CONFIG_KEY, ExecutableGraph
from jiuwen.core.graph.executable import Executable, Input, Output
from jiuwen.core.stream.base import StreamMode, BaseStreamMode
from jiuwen.core.stream.emitter import StreamEmitter
from jiuwen.core.stream.manager import StreamWriterManager
from jiuwen.core.stream.writer import OutputSchema
from jiuwen.core.tracer.tracer import Tracer
from jiuwen.core.workflow.workflow_config import WorkflowConfig


class WorkflowOutput(BaseModel):
    result: str


class WorkflowChunk(BaseModel):
    chunk_id: str
    payload: str
    metadata: Dict[str, Any]
    is_final: bool


class BaseWorkFlow:
    def __init__(self, workflow_config: WorkflowConfig, new_graph: Graph):
        self._graph = new_graph
        self._workflow_config = workflow_config

    def config(self):
        return self._workflow_config

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
        self._workflow_config.comp_configs[comp_id] = CompIOConfig(inputs_schema=inputs_schema,
                                                                   outputs_schema=outputs_schema,
                                                                   inputs_transformer=inputs_transformer,
                                                                   outputs_transformer=outputs_transformer)
        return self

    def start_comp(
            self,
            start_comp_id: str,
    ) -> Self:
        self._graph.start_node(start_comp_id)
        return self

    def end_comp(
            self,
            end_comp_id: str,
    ) -> Self:
        self._graph.end_node(end_comp_id)
        return self

    def add_connection(self, src_comp_id: str, target_comp_id: str) -> Self:
        self._graph.add_edge(src_comp_id, target_comp_id)
        return self

    def add_stream_connection(self, src_comp_id: str, target_comp_id: str) -> Self:
        self._graph.add_edge(src_comp_id, target_comp_id)
        if target_comp_id not in self._workflow_config.stream_edges:
            self._workflow_config.stream_edges[src_comp_id] = [target_comp_id]
        else:
            self._workflow_config.stream_edges[src_comp_id].append(target_comp_id)
        return self

    def add_conditional_connection(self, src_comp_id: str, router: Router) -> Self:
        self._graph.add_conditional_edges(source_node_id=src_comp_id, router=router)
        return self

    def compile(self, context: Context) -> ExecutableGraph:
        context.config.set_workflow_config(self._workflow_config)
        return self._graph.compile(context)


class Workflow(BaseWorkFlow):
    def __init__(self, workflow_config: WorkflowConfig, graph: Graph):
        super().__init__(workflow_config, graph)
        self._end_comp_id: str = ""

    def set_start_comp(
            self,
            start_comp_id: str,
            component: StartComponent,
            inputs_schema: dict = None,
            outputs_schema: dict = None,
            inputs_transformer: Transformer = None,
            outputs_transformer: Transformer = None
    ) -> Self:
        self.add_workflow_comp(start_comp_id, component, wait_for_all=False, inputs_schema=inputs_schema,
                               outputs_schema=outputs_schema,
                               inputs_transformer=inputs_transformer,
                               outputs_transformer=outputs_transformer)
        self.start_comp(start_comp_id)
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
        self.add_workflow_comp(end_comp_id, component, wait_for_all=False, inputs_schema=inputs_schema,
                               outputs_schema=outputs_schema,
                               inputs_transformer=inputs_transformer,
                               outputs_transformer=outputs_transformer)
        self.end_comp(end_comp_id)
        self._end_comp_id = end_comp_id
        return self

    async def sub_invoke(self, inputs: Input, context: Context, config: Any = None) -> Output:
        logger.info("begin to sub_invoke, input=%s", inputs)
        context.config.set_workflow_config(self._workflow_config)
        compiled_graph = self._graph.compile(context)
        await compiled_graph.invoke({INPUTS_KEY: inputs, CONFIG_KEY: config}, context)
        results = context.state.get_outputs(self._end_comp_id)
        logger.info("end to sub_invoke, results=%s", results)
        return results

    async def invoke(self, inputs: Input, context: Context) -> Output:
        logger.info("begin to invoke, input=%s", inputs)
        chunks = []
        async for chunk in self.stream(inputs, context):
            chunks.append(chunk)

        results = chunks[-1].model_dump() if (len(chunks) > 1 and isinstance(chunks[-1], OutputSchema) and
                                              chunks[-1].type == INTERACTION) else context.state.get_outputs(
            self._end_comp_id)
        logger.info("end to invoke, results=%s", results)
        return results

    async def stream(
            self,
            inputs: Input,
            context: Context,
            stream_modes: list[StreamMode] = None
    ) -> AsyncIterator[WorkflowChunk]:
        context.set_stream_writer_manager(StreamWriterManager(stream_emitter=StreamEmitter(), modes=stream_modes))
        if context.tracer is None and (stream_modes is None or BaseStreamMode.TRACE in stream_modes):
            tracer = Tracer()
            tracer.init(context.stream_writer_manager, context.callback_manager)
            context.set_tracer(tracer)
        compiled_graph = self.compile(context)

        async def stream_process():
            try:
                await compiled_graph.invoke({INPUTS_KEY: inputs, CONFIG_KEY: None}, context)
            finally:
                await context.stream_writer_manager.stream_emitter.close()

        task = asyncio.create_task(stream_process())
        async for chunk in context.stream_writer_manager.stream_output():
            yield chunk

        try:
            await task
        except Exception:
            raise

    def _convert_to_component(self, executable: Executable) -> WorkflowComponent:
        pass
