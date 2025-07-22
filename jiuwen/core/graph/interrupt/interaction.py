#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from __future__ import annotations

import asyncio
from typing import Any

from langgraph.errors import GraphInterrupt
from langgraph.types import Interrupt

from jiuwen.core.common.constants.constant import INTERACTION
from jiuwen.core.common.constants.constant import INTERACTIVE_INPUT
from jiuwen.core.context.context import Context
from jiuwen.core.context.utils import NESTED_PATH_SPLIT
from jiuwen.core.stream.writer import OutputSchema


class Interaction(object):
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.idx = 0
        self.node_id = self.ctx.state._node_id
        self.interactive_inputs = None
        interactive_inputs = self.ctx.state.get_comp(INTERACTIVE_INPUT + NESTED_PATH_SPLIT + self.node_id)
        if isinstance(interactive_inputs, list):
            self.interactive_inputs = interactive_inputs
        self.latest_interactive_inputs = None
        if self.interactive_inputs:
            self.latest_interactive_inputs = self.interactive_inputs[-1]

    def get_next_interactive_input(self) -> Any | None:
        if self.interactive_inputs and self.idx < len(self.interactive_inputs):
            res = self.interactive_inputs[self.idx]
            self.idx += 1
            return res

    def user_input(self, value: Any) -> Any:
        if res := self.get_next_interactive_input():
            return res
        if self.ctx.stream_writer_manager:
            output_writer = self.ctx.stream_writer_manager.get_output_writer()
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(
                    output_writer.write(OutputSchema(type=INTERACTION, index=self.idx, payload=(self.node_id, value))))
            else:
                loop.run_until_complete(
                    output_writer.write(OutputSchema(type=INTERACTION, index=self.idx, payload=(self.node_id, value))))

        raise GraphInterrupt((Interrupt(
            value=OutputSchema(type=INTERACTION, index=self.idx, payload=(self.node_id, value)), resumable=True,
            ns=self.node_id)))

    def user_latest_input(self, value: Any) -> Any:
        if res := self.latest_interactive_inputs:
            self.latest_interactive_inputs = None
            return res
        if self.ctx.stream_writer_manager:
            output_writer = self.ctx.stream_writer_manager.get_output_writer()
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(
                    output_writer.write(OutputSchema(type=INTERACTION, index=self.idx, payload=(self.node_id, value))))
            else:
                loop.run_until_complete(
                    output_writer.write(OutputSchema(type=INTERACTION, index=self.idx, payload=(self.node_id, value))))

        raise GraphInterrupt((Interrupt(
            value=OutputSchema(type=INTERACTION, index=self.idx, payload=(self.node_id, value)), resumable=True,
            ns=self.node_id)))
