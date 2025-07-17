#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any

from jiuwen.core.component.loop_callback.loop_callback import LoopCallback
from jiuwen.core.context.context import Context
from jiuwen.core.context.utils import is_ref_path, extract_origin_key, NESTED_PATH_SPLIT


class OutputCallback(LoopCallback):
    def __init__(self, node_id: str, outputs_format: dict[str, Any], round_result_root: str = None,
                 result_root: str = None, intermediate_loop_var_root: str = None):
        super().__init__()
        self._node_id = node_id
        self._outputs_format = outputs_format
        self._round_result_root = round_result_root if round_result_root else node_id + NESTED_PATH_SPLIT + "round"
        self._result_root = result_root if result_root else node_id
        self._intermediate_loop_var_root = intermediate_loop_var_root if intermediate_loop_var_root else node_id + NESTED_PATH_SPLIT + "intermediateLoopVar"

    def _generate_results(self, results: list[(str, Any)]):
        for key, value in self._outputs_format.items():
            if isinstance(value, str) and is_ref_path(value):
                ref_str = extract_origin_key(value)
                results.append((ref_str, None))
            elif isinstance(value, dict):
                self._generate_results(results)

    def first_in_loop(self):
        _results: list[(str, Any)] = []
        self._generate_results(_results)
        self._context.state.update({self._round_result_root: _results})

    def out_loop(self):
        results: list[(str, Any)] = self._context.state.get(self._round_result_root)
        if not isinstance(results, list):
            raise RuntimeError("error results in loop process")
        for (path, value) in results:
            self._context.state.update_io({path: value})
        self._context.state.commit()
        result = self._context.state.get_io(self._outputs_format)
        self._context.state.update({self._round_result_root: {}})
        self._context.state.set_outputs(self._node_id, result)

    def start_round(self):
        pass

    def end_round(self):
        results: list[(str, Any)] = self._context.state.get(self._round_result_root)
        if not isinstance(results, list):
            raise RuntimeError("error results in round process")
        for value in results:
            path = value[0]
            if path.startswith(self._intermediate_loop_var_root):
                value[1] = self._context.state.get(path)
            elif isinstance(value, list):
                if value[1] is None:
                    value[1] = []
                value[1].append(self._context.state.get(path))
            else:
                raise RuntimeError("error process in loop: " + path + ", " + str(value))
        self._context.state.update({self._round_result_root: results})
