#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Union, Any

from jiuwen.core.common.constants.constant import BPMN_VARIABLE_POOL_SEPARATOR
from jiuwen.core.component.loop_callback.loop_callback import LoopCallback


class IntermediateLoopVarCallback(LoopCallback):
    def __init__(self, context: Context, node_id: str,
                 intermediate_loop_var: dict[str, Union[str, Any]], intermediate_loop_var_root: str = None):
        self._context = context
        self._intermediate_loop_var = intermediate_loop_var
        self._intermediate_loop_var_root = intermediate_loop_var_root if intermediate_loop_var_root \
            else node_id + BPMN_VARIABLE_POOL_SEPARATOR + "intermediateLoopVar"

    def first_in_loop(self):
        for key, value in self._intermediate_loop_var.items():
            path = self._intermediate_loop_var_root + BPMN_VARIABLE_POOL_SEPARATOR + key
            updates: Any
            if isinstance(value, str):
                ref_str = get_ref_str(value)
                if ref_str != "":
                    update = self._context.store.read(ref_str)
                else:
                    update = value
            else:
                update = value
            self._context.store.write(path, update)

    def out_loop(self):
        self._context.store.write(self._intermediate_loop_var_root, {})

    def start_round(self):
        pass

    def end_round(self):
        pass
