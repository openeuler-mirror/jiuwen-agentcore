#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Union, Any

from jiuwen.core.component.condition.condition import Condition
from jiuwen.core.context.context import Context
from jiuwen.core.context.utils import extract_origin_key, NESTED_PATH_SPLIT

DEFAULT_MAX_LOOP_NUMBER = 1000


class ArrayCondition(Condition):
    def __init__(self, context: Context, node_id: str, arrays: dict[str, Union[str, list[Any]]], index_path: str = None,
                 array_root: str = None):
        self._context = context
        self._node_id = node_id
        self._arrays = arrays
        self._index_path = index_path if index_path else node_id + NESTED_PATH_SPLIT + "index"
        self._arrays_root = array_root if array_root else node_id + NESTED_PATH_SPLIT + "arrLoopVar"

    def init(self):
        self._context.state.update(self._node_id, {self._index_path: 0})
        self._context.state.update(self._node_id, {self._arrays_root: {}})

    def __call__(self) -> bool:
        current_idx = self._context.state.get(self._index_path)
        min_length = DEFAULT_MAX_LOOP_NUMBER
        updates: dict[str, Any] = {}
        for key, array_info in self._arrays.items():
            key_path = self._arrays_root + NESTED_PATH_SPLIT + key
            arr: list[Any] = []
            if isinstance(array_info, list):
                arr = array_info
            elif isinstance(array_info, str):
                ref_str = extract_origin_key(array_info)
                if ref_str != "":
                    arr = self._context.state.get(ref_str)
                else:
                    raise RuntimeError("error value: " + array_info + " is not a array path")
            else:
                raise RuntimeError("error value: " + array_info + " is not a array or a array path")
            min_length = min(len(arr), min_length)
            if current_idx >= min_length:
                return False
            updates[key_path] = arr[current_idx]

        self._context.state.update(self._node_id, {self._index_path: current_idx + 1})
        for path, update in updates.items():
            self._context.state.update(self._node_id, update)

        return True
