#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from abc import ABC
from typing import Any, Optional

from pydantic import BaseModel

from jiuwen.core.context.config import Config
from jiuwen.core.context.state import State
from jiuwen.core.context.store import Store


class Context(ABC):
    def __init__(self, config: Config, state: State, store: Store = None, tracer: Any = None):
        self._config = config
        self._state = state
        self._store = store
        self._tracer = tracer
        self._stream_writer_manager = None
        self._workflow_config: BaseModel = None
        self._queue_manager = None
        self._stream_modes: list[str] = None

    def init(self, io_schemas: dict[str, tuple[dict, dict]], stream_edges: dict[str, list[str]] = None,
             workflow_config: BaseModel = None, stream_modes: list[str] = None) -> bool:
        if self.config is not None and not self.config.init(io_schemas, stream_edges):
            return False
        self._workflow_config = workflow_config
        self._stream_modes = stream_modes

    @property
    def config(self) -> Config:
        return self._config

    @property
    def state(self) -> State:
        return self._state

    @property
    def store(self) -> Store:
        return self._store

    @property
    def tracer(self) -> Any:
        return self._tracer

    def get_stream_writer(self, mode: str) -> Optional[Any]:
        if mode not in self._stream_modes:
            return None
        return self._stream_writer_manager.get_writer(key=mode)
