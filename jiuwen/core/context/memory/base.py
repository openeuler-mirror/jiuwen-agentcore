#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from copy import deepcopy
from typing import Union, Optional, Any, Callable

from jiuwen.core.common.exception.exception import JiuWenBaseException
from jiuwen.core.context.state import CommitState, StateLike, State
from jiuwen.core.context.utils import extract_origin_key, get_value_by_nested_path, update_dict


class InMemoryStateLike(StateLike):
    def __init__(self):
        self._state: dict = dict()

    def get(self, key: Union[str, list, dict]) -> Optional[Any]:
        if isinstance(key, str):
            origin_key = extract_origin_key(key)
            return get_value_by_nested_path(origin_key, self._state)
        elif isinstance(key, dict):
            result = {}
            for target_key, target_schema in key.items():
                result[target_key] = self.get(target_schema)
            return result
        elif isinstance(key, list):
            result = []
            for item in key:
                result.append(self.get(item))
            return result
        else:
            raise JiuWenBaseException(1, "key type is not support")

    def get_by_transformer(self, transformer: Callable) -> Optional[Any]:
        return transformer(self._state)

    def update(self, node_id: str, data: dict) -> None:
        update_dict(self._state, data)


class InMemoryCommitState(CommitState):
    def __init__(self):
        self._state = InMemoryStateLike()
        self._updates: dict[str, list[dict]] = dict()

    def update(self, node_id: str, data: dict) -> None:
        if node_id not in self._updates:
            self._updates[node_id] = []
        self._updates[node_id].append(data)

    def commit(self) -> None:
        for key, updates in self._updates.items():
            for update in updates:
                self._state.update(key, update)
        self._updates.clear()

    def get_updates(self, node_id: str) -> list[dict]:
        if node_id not in self._updates:
            return []
        return deepcopy(self._updates[node_id])

    def rollback(self, failed_node_ids: list[str]) -> None:
        for node_id in failed_node_ids:
            self._updates[node_id] = []

    def get_by_transformer(self, transformer: Callable) -> Optional[Any]:
        return transformer(self._state)

    def get(self, key: Union[str, list, dict]) -> Optional[Any]:
        return self._state.get(key)

class InMemoryState(State):
    def __init__(self):
        super().__init__(io_state=InMemoryCommitState(),
                         global_state=InMemoryCommitState(),
                         trace_state=InMemoryStateLike(),
                         comp_state=InMemoryStateLike())


