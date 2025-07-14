# -*- coding: utf-8 -*-

"""
prompt optimization utils
"""

import os
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timezone, timedelta

from pydantic import BaseModel, field_validator, Field, FieldValidationInfo
import yaml

from jiuwen.agent_builder.prompt_builder.tune.base.exception import OnStopException
from jiuwen.agent_builder.prompt_builder.tune.common.exception import JiuWenBaseException, StatusCode
from jiuwen.agent_builder.prompt_builder.tune.base.case import Case
from jiuwen.agent_builder.prompt_builder.tune.base.constant import TuneConstant, TaskStatus


class TaskInfo(BaseModel):
    """prompt optimization input task info"""
    task_id: str = Field(...)
    task_name: str = Field(...)
    task_description: str = Field(default="")
    create_time: str = Field(...)


class OptimizeInfo(BaseModel):
    """definition of prompt optimization info"""
    cases: List[Case] = Field(default=[])
    num_iterations: int = Field(default=TuneConstant.DEFAULT_ITERATION_NUM)
    num_parallel: int = Field(default=TuneConstant.DEFAULT_LLM_PARALLEL_DEGREE,
                              ge=TuneConstant.MIN_LLM_PARALLEL_DEGREE, le=TuneConstant.MAX_LLM_PARALLEL_DEGREE)
    num_examples: int = Field(default=TuneConstant.DEFAULT_EXAMPLE_NUM,
                              ge=TuneConstant.MIN_EXAMPLE_NUM, le=TuneConstant.MAX_EXAMPLE_NUM)
    num_cot_examples: int = Field(default=TuneConstant.DEFAULT_COT_EXAMPLE_NUM,
                                  ge=TuneConstant.MIN_COT_EXAMPLE_NUM, le=TuneConstant.MAX_COT_EXAMPLE_NUM)
    num_retires: int = Field(default=TuneConstant.DEFAULT_LLM_CALL_RETRY_NUM,
                             ge=TuneConstant.MIN_LLM_CALL_RETRY_NUM, le=TuneConstant.MAX_LLM_CALL_RETRY_NUM)
    optimize_method: str = Field(default=TuneConstant.OPTIMIZATION_METHOD_JOINT)
    placeholder: Optional[List] = Field(default=[])
    evaluation_method: str = Field(default=TuneConstant.DEFAULT_EVALUATION_METHOD)
    tools: Union[List[Dict[str, Any]], Any] = Field(default=[])
    user_compare_rules: str = Field(default="None")


class JointParameters(BaseModel):
    """Joint optimization parameters"""
    num_examples: int = Field(default=TuneConstant.DEFAULT_EXAMPLE_NUM)
    num_cot_examples: int = Field(default=TuneConstant.DEFAULT_COT_EXAMPLE_NUM)
    base_instructions: str = Field(default="")
    filled_instructions: str = Field(default="")
    full_prompt: str = Field(default="")
    answer_format: str = Field(default="")
    task_description: str = Field(default="")
    num_iterations: int = Field(default=TuneConstant.DEFAULT_ITERATION_NUM)
    opt_placeholder_names: List[str] = Field(default=[])
    placeholders: List = Field(default=[])
    original_placeholders: List = Field(default=[])
    examples: List = Field(default=[])
    cot_examples: List = Field(default=[])


class History(BaseModel):
    """optimization history for every round"""
    optimized_prompt: str = Field(default="")
    original_placeholder: Dict[str, str] = Field(default={})
    optimized_placeholder: Dict[str, str] = Field(default={})
    examples: List[str] = Field(default=[])
    filled_prompt: str = Field(default="")
    success_rate: float = Field(default=0.0)
    iteration_round: int = Field(default=0)


class LLMModelInfo(BaseModel):
    """LLM model config info"""
    url: str = Field(default="", min_length=0, max_length=256)
    model: str = Field(default="", min_length=0, max_length=256)
    type: str = Field(default="", min_length=0, max_length=256)
    headers: Optional[Dict] = Field(default={})
    model_source: str = Field(default="", min_length=0, max_length=256)
    api_key: str = Field(default="", min_length=0, max_length=256)


class QwenLLM:
    def __init__(self, model_info: LLMModelInfo):
        self.url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        self.api_key = "sk-f9410e0700c94022a16b78341e860c45"
        self.model_name = model_info.model

    def chat(self, messages):
        import requests
        body = {
            "messages": messages,
            "model": self.model_name,
            "stream": False
        }
        headers = {
            "Authorization": f"{self.api_key}",
        }
        response = requests.post(self.url, json=body, headers=headers)
        if response.status_code != 200:
            print(response.text)
            raise Exception(response.text)
        content = response.json().get("choices")[0].get("message").get("content")
        return dict(content=content)

class LLMModelProcess:
    """LLM invoke process"""
    def __init__(self, llm_model_info: LLMModelInfo):
        if llm_model_info.headers is None:
            raise JiuWenBaseException(
                error_code=StatusCode.LLM_CONFIG_MISS_ERROR.code,
                message=StatusCode.LLM_CONFIG_MISS_ERROR.errmsg.format(
                    error_msg="prompt optimization llm config is missing"
                )
            )
        self.chat_llm = None
        self.model_info = llm_model_info

    def chat(self, messages: List[Any]) -> Dict:
        """chat"""
        return QwenLLM(self.model_info).chat(messages)


def load_yaml_to_dict(file_path: str) -> Dict:
    """load yaml file"""
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            yaml_content = f.read()
            parsed_dict = yaml.safe_load(yaml_content)
        except Exception as e:
            raise JiuWenBaseException(
                error_code=StatusCode.LLM_CONFIG_MISS_ERROR.code,
                message=StatusCode.LLM_CONFIG_MISS_ERROR.errmsg
            )
    return parsed_dict

def calculate_runtime(start_time: str) -> int:
    """calculate task runtime"""
    if not start_time:
        raise JiuWenBaseException(
            error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
            message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                error_msg="invalid start time"
            )
        )
    try:
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        cur_time = datetime.now(tz=timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
        cur_time = datetime.strptime(cur_time, "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        raise JiuWenBaseException(
            error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
            message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                error_msg="invalid time format"
            )
        ) from e
    return int((cur_time - start_time).total_seconds())


def placeholder_to_dict(placeholder_list: List, select_all: bool = False) -> Dict:
    """convert placeholder list to dict"""
    if not placeholder_list:
        return {}

    placeholder_dict = {}
    for placeholder in placeholder_list:
        if select_all or placeholder.get("need_optimize"):
            placeholder_dict[placeholder["name"]] = placeholder["content"]
    return placeholder_dict


def examples_to_string_list(example_list: List) -> List[str]:
    """convert example list to string list"""
    if not example_list:
        return []
    example_string_format = (f"[query]: {TuneConstant.QUESTION_KEY}\n"
                             f"[assistant answer]: {TuneConstant.LABEL_KEY}")
    example_string_list = []
    for example in example_list:
        example_string_list.append(example_string_format.format(
            question=example.get(TuneConstant.QUESTION_KEY, ""),
            label=example.get(TuneConstant.LABEL_KEY, "")
        ))
    return example_string_list

def get_example_question(example):
    """get example question"""
    content = example.get(TuneConstant.QUESTION_KEY, "")
    if TuneConstant.RAW_PROMPT_TAG in content:
        return str(example.get(TuneConstant.VARIABLE_KEY, ""))
    return content