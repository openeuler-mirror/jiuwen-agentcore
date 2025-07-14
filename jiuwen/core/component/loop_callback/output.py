#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any

from jiuwen.core.component.loop_callback.loop_callback import LoopCallback
from jiuwen.core.context.context import Context
from jiuwen.core.context.utils import is_ref_path, extract_origin_key, NESTED_PATH_SPLIT


class OutputCallback(LoopCallback):
    def __init__(self, context: Context, node_id: str, outputs_format: dict[str, Any],
                 round_result_root: str = None, result_root: str = None, intermediate_loop_var_root: str = None):
        self._node_id = node_id
        self._context = context
        self._outputs_format = outputs_format
        self._round_result_root = round_result_root if round_result_root else node_id + NESTED_PATH_SPLIT + "round"
        self._result_root = result_root if result_root else node_id
        self._intermediate_loop_var_root = intermediate_loop_var_root if intermediate_loop_var_root else node_id + NESTED_PATH_SPLIT + "intermediateLoopVar"

    def _generate_results(self, results: dict[str, list[Any]]):
        for key, value in self._outputs_format.items():
            if isinstance(value, str) and is_ref_path(value):
                ref_str = extract_origin_key(value)
                results[ref_str] = []
            elif isinstance(value, dict):
                self._generate_results(results)

    def first_in_loop(self):
        _results: dict[str, list[Any]] = {}
        self._generate_results(_results)
        self._context.state.update(self._round_result_root, _results)

    def out_loop(self):
        results: dict[str, list[Any]] = self._context.state.get(self._round_result_root)
        if not isinstance(results, dict):
            raise RuntimeError("error results in loop process")
        for path, array in results.items():
            self._context.state.update(self._node_id, {path: array})
        result = self._context.state.get_inputs(self._outputs_format)
        self._context.state.update(self._node_id, {self._round_result_root : {}})
        self._context.state.set_outputs(self._node_id, {self._result_root : result})

    def start_round(self):
        pass

    def end_round(self):
        results: dict[str, list[Any]] = self._context.state.get(self._round_result_root)
        if not isinstance(results, dict):
            raise RuntimeError("error results in round process")
        for path, value in results.items():
            if path.startswith(self._intermediate_loop_var_root):
                results[path] = self._context.state.get(path)
            elif isinstance(value, list):
                value.append(self._context.state.get(path))
            else:
                raise RuntimeError("error process in loop: " + path + ", " + str(value))
        self._context.state.update(self._node_id, {self._round_result_root : results})
