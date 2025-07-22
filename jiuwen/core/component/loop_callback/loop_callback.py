#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from abc import ABC, abstractmethod

from jiuwen.core.context.context import ContextSetter


class LoopCallback(ContextSetter, ABC):

    @abstractmethod
    def first_in_loop(self):
        raise NotImplementedError

    @abstractmethod
    def out_loop(self):
        raise NotImplementedError

    @abstractmethod
    def start_round(self):
        raise NotImplementedError

    @abstractmethod
    def end_round(self):
        raise NotImplementedError
