#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from __future__ import annotations

from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Input

class JiuwenBaseCheckpointSaver(object):

    def __init__(self):
        self.ctx: Context = None
        self.input: Input = None
        self._recovered = False

    def register_context(self, ctx: Context):
        self.ctx = ctx

    def register_input(self, input: Input):
        self.input = input

    def init_recovered(self):
        self._recovered = False

    def recovered(self):
        if not self._recovered:
            self._recovered = True
            return False
        return True
