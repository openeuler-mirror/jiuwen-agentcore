#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_id
)
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from jiuwen.core.common.constants.constant import INTERACTIVE_INPUT
from jiuwen.core.graph.interrupt.interactive_input import InteractiveInput
from jiuwen.graph.checkpoint.base import JiuwenBaseCheckpointSaver

STATE_KEY = "state"
STATE_UPDATES_KEY = "state_updates"


class JiuwenInMemoryCheckpointSaver(InMemorySaver, JiuwenBaseCheckpointSaver):
    # (thread ID, checkpoint ns, checkpoint ID, io_state KEY) -> (value type, value dumped bytes)
    state_blobs: dict[
        tuple[
            str, str, str, str
        ],
        tuple[str, bytes],
    ] = {}

    # (thread ID, checkpoint ns, checkpoint ID, io_state_updates KEY) -> (value type, value dumped bytes)
    state_updates_blobs: dict[
        tuple[
            str, str, str, str
        ],
        tuple[str, bytes]
    ] = {}

    def __init__(self, *, serde=None):
        if serde is None:
            serde = JsonPlusSerializer(pickle_fallback=True)
        InMemorySaver.__init__(self, serde=serde)
        JiuwenBaseCheckpointSaver.__init__(self)
        self.io_state_blobs = {}
        self.global_state_blobs = {}
        self.io_state_updates_blobs = {}
        self.global_state_updates_blobs = {}

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)
        if checkpoint_id is None and (checkpoints := self.storage[thread_id][checkpoint_ns]):
            checkpoint_id = max(checkpoints.keys())
        if checkpoint_id:
            if (state_blob := self.state_blobs.get((thread_id, checkpoint_ns, checkpoint_id, STATE_KEY))) and \
                    state_blob[0] != "empty":
                state = self.serde.loads_typed(state_blob)
                self.ctx.state.set_state(state)

            if isinstance(self.input, InteractiveInput):
                interactive_inputs = self.ctx.state.get_comp(INTERACTIVE_INPUT)
                for node_id, input in self.input.user_input.items():
                    exe_ctx = self.ctx.create_executable_context(node_id)
                    if (
                        isinstance(interactive_inputs, dict) and
                        (interactive_input := interactive_inputs.get(node_id)) and
                        isinstance(interactive_input, list)
                    ):
                        interactive_input.append(input)
                        exe_ctx.state.update_comp({INTERACTIVE_INPUT: {node_id: interactive_input}})
                        continue
                    exe_ctx.state.update_comp({INTERACTIVE_INPUT: {node_id: [input]}})
                self.ctx.state.commit()

            if state_updates_blob := self.state_updates_blobs.get(
                    (thread_id, checkpoint_ns, checkpoint_id, STATE_UPDATES_KEY)):
                state_updates = self.serde.loads_typed(state_updates_blob)
                self.ctx.state.set_updates(state_updates)
                
        return super().get_tuple(config)

    def put(
            self,
            config: RunnableConfig,
            checkpoint: Checkpoint,
            metadata: CheckpointMetadata,
            new_versions: ChannelVersions,
    ) -> RunnableConfig:
        if self.ctx:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"]["checkpoint_ns"]
            checkpoint_id = checkpoint["id"]

            state = self.ctx.state.get_state()
            if state_blob := self.serde.dumps_typed(state):
                self.state_blobs[(thread_id, checkpoint_ns, checkpoint_id, STATE_KEY)] = state_blob

            updates = self.ctx.state.get_updates()
            if updates_blob := self.serde.dumps_typed(updates):
                self.state_updates_blobs[
                    (thread_id, checkpoint_ns, checkpoint_id, STATE_UPDATES_KEY)] = updates_blob

        return super().put(config, checkpoint, metadata, new_versions)

    def delete_thread(self, thread_id: str) -> None:
        super().delete_thread(thread_id)
        for key in list(self.state_blobs.keys()):
            if key[0] == thread_id:
                del self.state_blobs[key]

        for key in list(self.state_updates_blobs.keys()):
            if key[0] == thread_id:
                del self.state_updates_blobs[key]
