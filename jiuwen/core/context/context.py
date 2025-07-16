#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from abc import ABC
from typing import Any, Self

from pydantic import BaseModel

from jiuwen.core.context.config import Config, CompIOConfig
from jiuwen.core.context.state import State
from jiuwen.core.context.store import Store
from jiuwen.core.runtime.callback_manager import CallbackManager
from jiuwen.core.stream.base import StreamMode
from jiuwen.core.stream.emitter import StreamEmitter
from jiuwen.core.stream.manager import StreamWriterManager
from jiuwen.core.tracer.tracer import Tracer


class Context(ABC):
    def __init__(self, config: Config, state: State, store: Store = None, tracer: Any = None,
                 stream_emitter: StreamEmitter = None, stream_writer_manager: StreamWriterManager = None,
                 workflow_config: BaseModel = None, queue_manager: Any = None,
                 callback_manager: CallbackManager = None):
        self._config = config
        self._state = state
        self._store = store
        self._tracer = tracer
        self._callback_manager = callback_manager
        self._stream_emitter = stream_emitter
        self._stream_writer_manager = stream_writer_manager
        self._workflow_config: BaseModel = workflow_config
        self._queue_manager = queue_manager

    def init(self, comp_configs: dict[str, CompIOConfig], stream_edges: dict[str, list[str]] = None,
             workflow_config: BaseModel = None, stream_modes: list[StreamMode] = None) -> bool:
        if self.config is not None and not self.config.init(comp_configs, stream_edges):
            return False
        self._callback_manager = CallbackManager()
        self._stream_emitter = StreamEmitter()
        self._stream_writer_manager = StreamWriterManager(stream_emitter=self._stream_emitter, modes=stream_modes)
        self._workflow_config = workflow_config
        if isinstance(self._tracer, Tracer):
            self._tracer.init(self._stream_writer_manager, self._callback_manager)
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

    def create_executable_context(self, node_id: str) -> Self:
        return Context(config=self.config, state=self.state.create_executable_state(node_id), store=self._store,
                       tracer=self._tracer, stream_emitter=self._stream_emitter,
                       stream_writer_manager=self._stream_writer_manager,
                       workflow_config=self._workflow_config, queue_manager=self._queue_manager,
                       callback_manager=self._callback_manager)
