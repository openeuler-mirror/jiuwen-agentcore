#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from enum import Enum


class StatusCode(Enum):
    CONTROLLER_INTERRUPTED_ERROR = (10312, "controller interrupted error")

    # Prompt 模板管理 102050 - 102099
    PROMPT_ASSEMBLER_VARIABLE_INIT_ERROR = (102050, "Wrong arguments for initializing the variable")
    PROMPT_ASSEMBLER_INIT_ERROR = (102051, "Wrong arguments for initializing the assembler")
    PROMPT_ASSEMBLER_INPUT_KEY_ERROR = (
        102052,
        "Missing or unexpected key-value pairs passed in as arguments for the assembler or variable when updating"
    )
    PROMPT_ASSEMBLER_TEMPLATE_FORMAT_ERROR = (
        102053,
        "Errors occur when formatting the template content due to wrong format")

    # Prompt 模板管理 102100 - 102149
    PROMPT_TEMPLATE_DUPLICATED_ERROR = (102101, "Template duplicated")
    PROMPT_TEMPLATE_NOT_FOUND_ERROR = (102102, "Template not found")

    @property
    def code(self):
        return self.value[0]

    @property
    def errmsg(self):
        return self.value[1]
