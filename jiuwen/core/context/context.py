#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from abc import ABC
from typing import Any, Optional

from pydantic import BaseModel

from jiuwen.core.context.config import Config
from jiuwen.core.context.state import State
from jiuwen.core.context.store import Store
from jiuwen.core.stream.base import StreamMode
from jiuwen.core.stream.emitter import StreamEmitter
from jiuwen.core.stream.manager import StreamWriterManager


class Context(ABC):
    def __init__(self, config: Config, state: State, store: Store = None, tracer: Any = None):
        self._config = config
        self._state = state
        self._store = store
        self._tracer = tracer
        self._stream_emitter = None
        self._stream_writer_manager = None
        self._workflow_config: BaseModel = None
        self._queue_manager = None

    def init(self, io_schemas: dict[str, tuple[dict, dict]], stream_edges: dict[str, list[str]] = None,
             workflow_config: BaseModel = None, stream_modes: list[StreamMode] = None) -> bool:
        if self.config is not None and not self.config.init(io_schemas, stream_edges):
            return False
        self._stream_emitter = StreamEmitter()
        self._stream_writer_manager = StreamWriterManager(stream_emitter=self._stream_emitter, modes=stream_modes)
        self._workflow_config = workflow_config
        return True

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

    @property
    def stream_writer_manager(self) -> StreamWriterManager:
        return self._stream_writer_manager