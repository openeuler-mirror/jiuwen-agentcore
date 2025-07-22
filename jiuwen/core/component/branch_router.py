#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Callable, Union

from jiuwen.core.component.condition.condition import Condition, FuncCondition
from jiuwen.core.component.condition.expression import ExpressionCondition
from jiuwen.core.context.context import Context, ContextSetter


class Branch(ContextSetter):
    def __init__(self, condition: Union[str, Callable[[], bool], Condition], target: list[str],
                 branch_id: str = None):
        super().__init__()
        self.branch_id = branch_id
        if isinstance(condition, str):
            self._condition = ExpressionCondition(condition)
        elif isinstance(condition, Callable):
            self._condition = FuncCondition(condition)
        else:
            self._condition = condition
        self.target = target

    def init(self):
        self._condition.init()

    def set_context(self, context: Context):
        self._condition.set_context(context)

    def evaluate(self) -> bool:
        return self._condition()


class BranchRouter(ContextSetter):
    def __init__(self):
        super().__init__()
        self._branches: list[Branch] = []

    def add_branch(self, condition: Union[str, Callable[[], bool], Condition], target: list[str],
                   branch_id: str = None):
        self._branches.append(Branch(condition, target, branch_id))

    def set_context(self, context: Context):
        for branch in self._branches:
            branch.set_context(context)

    def __call__(self, *args, **kwargs) -> list[str]:
        for branch in self._branches:
            branch.init()
            if branch.evaluate():
                return branch.target
        return []
