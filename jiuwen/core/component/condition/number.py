#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Union

from jiuwen.core.component.condition.condition import Condition
from jiuwen.core.context.context import Context
from jiuwen.core.context.utils import NESTED_PATH_SPLIT


class NumberCondition(Condition):
    def __init__(self, node_id: str, limit: Union[str, int], index_path: str = None):
        super().__init__()
        self._index_path = index_path if index_path else node_id + NESTED_PATH_SPLIT + "index"
        self._limit = limit
        self._node_id = node_id

    def init(self):
        self._context.state.update_io({self._index_path: -1})
        self._context.state.commit()

    def __call__(self) -> bool:
        current_idx = self._context.state.get(self._index_path) + 1
        limit_num: int
        if isinstance(self._limit, int):
            limit_num = self._limit
        else:
            limit_num = self._context.state.get(self._limit)

        result = current_idx < limit_num
        if result:
            self._context.state.update_io({self._index_path: current_idx})

        return result
