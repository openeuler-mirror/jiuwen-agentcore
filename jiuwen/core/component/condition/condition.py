#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from abc import ABC, abstractmethod
from typing import Callable

from jiuwen.core.context.context import ContextSetter

INDEX = "index"


class Condition(ContextSetter, ABC):

    @abstractmethod
    def init(self):
        raise NotImplementedError

    @abstractmethod
    def __call__(self) -> bool:
        raise NotImplementedError


class FuncCondition(Condition):
    def __init__(self, func: Callable[[], bool]):
        super().__init__()
        self._func = func

    def init(self):
        pass

    def __call__(self) -> bool:
        return self._func()


class AlwaysTrue(Condition):

    def init(self):
        pass

    def __call__(self) -> bool:
        return True
