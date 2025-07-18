#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
import uuid
from abc import ABC, abstractmethod
from typing import Any, Union, Optional, Callable, Self

from jiuwen.core.common.logging.base import logger


class ReadableStateLike(ABC):
    @abstractmethod
    def get(self, key: Union[str, list, dict]) -> Optional[Any]:
        pass


Transformer = Callable[[ReadableStateLike], Any]


class StateLike(ReadableStateLike):
    @abstractmethod
    def get_by_transformer(self, transformer: Transformer) -> Optional[Any]:
        pass

    @abstractmethod
    def update(self, node_id: str, data: dict) -> None:
        pass


class CommitState(StateLike):
    @abstractmethod
    def commit(self) -> None:
        pass

    @abstractmethod
    def rollback(self, node_id: str) -> None:
        pass

    @abstractmethod
    def get_updates(self, node_id: str) -> list[dict]:
        pass


class State(ABC):
    def __init__(
            self,
            io_state: CommitState,
            global_state: CommitState,
            comp_state: CommitState,
            trace_state: dict = {},
            node_id: str = None
    ):
        self._io_state = io_state
        self._global_state = global_state
        self._trace_state = trace_state
        self._comp_state = comp_state
        self._node_id = node_id

    def get(self, key: Union[str, list, dict]) -> Optional[Any]:
        if self._global_state is None:
            return None
        value = self._global_state.get(key)
        if value is None:
            return self._io_state.get(key)
        return value

    def update(self, data: dict) -> None:
        if self._global_state is None:
            return
        self._global_state.update(self._node_id, data)

    def update_io(self, data: dict) -> None:
        if self._io_state is None:
            return
        self._io_state.update(self._node_id, data)

    def get_io(self, key: Union[str, list, dict]) -> Optional[Any]:
        if self._io_state is None:
            return
        return self._io_state.get(key)

    def update_trace(self, invoke_id: str, span):
        self._trace_state.update({invoke_id: span})

    def update_comp(self, data: dict) -> None:
        if self._comp_state is None:
            return
        self._comp_state.update(self._node_id, data)

    def get_comp(self, key: Union[str, list, dict]) -> Optional[Any]:
        if self._comp_state is None:
            return
        return self._comp_state.get(key)

    def set_user_inputs(self, inputs: Any) -> None:
        if self._io_state is None or inputs is None:
            return
        self._io_state.update("", inputs)
        self._global_state.update("", inputs)
        self.commit()

    def get_inputs_by_transformer(self, transformer: Callable) -> dict:
        if self._io_state is None:
            return {}
        return self._io_state.get_by_transformer(transformer)

    def get_outputs(self, node_id: str) -> Any:
        if self._io_state is None:
            return {}
        return self._io_state.get(node_id)

    def set_outputs(self, node_id: str, outputs: dict) -> None:
        if self._io_state is None or outputs is None:
            return
        return self._io_state.update(node_id, {node_id: outputs})

    def create_executable_state(self, node_id: str) -> Self:
        return State(io_state=self._io_state, global_state=self._global_state, comp_state=self._comp_state,
                     trace_state=self._trace_state, node_id=node_id)

    def commit(self) -> None:
        self._io_state.commit()
        self._comp_state.commit()
        self._global_state.commit()

    def rollback(self) -> None:
        self._comp_state.rollback(self._node_id)
        self._io_state.rollback(self._node_id)
        self._global_state.rollback(self._node_id)

    def get_updates(self) -> dict:
        return {
            "io": self._io_state.get_updates(self._node_id),
            "global": self._global_state.get_updates(self._node_id),
            "comp": self._comp_state.get_updates(self._node_id)
        }
