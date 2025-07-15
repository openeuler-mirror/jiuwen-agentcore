#!/usr/bin/python3.11
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved

from jiuwen.core.utils.llm.messages import ToolInfo
from jiuwen.core.utils.tool.base import Tool
from jiuwen.core.utils.tool.constant import Input, Output


class LocalFunction(Tool):
    def __init__(self):
        super().__init__()

    def invoke(self, inputs: Input, **kwargs) -> Output:
        """invoke the tool"""
        pass

    async def ainvoke(self, inputs: Input, **kwargs) -> Output:
        """async invoke the tool"""
        pass

    def get_tool_info(self) -> ToolInfo:
        """get tool info"""
        pass