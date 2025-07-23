#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from jiuwen.core.component.loop_callback.loop_callback import LoopCallback

LOOP_ID = "__sys_loop_id"


class LoopIdCallback(LoopCallback):
    def __init__(self, node_id: str):
        super().__init__()
        self._node_id = node_id

    def first_in_loop(self):
        self._context.state().update({LOOP_ID: self._node_id})

    def out_loop(self):
        self._context.state().update({LOOP_ID: None})

    def start_round(self):
        pass

    def end_round(self):
        pass
