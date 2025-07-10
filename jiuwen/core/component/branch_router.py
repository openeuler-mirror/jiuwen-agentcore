#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Callable, Union

from jiuwen.core.component.condition.condition import Condition, FuncCondition
from jiuwen.core.component.condition.expression import ExpressionCondition


class Branch:
    def __init__(self, context: Context, condition: Union[str, Callable[[], bool], Condition],
                 target: list[str], branch_id: str = None):
        self._context = context
        self.branch_id = branch_id
        if isinstance(condition, str):
            self._condition = ExpressionCondition(context, condition)
        elif isinstance(condition, Callable):
            self._condition = FuncCondition(condition)
        else:
            self._condition = condition
        self.target = target

    def init(self):
        self._condition.init()

    def evaluate(self) -> bool:
        return self._condition()


class BranchRouter:
    def __init__(self, context: Context):
        self._context = context
        self._branches: list[Branch] = []

    def add_branch(self, condition: Union[str, Callable[[], bool], Condition], target: list[str],
                   branch_id: str = None):
        self._branches.append(Branch(self._context, condition, target, branch_id))

    def __call__(self, *args, **kwargs) -> list[str]:
        for branch in self._branches:
            branch.init()
            if branch.evaluate():
                return branch.target
        return []
