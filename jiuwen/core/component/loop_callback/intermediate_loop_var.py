#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Union, Any

from jiuwen.core.component.loop_callback.loop_callback import LoopCallback, INTERMEDIATE_LOOP_VAR
from jiuwen.core.context.utils import NESTED_PATH_SPLIT, is_ref_path, extract_origin_key


class IntermediateLoopVarCallback(LoopCallback):
    def __init__(self, node_id: str, intermediate_loop_var: dict[str, Union[str, Any]]):
        super().__init__()
        self._intermediate_loop_var = intermediate_loop_var
        self._intermediate_loop_var_root = node_id + NESTED_PATH_SPLIT + INTERMEDIATE_LOOP_VAR

    def first_in_loop(self):
        for key, value in self._intermediate_loop_var.items():
            path = self._intermediate_loop_var_root + NESTED_PATH_SPLIT + key
            updates: Any
            if isinstance(value, str):
                if is_ref_path(value):
                    ref_str = extract_origin_key(value)
                    update = self._context.state().get(ref_str)
                else:
                    update = value
            else:
                update = value
            self._context.state().update_io({path: update})

    def out_loop(self):
        self._context.state().update_io({self._intermediate_loop_var_root: {}})

    def start_round(self):
        pass

    def end_round(self):
        pass
