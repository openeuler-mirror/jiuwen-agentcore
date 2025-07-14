#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from abc import ABC, abstractmethod
from typing import Any, Union, Optional, Callable


class StateLike(ABC):
    @abstractmethod
    def get(self, key: Union[str, list, dict]) -> Optional[Any]:
        pass

    @abstractmethod
    def get_by_transformer(self, transformer: Callable) -> Optional[Any]:
        pass

    @abstractmethod
    def update(self, node_id: str, data: dict) -> None:
        pass

class CommitState(StateLike):
    @abstractmethod
    def commit(self) -> None:
        pass

    @abstractmethod
    def rollback(self, failed_node_ids: list[str]) -> None:
        pass

    @abstractmethod
    def get_updates(self, node_id: str) -> list[dict]:
        pass

class State(ABC):
    def __init__(
            self,
            io_state: CommitState,
            global_state: CommitState,
            trace_state: StateLike,
            comp_state: StateLike
    ):
        self._io_state = io_state
        self._global_state = global_state
        self._trace_state = trace_state
        self._comp_state = comp_state

    @property
    def io_state(self) -> CommitState:
        return self._io_state

    @property
    def trace_state(self) -> StateLike:
        return self._trace_state

    @property
    def global_state(self) -> CommitState:
        return self._global_state

    @property
    def comp_state(self) -> StateLike:
        return self._comp_state

    def get(self, key: Union[str, dict]) -> Optional[Any]:
        if self._global_state is None:
            return None
        return self._global_state.get(key)

    def update(self, node_id: str, data: dict) -> None:
        if self._global_state is None:
            return
        self._global_state.update(node_id, data)

    def update_io(self, node_id: str, data: dict) -> None:
        if self._io_state is None:
            return
        self._io_state.update(node_id, data)

    def update_trace(self, node_id: str, data: dict) -> None:
        if self._trace_state is None:
            return
        self._trace_state.update(node_id, data)

    def update_comp(self, node_id: str, data: dict) -> None:
        if self._comp_state is None:
            return
        self._comp_state.update(node_id, data)

    def set_user_inputs(self, inputs: dict) -> None:
        if self._io_state is None:
            return
        self._io_state.update({"user": {"inputs": inputs}})

    def get_inputs(self, input_schemas: dict) -> dict:
        if self._io_state is None:
            return {}
        return self._io_state.get(input_schemas)

    def get_outputs(self, node_id: str) -> Any:
        if self._io_state is None:
            return {}
        return self._io_state.get(node_id)

    def set_outputs(self, node_id: str, outputs: dict) -> None:
        if self._io_state is None:
            return
        return self._io_state.update(node_id, outputs)

