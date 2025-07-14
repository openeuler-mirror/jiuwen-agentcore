#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Union, Any

from jiuwen.core.common.constants.constant import BPMN_VARIABLE_POOL_SEPARATOR
from jiuwen.core.component.condition.condition import Condition
from jiuwen.core.context.context import Context

DEFAULT_MAX_LOOP_NUMBER = 1000


class ArrayCondition(Condition):
    def __init__(self, context: Context, node_id: str, arrays: dict[str, Union[str, list[Any]]], index_path: str = None,
                 array_root: str = None):
        self._context = context
        self._arrays = arrays
        self._index_path = index_path if index_path else node_id + BPMN_VARIABLE_POOL_SEPARATOR + "index"
        self._arrays_root = array_root if array_root else node_id + BPMN_VARIABLE_POOL_SEPARATOR + "arrLoopVar"

    def init(self):
        self._context.store.write(self._index_path, 0)
        self._context.store.write(self._arrays_root, {})

    def __call__(self) -> bool:
        current_idx = self._context.store.read(self._index_path)
        min_length = DEFAULT_MAX_LOOP_NUMBER
        updates: dict[str, Any] = {}
        for key, array_info in self._arrays.items():
            key_path = self._arrays_root + BPMN_VARIABLE_POOL_SEPARATOR + key
            arr: list[Any] = []
            if isinstance(array_info, list):
                arr = array_info
            elif isinstance(array_info, str):
                ref_str = get_ref_str(array_info)
                if ref_str != "":
                    arr = self._context.store.read(ref_str)
                else:
                    raise RuntimeError("error value: " + array_info + " is not a array path")
            else:
                raise RuntimeError("error value: " + array_info + " is not a array or a array path")
            min_length = min(len(arr), min_length)
            if current_idx >= min_length:
                return False
            updates[key_path] = arr[current_idx]

        self._context.store.write(self._index_path, current_idx + 1)
        for path, update in updates.items():
            self._context.store.write(path, update)

        return True
