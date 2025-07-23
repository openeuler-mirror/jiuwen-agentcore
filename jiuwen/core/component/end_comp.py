#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
import uuid
from abc import ABC
from copy import deepcopy
from dataclasses import dataclass, field
from typing import AsyncIterator
from jiuwen.core.common.logging.base import logger


from jiuwen.core.common.constants.constant import USER_FIELDS
from jiuwen.core.common.utils.utils import TemplateUtils
from jiuwen.core.component.base import WorkflowComponent
from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Executable, Input, Output
from jiuwen.core.stream.base import StreamCode
import time

async def get_stream_data(stream_code: str,  data: dict, index: int, context: Context,):


    stream_final_data = dict(type=stream_code, index = index, payload=data)

    await context.stream_writer_manager.get_output_writer().write(stream_final_data)


class End(Executable,WorkflowComponent):
    def __init__(self, node_id: str, node_name: str, conf: dict):
        super().__init__()
        self.node_id = node_id
        self.node_name = node_name
        self.conf = conf
        self.template = conf["responseTemplate"]

    async def invoke(self, inputs: Input, context: Context) -> Output:
        answer = TemplateUtils.render_template(self.template, inputs.get(USER_FIELDS))

        final_output = dict(responseContent=answer)
        try:
          response_mode = inputs.get("response_mode")
          if response_mode is not None and response_mode == "streaming":
            response_list = TemplateUtils.render_template_to_list(self.template)
            index = 0
            for res in response_list:
                if res.startswith("{{") and res.endswith("}}"):
                    param_name = res[2:-2]
                    param_value = inputs.get(USER_FIELDS).get(param_name)
                    if param_value is None:
                        continue
                    await get_stream_data(StreamCode.PARTIAL_CONTENT.name,dict(answer=param_value), index, context)


                else:
                    await get_stream_data(StreamCode.PARTIAL_CONTENT.name,
                                          dict(answer=res), index, context)

                index += 1

            final_index = 0
            await get_stream_data(StreamCode.MESSAGE_END.name, dict(answer=final_output), final_index, context)
            await get_stream_data(StreamCode.WORKFLOW_END.name, dict(answer=final_output),  final_index, context)
            await get_stream_data(StreamCode.FINISH.name, dict(answer=final_output), final_index, context)
        except Exception as e:
            logger.info("stream output error: {}".format(e))


        return final_output

    async def stream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        pass

    async def collect(self, inputs: AsyncIterator[Input], contex: Context) -> Output:
        pass

    async def transform(self, inputs: AsyncIterator[Input], context: Context) -> AsyncIterator[Output]:
        pass

    async def interrupt(self, message: dict):
        pass

    def to_executable(self) -> Executable:
        return self

