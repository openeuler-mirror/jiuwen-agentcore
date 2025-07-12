#!/usr/bin/python3.11
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved

from typing import List, Dict, Any, Iterator, AsyncIterator
from pydantic import Field, BaseModel

from jiuwen.core.utils.llm.base import BaseChatModel, BaseModelInfo
from jiuwen.core.utils.llm.messages import AIMessage
from jiuwen.core.utils.llm.messages_chunk import AIMessageChunk
from jiuwen.core.utils.llm.model_utils.defult_model import RequestChatModel


class Siliconflow(BaseModel, BaseChatModel):
    model_info: BaseModelInfo=Field(default_factory=BaseModelInfo)
    _request_model: RequestChatModel = None

    def __init__(self, model_info: BaseModelInfo):
        super().__init__()
        self.model_info = BaseModelInfo(**model_info.dict())
        self._request_model = RequestChatModel(model_info=self.model_info)
        self._should_close_session = True


    async def close(self):
        if hasattr(self, '_request_model') and self._request_model:
            if hasattr(self._request_model, 'close'):
                await self._request_model.close()
            self._request_model = None


    def model_provider(self)-> str:
        return "siliconflow"

    def _invoke(self, messages: List[Dict], tools: List[Dict] = None, **kwargs: Any) -> AIMessage:
        return self._request_model._invoke(messages, tools, **kwargs)

    async def _ainvoke(self, messages: List[Dict], tools: List[Dict] = None, **kwargs: Any) -> AIMessage:
        return await self._request_model._ainvoke(messages, tools, **kwargs)  # Added await here

    def _stream(self, messages: List[Dict], tools: List[Dict] = None, **kwargs: Any) -> Iterator[AIMessageChunk]:
        return self._request_model._stream(messages, tools, **kwargs)

    async def _astream(self, messages: List[Dict], tools: List[Dict] = None, **kwargs: Any) -> AsyncIterator[
        AIMessageChunk]:
        async for chunk in self._request_model._astream(messages, tools, **kwargs):
            yield chunk