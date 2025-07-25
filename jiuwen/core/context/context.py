#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
import uuid
from abc import ABC, abstractmethod
from typing import Any, Self

from jiuwen.core.context.config import Config
from jiuwen.core.context.mq_manager import MessageQueueManager
from jiuwen.core.context.state import State
from jiuwen.core.context.store import Store
from jiuwen.core.runtime.callback_manager import CallbackManager
from jiuwen.core.stream.manager import StreamWriterManager
from jiuwen.core.tracer.tracer import Tracer


class Context(ABC):
    @abstractmethod
    def config(self) -> Config:
        pass

    @abstractmethod
    def state(self) -> State:
        pass

    @abstractmethod
    def store(self) -> Store:
        pass

    @abstractmethod
    def tracer(self) -> Any:
        pass

    @abstractmethod
    def stream_writer_manager(self) -> StreamWriterManager:
        pass

    @abstractmethod
    def callback_manager(self) -> CallbackManager:
        pass

    @abstractmethod
    def controller_context_manager(self):
        pass

    @abstractmethod
    def session_id(self) -> str:
        pass

    def set_controller_context_manager(self, controller_context_manager) -> None:
        return

    def set_tracer(self, tracer: Tracer) -> None:
        return

    def set_stream_writer_manager(self, stream_writer_manager: StreamWriterManager) -> None:
        return

    def set_queue_manager(self, queue_manager: MessageQueueManager):
        return

    def clone(self) -> Self:
        return None


class WorkflowContext(Context):
    def __init__(self, state: State, config: Config = Config(), store: Store = None, tracer: Tracer = None,
                 session_id: str = None):
        self.__config = config
        self.__state = state
        self.__store = store
        self.__tracer = tracer
        self.__callback_manager = CallbackManager()
        self.__stream_writer_manager: StreamWriterManager = None
        self.__controller_context_manager = None
        self.__session_id = session_id if session_id else uuid.uuid4().hex
        self.queue_manager: MessageQueueManager = None

    def set_stream_writer_manager(self, stream_writer_manager: StreamWriterManager) -> None:
        if self.__stream_writer_manager is not None:
            return
        self.__stream_writer_manager = stream_writer_manager

    def set_tracer(self, tracer: Tracer) -> None:
        self.__tracer = tracer

    def set_controller_context_manager(self, controller_context_manager) -> None:
        self.__controller_context_manager = controller_context_manager

    def config(self) -> Config:
        return self.__config

    def state(self) -> State:
        return self.__state

    def store(self) -> Store:
        return self.__store

    def tracer(self) -> Any:
        return self.__tracer

    def stream_writer_manager(self) -> StreamWriterManager:
        return self.__stream_writer_manager

    def callback_manager(self) -> CallbackManager:
        return self.__callback_manager

    def controller_context_manager(self):
        return self.__controller_context_manager

    def set_queue_manager(self, queue_manager: MessageQueueManager):
        if self.queue_manager is not None:
            return
        self.queue_manager = queue_manager

    def session_id(self) -> str:
        return self.__session_id

    def clone(self) -> Self:
        return WorkflowContext(state=self.state().clone(), session_id=self.session_id())


class NodeContext(Context):
    def __init__(self, context: Context, node_id: str):
        self.__node_id = node_id
        self.__parent_id = context.executable_id() if isinstance(context, NodeContext) else ''
        self.__executable_id = self.__parent_id + "." + node_id if len(self.__parent_id) != 0 else node_id
        self.__state = context.state().create_node_state(self.__executable_id)
        self.__context = context

    def node_id(self):
        return self.__node_id

    def executable_id(self):
        return self.__executable_id

    def parent_id(self):
        return self.__parent_id

    def tracer(self) -> Any:
        return self.__context.tracer()

    def state(self) -> State:
        return self.__state

    def config(self) -> Config:
        return self.__context.config()

    def store(self) -> Store:
        return self.__context.store()

    def stream_writer_manager(self) -> StreamWriterManager:
        return self.__context.stream_writer_manager()

    def callback_manager(self) -> CallbackManager:
        return self.__context.callback_manager()

    def controller_context_manager(self):
        return self.__context.controller_context_manager()

    def session_id(self) -> str:
        return self.__context.session_id()

    def parent_context(self):
        return self.__context

class ContextSetter(ABC):
    def __init__(self, context: Context = None):
        self._context = context

    def set_context(self, context: Context):
        self._context = context
