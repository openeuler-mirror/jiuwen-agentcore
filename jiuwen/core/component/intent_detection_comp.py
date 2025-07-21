#!/usr/bin/env python
# coding=utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import re
import ast
from dataclasses import dataclass, field

from jiuwen.core.common.exception.exception import JiuWenBaseException
from jiuwen.core.common.exception.status_code import StatusCode
from jiuwen.core.common.logging.base import logger
from jiuwen.core.component.base import WorkflowComponent, ComponentConfig
from typing import Optional, AsyncIterator

from jiuwen.core.component.common.configs.model_config import ModelConfig
from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Executable, Output, Input
from jiuwen.core.utils.llm.base import BaseChatModel
from jiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
from jiuwen.core.utils.prompt.template.template import Template

LUI = "llm"
NAME = "name"
MODEL = "model"
CLASS = "class"
REASON = "reason"
INPUT = "input"
USER_PROMPT = "user_prompt"
CATEGORY_INFO = "category_info"
CATEGORY_LIST = "category_list"
CATEGORY_NAME_LIST = "category_name_list"
DEFAULT_CLASS = "default_class"
CHAT_HISTORY = "chat_history"
EXAMPLE_CONTENT = "example_content"
ENABLE_HISTORY = "enable_history"
ENABLE_INPUT = "enable_input"
LLM_INPUTS = "llm_inputs"
LLM_OUTPUTS = "llm_outputs"
MODEL_SOURCE = "modelType"
MODEL_NAME = "modelName"
HYPTER_PARAM = "hyperParameters"
EXTENSION = "extension"
CHAT_HISTORY_MAX_TURN = "chat_history_max_turn"
INTENT_DETECTION_TEMPLATE = "intent_detection_template"
ROLE = "role"
CONTENT = "content"
ROLE_MAP = {"user": '用户', 'assistant': '助手', 'system': '系统'}
JSON_PARSE_FAIL_REASON = "当前意图识别的输出:'{result}'格式不符合有效的JSON规范，导致解析失败，因此返回默认分类。"
CLASS_KEY_MISSING_REASON = "当前意图识别的输出 '{result}' 缺少必要的输出'class'分类信息，因此返回默认分类。"
VALIDATION_FAIL_REASON = "当前意图识别的输出类别 '{intent_class}' 不在预定义的分类列表: '{category_list}'中，因此系统返回默认分类。"
WORKFLOW_CHAT_HISTORY = "workflow_chat_history"

# EI增加
RESULT = "result"
CATEGORY_NAME_ITS1 = "category_name_list"
FEW_SHOT_NUM = 5
ENABLE_Q2L = 'enableKnowledge'
RECALLTHREADSHOLD = "recallThreshold"
DEFAULT_QUERY_CATE = 'title'
DEFAULT_CLASS_CATE = 'content'
DEFAULT_INT = "不确定，其他的意图"
SEARCH_TYPE = "faq"
SEARCH_NUM = 5
CLASSIFICATION_ID = "classificationId"
CLASSIFICATION_DEFAULT_ID = "分类0"
CLASSIFICATION_NAME = "name"
CLASSIFICATION_DEFAULT_NAME = "其他意图"
KG_FILTER_KEY = "filter_string"
KG_FILTER_PREFIX = "category:"
KG_SCOPE = "scope"


@dataclass
class IntentDetectionConfig(ComponentConfig):
    user_prompt: str = ""
    category_info: str = ""
    category_list: list[str] = field(default_factory=list)
    intent_detection_template: Template = None
    category_name_list: list[str] = field(default_factory=list)
    default_class: str = '分类1'
    enable_history: bool = False
    enable_input: bool = True
    chat_history_max_turn: int = 3
    example_content: list[str] = field(default_factory=list)
    overrideable: bool = False
    enableKnowledges: bool = False
    enable_q2fewshot: bool = True
    enable_validation: bool = True
    recallThreshold: float = 0.9
    levenshtein_ration: float = 0.8
    q2label_few_shot_score: float = 0.5
    model: 'ModelConfig' = None


@dataclass()
class IntentDetectionExecutable(Executable):
    def __init__(self, component_config: IntentDetectionConfig):
        super().__init__()
        self._context = None
        self._llm: BaseChatModel = None
        self._initialized: bool = False
        self._config = component_config

    # 获取意图的id和name，用于下一节点调用
    def _get_intent_id_name(self, intent_config, intent_class):
        intent_res = {CLASSIFICATION_ID: CLASSIFICATION_DEFAULT_ID, CLASSIFICATION_NAME: CLASSIFICATION_DEFAULT_NAME}
        idx = next((i for i, category in enumerate(intent_config.category_list) if category == intent_class), -1)
        if idx > -1:
            intent_res = {CLASSIFICATION_ID: idx, CLASSIFICATION_NAME: intent_config.category_name_list[idx]}
        return intent_res

    def _get_chat_history_from_context(self):
        """从上下文中获取对话历史"""
        chat_history = []
        if self._context:
            chat_history: list = self._context.state.get(WORKFLOW_CHAT_HISTORY)
        return chat_history

    def _get_category_info(self):
        if len(self._config.category_list) != len(self._config.category_name_list):
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_INTENT_DETECTION_USER_INPUT_ERROR.code,
                message=f"意图识别分类与描述必须匹配")

        return "\n".join(f"{cid}: {cname}" for cid, cname in
                         zip(self._config.category_list,
                             self._config.category_name_list))

    def _set_context(self, context: Context):
        """设置context属性"""
        self._context = context

    def _create_llm_instance(self):
        return ModelFactory().get_model(self._config.model.model_provider, self._config.model.model_info)

    def _initialize_if_needed(self):
        if not self._initialized:
            try:
                self._llm = self._create_llm_instance()
                self._initialized = True
            except Exception as e:
                raise JiuWenBaseException(
                    error_code=StatusCode.WORKFLOW_LLM_INIT_ERROR.code,
                    message=StatusCode.WORKFLOW_LLM_INIT_ERROR.errmsg.format(msg=str(e))
                ) from e

    def _prepare_detection_inputs(self, inputs, chat_history):
        """准备意图检测所需的输入"""
        current_inputs = {}
        global_intent_map = []

        # 添加基本配置参数
        current_inputs.update({
            USER_PROMPT: self._config.user_prompt,
            CATEGORY_INFO: self._get_category_info(),
            DEFAULT_CLASS: self._config.default_class,
            ENABLE_HISTORY: self._config.enable_history,
            ENABLE_INPUT: self._config.enable_input,
            EXAMPLE_CONTENT: "\n\n".join(self._config.example_content),
            CHAT_HISTORY_MAX_TURN: self._config.chat_history_max_turn
        })

        # 检查输入配置有效性
        if not self._config.enable_history and not self._config.enable_input:
            raise ValueError("AT LEAST ONE OF INTENT_DETECTION'S ENABLE_HISTORY AND ENABLE_INPUT SHOULD ENABLE.")

        # 处理历史记录
        if self._config.enable_history:
            chat_history_str = self._format_chat_history(chat_history)
            current_inputs.update({CHAT_HISTORY: chat_history_str})

        # 处理当前输入
        if self._config.enable_input:
            current_inputs.update({INPUT: inputs.get(INPUT)})

        # 保存全局意图映射用于后续处理
        current_inputs['global_intent_map'] = global_intent_map

        return current_inputs

    def _format_chat_history(self, chat_history):
        """格式化聊天历史记录"""
        chat_history_str = ""
        for history in chat_history[-self._config.chat_history_max_turn:]:
            chat_history_str += "{}: {}\n".format(
                ROLE_MAP.get(history.get(ROLE, CONTENT), "用户"),
                history.get(CONTENT)
            )
        return chat_history_str

    def _pre_process(self, inputs: dict):
        """Pre-process inputs for model"""
        final_prompts = self._config.intent_detection_template.format(inputs).to_messages()
        return final_prompts

    def _handle_detection_result(self, llm_output):
        """处理意图检测结果"""
        intent_class, reason = self.intent_detection_post_process(llm_output)
        # 验证输出有效性
        if not self.output_validation(intent_class):
            return dict(
                result=self._config.default_class,
                reason=VALIDATION_FAIL_REASON.format(
                    intent_class=intent_class,
                    category_list=self._config.category_list
                )
            )
        intent_id_name = self._get_intent_id_name(self._config, intent_class)
        return dict(result=intent_class, reason=reason, classificationId=intent_id_name.get(CLASSIFICATION_ID, ""),
                    name=intent_id_name.get(CLASSIFICATION_NAME, ""))

    def get_llm_result(self, current_inputs):
        """获取llm"""
        llm_inputs = self._pre_process(current_inputs)
        logger.info(f"[%s] intent detection llm_inputs: %s", self._context.executable_id, llm_inputs)
        current_inputs.update({LLM_INPUTS: llm_inputs})
        try:
            llm_output = self._llm.invoke(llm_inputs).content
        except Exception as e:
            raise JiuWenBaseException(
                message=StatusCode.WORKFLOW_INTENT_DETECTION_LLM_INVOKE_ERROR.errmsg.format(
                    error_msg=str(e)
                ),
                error_code=StatusCode.WORKFLOW_INTENT_DETECTION_LLM_INVOKE_ERROR.code
            )
        return llm_output

    async def invoke(self, inputs: Input, context: Context) -> Output:
        """invoke IntentDetection节点"""
        # 提取上下文数据
        self._set_context(context)
        self._initialize_if_needed()
        chat_history = self._get_chat_history_from_context()
        # 处理意图检测输入：
        try:
            current_inputs = self._prepare_detection_inputs(inputs, chat_history)
        except Exception as e:
            raise JiuWenBaseException(
                message=StatusCode.WORKFLOW_INTENT_DETECTION_USER_INPUT_ERROR.errmsg.format(
                    error_mage=f"Search is wrong "
                ),
                error_code=StatusCode.WORKFLOW_INTENT_DETECTION_USER_INPUT_ERROR.code
            ) from e

        # 获取大模型结果
        llm_output = self.get_llm_result(current_inputs)
        logger.info(f"[%s] intent detection output_inputs: %s", self._context.executable_id, llm_output)
        # 后处理意图检测结果
        intent_res = self._handle_detection_result(llm_output)
        return intent_res

    async def stream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        pass

    async def collect(self, inputs: AsyncIterator[Input], contex: Context) -> Output:
        pass

    async def transform(self, inputs: AsyncIterator[Input], context: Context) -> AsyncIterator[Output]:
        pass

    async def interrupt(self, message: dict):
        pass

    def refix_llm_output(self, input_str):
        """大模型输出后处理"""
        res = input_str
        json_path = r'\{.*\}'
        match = re.search(json_path, input_str, re.DOTALL)
        if match:
            res = match.group(0)
            res = res.replace("false", "False").replace("true", "True").replace("null", "None")
        else:
            return input_str
        if "</cot>" in res:
            tmp = res.split("</cot>")
            res = tmp[-1]
        return res

    def intent_detection_post_process(self, result):
        """
        Post-process the result
        Apps:
            result: The result is a dict string.
        Returns:
            The processed results are 'class' and 'reason'
        """
        try:
            # 对推理模型的返回值处理
            result = self.refix_llm_output(result)
            parsed_dict = ast.literal_eval(result)
            if not isinstance(parsed_dict, dict):
                return self._config.default_class, JSON_PARSE_FAIL_REASON.format(result=result)
        except Exception:
            return self._config.default_class, JSON_PARSE_FAIL_REASON.format(result=result)

        # post_process class information
        if not parsed_dict.get(CLASS):
            return self._config.default_class, CLASS_KEY_MISSING_REASON.format(result=parsed_dict)

        intent_class = parsed_dict.get(CLASS).replace('\n', '').replace(' ', '').replace('"', '').replace("'", '')
        match = re.search(r"方案文件", intent_class)
        if match:
            parsed_dict.update({CLASS: match.group(0)})

        return parsed_dict.get(CLASS), parsed_dict.get(REASON, '')

    def output_validation(self, result):
        """
        Validation of LLM output
        Args:
            result: LLM output
        Returns:
            True: Validation passed
            False: Validation failed
        """
        return result in self._config.category_list


class IntentDetectionComponent(WorkflowComponent):
    def __init__(self, component_config: Optional[IntentDetectionConfig] = None):
        super().__init__()
        self._executable = None
        self._config = component_config

    @property
    def executable(self) -> IntentDetectionExecutable:
        """延迟创建executable实例"""
        if self._executable is None:
            self._executable = self.to_executable()
        return self._executable

    def to_executable(self) -> IntentDetectionExecutable:
        """创建可执行实例"""
        return IntentDetectionExecutable(self._config)
