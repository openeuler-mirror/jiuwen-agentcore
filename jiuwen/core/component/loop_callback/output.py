#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any

from jiuwen.core.common.constants.constant import BPMN_VARIABLE_POOL_SEPARATOR
from jiuwen.core.component.loop_callback.loop_callback import LoopCallback


class OutputCallback(LoopCallback):
    def __init__(self, context: Context, node_id: str, outputs_format: dict[str, Any],
                 round_result_root: str = None, result_root: str = None, intermediate_loop_var_root: str = None):
        self._context = context
        self._outputs_format = outputs_format
        self._round_result_root = round_result_root if round_result_root else node_id + BPMN_VARIABLE_POOL_SEPARATOR + "round"
        self._result_root = result_root if result_root else node_id
        self._intermediate_loop_var_root = intermediate_loop_var_root if intermediate_loop_var_root else node_id + BPMN_VARIABLE_POOL_SEPARATOR + "intermediateLoopVar"

    def _generate_results(self, results: dict[str, list[Any]]):
        for key, value in self._outputs_format.items():
            if isinstance(value, str):
                ref_str = get_ref_str(value)
                if ref_str != "":
                    results[ref_str] = []
            elif isinstance(value, dict):
                self._generate_results(results)

    def first_in_loop(self):
        _results: dict[str, list[Any]] = {}
        self._generate_results(_results)
        self._context.store.write(self._round_result_root, _results)

    def out_loop(self):
        results: dict[str, list[Any]] = self._context.store.read(self._round_result_root)
        if not isinstance(results, dict):
            raise RuntimeError("error results in loop process")
        for path, array in results.items():
            self._context.store.write(path, array)
        result = filter_input(self._outputs_format, self._context.store)
        self._context.store.write(self._round_result_root, {})
        set_output(result, self._result_root, self._context.store)

    def start_round(self):
        pass

    def end_round(self):
        results: dict[str, list[Any]] = self._context.store.read(self._round_result_root)
        if not isinstance(results, dict):
            raise RuntimeError("error results in round process")
        for path, value in results.items():
            if path.startswith(self._intermediate_loop_var_root):
                results[path] = self._context.store.read(path)
            elif isinstance(value, list):
                value.append(self._context.store.read(path))
            else:
                raise RuntimeError("error process in loop: " + path + ", " + str(value))
        self._context.store.write(self._round_result_root, results)
