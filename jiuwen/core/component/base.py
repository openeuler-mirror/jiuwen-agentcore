#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from abc import ABC
from dataclasses import dataclass, field
from email.policy import default
from enum import Enum
from typing import Optional

from jiuwen.core.graph.base import Graph
from jiuwen.core.graph.executable import Executable


@dataclass
class WorkflowComponentMetadata:
    node_id: str
    node_type: str
    node_name: str


@dataclass
class ComponentConfig:
    metadata: Optional[WorkflowComponentMetadata] = field(default=None)


@dataclass
class ComponentState:
    comp_id: str
    status: Enum


class WorkflowComponent(ABC):
    def __init__(self):
        pass

    def add_component(self, graph: Graph, node_id: str, wait_for_all: bool = False) -> None:
        graph.add_node(node_id, self.to_executable(), wait_for_all=wait_for_all)

    def to_executable(self) -> Executable:
        pass

class StartComponent(Executable):
    pass

class EndComponent(Executable):
    pass
