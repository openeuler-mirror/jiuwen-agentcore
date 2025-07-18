#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from abc import ABC
from typing import Any, Self

from jiuwen.core.context.config import Config
from jiuwen.core.context.state import State
from jiuwen.core.context.store import Store
from jiuwen.core.runtime.callback_manager import CallbackManager
from jiuwen.core.stream.manager import StreamWriterManager
from jiuwen.core.tracer.tracer import Tracer


class Context(ABC):
    def __init__(self, config: Config, state: State, store: Store = None):
        self._config = config
        self._state = state
        self._store = store
        self._tracer = None
        self._callback_manager = CallbackManager()
        self._stream_writer_manager: StreamWriterManager = None
        self._controller_context_manager = None

    def set_stream_writer_manager(self, stream_writer_manager: StreamWriterManager):
        if self._stream_writer_manager is not None:
            return
        self._stream_writer_manager = stream_writer_manager

    def set_tracer(self, tracer: Tracer):
        self._tracer = tracer

    def set_controller_context_manager(self, controller_context_manager):
        self._controller_context_manager = controller_context_manager

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

    @property
    def callback_manager(self) -> CallbackManager:
        return self._callback_manager

    def create_executable_context(self, node_id: str) -> Self:
        context = ExecutableContext(self, node_id)
        context.set_stream_writer_manager(self._stream_writer_manager)
        context.set_tracer(self.tracer)
        return context


class ExecutableContext(Context):
    def __init__(self, context: Context, node_id: str):
        self._node_id = node_id
        self._parent_id = context.executable_id if isinstance(context, ExecutableContext) else None
        self._executable_id = self._parent_id + "." + node_id if self._parent_id is not None else node_id
        super().__init__(context.config, context.state.create_executable_state(self._executable_id), context.store)

    @property
    def node_id(self):
        return self._node_id

    @property
    def executable_id(self):
        return self._executable_id

    @property
    def parent_id(self):
        return self._parent_id
