#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
import asyncio
import json
from abc import ABC, abstractmethod
from functools import partial
from typing import TypeVar, Generic, Iterator, AsyncIterator, Any

from jiuwen.core.common.exception.exception import InterruptException
from jiuwen.core.common.exception.status_code import StatusCode
from jiuwen.core.context.context import Context

Input = TypeVar("Input", contravariant=True)
Output = TypeVar("Output", contravariant=True)


class Executable(Generic[Input, Output], ABC):
    memory: "ConversationMemory" = None
    memory_auto_save: bool = True
    local_params: dict = dict()
    global_params: dict = {"memory": None, "input": None}
    is_global: bool = False
    global_var_name: str = ""

    @abstractmethod
    def invoke(self, inputs: Input, context: Context) -> Output:
        pass

    @abstractmethod
    async def ainvoke(self, inputs: Input, context: Context) -> Output:
        return await asyncio.get_running_loop().run_in_executor(
            None, partial(self.invoke, context=context), inputs
        )

    @abstractmethod
    def stream(self, inputs: Input, context: Context) -> Iterator[Output]:
        yield self.invoke(inputs, context)

    @abstractmethod
    async def astream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        yield self.ainvoke(inputs, context)

    @abstractmethod
    def interrupt(self, message: dict):
        raise InterruptException(
            error_code=StatusCode.CONTROLLER_INTERRUPTED_ERROR.code,
            message=json.dumps(message, ensure_ascii=False)
        )

GeneralExecutor = Executable[dict[str, Any], dict[str, Any]]