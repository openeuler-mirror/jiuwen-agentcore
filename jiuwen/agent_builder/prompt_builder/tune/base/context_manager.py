#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved

import copy
import threading
import hashlib
import time
from typing import Dict, Optional, Any

from cacheout import Cache

from jiuwen.agent_builder.prompt_builder.tune.common.singleton import Singleton

from logging import getLogger
logger = getLogger(__name__)

from jiuwen.agent_builder.prompt_builder.tune.base.constant import TuneConstant, TaskStatus

Context = Dict[str, Any]
STOP_EVENT = "stop_event"

class ContextManager(metaclass=Singleton):
    """manage optimizer train context"""
    def __init__(self):
        self._cache: Cache = Cache(maxsize=65536)            # context memory cache
        self._check_points: Cache = Cache(maxsize=65536)     # context checkpoint
        self._lock: threading.Lock = threading.Lock()

        self._n_max_running_task: int = TuneConstant.DEFAULT_MAX_RUNNING_TASK_NUM

    def __len__(self):
        """get length of current contexts"""
        with self._lock:
            return self._cache.size()

    @staticmethod
    def _generate_context_id():
        """generate unique context id"""
        timestamp = str(int(time.time() * 1000))
        return f"JNT_{hashlib.sha256(timestamp.encode()).hexdigest()}"

    def get_context_attr(self, ctx_id: str, attr_name: str):
        context = self._cache.get(ctx_id)
        if context:
            return context.get(attr_name, None)

    def set_context_attr(self, ctx_id: str, attr_name: str, value: Any):
        context = self._cache.get(ctx_id)
        if context:
            context[attr_name] = value
        checkpoint = self._check_points.get(ctx_id)
        if checkpoint:
            checkpoint[attr_name] = value

    def set(self, ctx_id: str, context: Context):
        """set context to cache"""
        with self._lock:
            self._cache.set(ctx_id, context)

    def get(self, ctx_id: str) -> Optional[Context]:
        """get context from cache"""
        with self._lock:
            return self._cache.get(ctx_id, None)

    def is_executable(self):
        n_running_task = 0
        for task in self._cache.values():
            status = task.status
            if status in (TaskStatus.TASK_STOPPING, TaskStatus.TASK_RUNNING):
                n_running_task += 1
        return n_running_task <= self._n_max_running_task

    def set_checkpoint(self, ctx_id: str, context: Context):
        """set checkpoint to cache"""
        with self._lock:
            stop_event = context.get(STOP_EVENT)
            context[STOP_EVENT] = None
            copy_context = copy.deepcopy(context)
            context[STOP_EVENT] = stop_event
            self._check_points.set(ctx_id, copy_context)

    def get_checkpoint(self, ctx_id: str) -> Optional[Context]:
        """get checkpoint from cache"""
        with self._lock:
            context = copy.deepcopy(self._check_points.get(ctx_id), None)
            if context:
                context[STOP_EVENT] = threading.Event()
            return context

    def delete(self, ctx_id: str):
        """delete checkpoint from cache"""
        with self._lock:
            self._cache.delete(ctx_id)
            self._check_points.delete(ctx_id)

    def clear(self):
        """clear checkpoint from cache"""
        with self._lock:
            self._cache.clear()
            self._check_points.clear()

    def items(self):
        with self._lock:
            return self._cache.items()