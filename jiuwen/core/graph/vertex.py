#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from typing import Any, Optional

from jiuwen.core.common.exception.exception import JiuWenBaseException
from jiuwen.core.common.logging.base import logger
from jiuwen.core.component.condition.condition import INDEX
from jiuwen.core.component.loop_callback.loop_id import LOOP_ID
from jiuwen.core.component.workflow_comp import ExecWorkflowComponent
from jiuwen.core.context.context import Context, NodeContext
from jiuwen.core.context.utils import get_by_schema, NESTED_PATH_SPLIT
from jiuwen.core.graph.base import INPUTS_KEY, CONFIG_KEY
from jiuwen.core.graph.executable import Executable, Output
from jiuwen.core.graph.graph_state import GraphState


class Vertex:
    def __init__(self, node_id: str, executable: Executable = None):
        self._node_id = node_id
        self._executable = executable
        self._context: NodeContext = None

    def init(self, context: Context) -> bool:
        self._context = NodeContext(context, self._node_id)
        return True

    async def __call__(self, state: GraphState, config: Any = None) -> Output:
        if self._context is None or self._executable is None:
            raise JiuWenBaseException(1, "vertex is not initialized, node is is " + self._node_id)
        inputs = await self.__pre_invoke__()
        logger.info("vertex[%s] inputs %s", self._context.executable_id(), inputs)
        is_stream = self.__is_stream__(state)
        if self._executable.graph_invoker():
            inputs = {INPUTS_KEY: inputs, CONFIG_KEY: config}

        try:
            if is_stream:
                result_iter = await self._executable.stream(inputs, context=self._context)
                self.__post_stream__(result_iter)
            else:
                results = await self._executable.invoke(inputs, context=self._context)
                outputs = await self.__post_invoke__(results)
                logger.info("vertex[%s] outputs %s", self._context.executable_id(), outputs)
        except JiuWenBaseException as e:
            raise JiuWenBaseException(e.error_code, "failed to invoke, caused by " + e.message)
        return {"source_node_id": [self._node_id]}

    async def __pre_invoke__(self) -> Optional[dict]:
        inputs_transformer = self._context.config().get_input_transformer(self._node_id)
        if inputs_transformer is None:
            inputs_schema = self._context.config().get_inputs_schema(self._node_id)
            inputs = self._context.state().get_io(inputs_schema)
        else:
            inputs = self._context.state().get_inputs_by_transformer(inputs_transformer)
        if self._context.tracer() is not None:
            await self.__trace_inputs__(inputs)
        return inputs

    async def __post_invoke__(self, results: Optional[dict]) -> Any:
        output_transformer = self._context.config().get_output_transformer(self._node_id)
        if output_transformer is None:
            output_schema = self._context.config().get_outputs_schema(self._node_id)
            results = get_by_schema(output_schema, results) if output_schema else results
        else:
            results = output_transformer(results)
        self._context.state().set_outputs(self._node_id, results)
        if self._context.tracer() is not None:
            await self.__trace_outputs__(results)
        return results

    def __post_stream__(self, results_iter: Any) -> None:
        pass

    async def __trace_inputs__(self, inputs: Optional[dict]) -> None:
        if self._executable.skip_trace():
            return
        # TODO 组件信息
        await self._context.tracer().trigger("tracer_workflow", "on_pre_invoke", invoke_id=self._context.executable_id(),
                                           parent_node_id=self._context.parent_id(),
                                           inputs=inputs,
                                           component_metadata=self._get_component_metadata())
        self._context.state().update_trace(self._context.tracer().get_workflow_span(self._context.executable_id(),
                                                                                self._context.parent_id()))

        if isinstance(self._executable, ExecWorkflowComponent):
            self._context.tracer().register_workflow_span_manager(self._context.executable_id())

    async def __trace_outputs__(self, outputs: Optional[dict] = None) -> None:
        if self._executable.skip_trace():
            return
        await self._context.tracer().trigger("tracer_workflow", "on_post_invoke", invoke_id=self._context.executable_id(),
                                           parent_node_id=self._context.parent_id(),
                                           outputs=outputs)
        self._context.state().update_trace(self._context.tracer().get_workflow_span(self._context.executable_id(),
                                                                                self._context.parent_id()))

    def _get_component_metadata(self) -> dict:
        component_metadata = {"component_type": self._context.executable_id()}
        loop_id = self._context.state().get(LOOP_ID)
        if loop_id:
            index = self._context.state().get(loop_id + NESTED_PATH_SPLIT + INDEX)
            component_metadata.update({
                "loop_node_id": loop_id,
                "loop_index": index + 1
            })
            self._context.tracer().pop_workflow_span(self._context.executable_id(), self._context.parent_id())
        return component_metadata

    def __is_stream__(self, state: GraphState) -> bool:
        return False
