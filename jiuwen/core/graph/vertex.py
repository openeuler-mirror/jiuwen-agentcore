#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from typing import Any, Optional

from jiuwen.core.common.exception.exception import JiuWenBaseException
from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Executable, Output
from jiuwen.core.graph.graph_state import GraphState

class Vertex:
    def __init__(self, node_id: str, executable: Executable = None):
        self._node_id = node_id
        self._executable = executable
        self._context: Context = None

    def init(self, context: Context) -> bool:
        self._context = context
        return True

    def __call__(self, state: GraphState) -> Output:
        if self._context is None:
            raise JiuWenBaseException(1, "vertex is not initialized, node is is %s", self._node_id)
        inputs = self.__pre_invoke__(state)
        is_stream = self.__is_stream__(state)
        try:
            if is_stream:
                result_iter = self._executable.stream(inputs, context=self._context)
                self.__post_stream__(result_iter)
            else:
                results = self._executable.invoke(inputs, context=self._context)
                self.__post_invoke__(results)
        except JiuWenBaseException as e:
            raise JiuWenBaseException(e.error_code, "failed to invoke, caused by " + e.message)
        return {"source": self._node_id}

    def __pre_invoke__(self, state:GraphState) -> Optional[dict]:
        inputs_schema = self._context.config.get_inputs_schema(self._node_id)
        inputs = self._context.state.get_inputs(inputs_schema)
        if self._context.tracer is not None:
            self.__trace_inputs__(inputs)
        return inputs

    def __post_invoke__(self, results: Optional[dict]) -> None:
        self._context.state.set_outputs(results)
        pass

    def __post_stream__(self, results_iter: Any) -> None:
        pass

    def __trace_inputs__(self, inputs: Optional[dict]) -> None:
        pass

    def __is_stream__(self, state: GraphState) -> bool:
        return False

