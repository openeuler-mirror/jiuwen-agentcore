#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Union

from jiuwen.core.component.condition.condition import Condition, INDEX
from jiuwen.core.context.utils import NESTED_PATH_SPLIT


class NumberCondition(Condition):
    def __init__(self, node_id: str, limit: Union[str, int]):
        super().__init__()
        self._index_path = node_id + NESTED_PATH_SPLIT + INDEX
        self._limit = limit
        self._node_id = node_id

    def init(self):
        pass

    def __call__(self) -> bool:
        current_idx = self._context.state().get(self._index_path) + 1
        limit_num: int
        if isinstance(self._limit, int):
            limit_num = self._limit
        else:
            limit_num = self._context.state().get(self._limit)

        return current_idx < limit_num
