#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from copy import deepcopy
from typing import Union, Optional, Any, Callable

from jiuwen.core.common.exception.exception import JiuWenBaseException
from jiuwen.core.context.state import Transformer
from jiuwen.core.context.state import CommitState, StateLike, State
from jiuwen.core.context.utils import update_dict, get_by_schema


class InMemoryStateLike(StateLike):
    def __init__(self):
        self._state: dict = dict()

    def get(self, key: Union[str, list, dict]) -> Optional[Any]:
        return get_by_schema(key, self._state)

    def get_by_transformer(self, transformer: Callable) -> Optional[Any]:
        return transformer(self._state)

    def update(self, node_id: str, data: dict) -> None:
        if node_id is None:
            raise JiuWenBaseException(1, "can not update state by none node_id")
        update_dict(data, self._state)


class InMemoryCommitState(CommitState):
    def __init__(self):
        self._state = InMemoryStateLike()
        self._updates: dict[str, list[dict]] = dict()

    def update(self, node_id: str, data: dict) -> None:
        if node_id is None:
            raise JiuWenBaseException(1, "can not update state by none node_id")
        if node_id not in self._updates:
            self._updates[node_id] = []
        self._updates[node_id].append(data)

    def commit(self) -> None:
        for key, updates in self._updates.items():
            for update in updates:
                self._state.update(key, update)
        self._updates.clear()

    def get_updates(self, node_id: str) -> list[dict]:
        if node_id is None:
            return [{"node_id": deepcopy(node), "updates": deepcopy(update)} for node, update in self._updates.items()]
        if node_id not in self._updates:
            return []
        return [{"node_id": node_id, "updates": deepcopy(self._updates[node_id])}]

    def rollback(self, node_id: str) -> None:
        self._updates[node_id] = []

    def get_by_transformer(self, transformer: Transformer) -> Optional[Any]:
        return transformer(self._state)

    def get(self, key: Union[str, list, dict]) -> Optional[Any]:
        return self._state.get(key)

class InMemoryState(State):
    def __init__(self):
        super().__init__(io_state=InMemoryCommitState(),
                         global_state=InMemoryCommitState(),
                         trace_state=dict(),
                         comp_state=InMemoryCommitState())


