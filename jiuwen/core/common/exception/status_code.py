#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from enum import Enum


class StatusCode(Enum):
    CONTROLLER_INTERRUPTED_ERROR = (10312, "controller interrupted error")
    PROMPT_JSON_SCHEMA_ERROR = (102056, "Invalid json schema, root cause = {error_msg}.")

    @property
    def code(self):
        return self.value[0]

    @property
    def errmsg(self):
        return self.value[1]
