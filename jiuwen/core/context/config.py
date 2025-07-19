#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from abc import ABC
from typing import TypedDict, Any, Optional

from jiuwen.core.common.configs.workflow_config import WorkflowMetadata
from jiuwen.core.context.state import Transformer

class MetadataLike(TypedDict):
    name: str
    event: str

class CompIOConfig(ABC):
    def __init__(self, inputs_schema: dict = None,
                 outputs_schema: dict = None,
                 inputs_transformer: Transformer = None,
                 outputs_transformer: Transformer = None):
        self.inputs_schema = inputs_schema
        self.outputs_schema = outputs_schema
        self.inputs_transformer = inputs_transformer
        self.outputs_transformer = outputs_transformer

class WorkflowConfig:
    metadata: WorkflowMetadata = WorkflowMetadata()
    comp_configs: dict[str, CompIOConfig] = {}
    stream_edges: dict[str, list[str]] = {}

class Config(ABC):
    """
    Config is the class defines the basic infos of workflow
    """

    def __init__(self):
        """
        initialize the config
        """
        self._callback_metadata: dict[str, MetadataLike] = {}
        self._env: dict = {}
        self._workflow_config: WorkflowConfig = WorkflowConfig()
        self.__load_envs__()

    def set_workflow_config(self, workflow_config: WorkflowConfig) -> None:
        self._workflow_config = workflow_config

    def set_comp_io_config(self, node_id: str, comp_io_config: CompIOConfig) -> None:
        """
        set io schema of single node
        :param node_id: node id
        :param comp_io_config: component io config
        """
        self._workflow_config.comp_configs[node_id] = comp_io_config

    def get_inputs_schema(self, node_id: str) -> dict:
        """
        get inputs schemas by specific node id
        :param node_id: node id
        :return: inputs schema
        """
        if node_id not in self._workflow_config.comp_configs:
            return {}
        else:
            return self._workflow_config.comp_configs[node_id].inputs_schema

    def get_outputs_schema(self, node_id: str) -> dict:
        """
        get outputs schemas by specific node id
        :param node_id: node id
        :return: outputs schema
        """
        if node_id not in self._workflow_config.comp_configs:
            return {}
        else:
            return self._workflow_config.comp_configs[node_id].outputs_schema

    def get_input_transformer(self, node_id: str) -> Optional[Transformer]:
        """
        get inputs transformer by specific node id
        :param node_id: node id
        :return: transformer
        """
        if node_id not in self._workflow_config.comp_configs:
            return None
        else:
            return self._workflow_config.comp_configs[node_id].inputs_transformer

    def get_output_transformer(self, node_id: str) -> Optional[Transformer]:
        """
        get output transformer by specific node id
        :param node_id: node id
        :return: transformer
        """
        if node_id not in self._workflow_config.comp_configs:
            return None
        else:
            return self._workflow_config.comp_configs[node_id].outputs_transformer

    def set_stream_edge(self, source_node_id: str, target_node_id: str) -> None:
        """
        set a single stream edge
        :param source_node_id: source node id
        :param target_node_id: target node id
        """
        self._workflow_config.stream_edges[source_node_id].append(target_node_id)

    def set_stream_edges(self, edges: dict[str, list[str]]) -> None:
        """
        set stream edges
        :param edges: stream edges
        """
        self._workflow_config.stream_edges.update(edges)

    def is_stream_edge(self, source_node_id: str, target_node_id: str) -> bool:
        """
        whether the given edge is a stream edge
        :param source_node_id: source node id
        :param target_node_id: target node id
        :return: true if is stream edge
        """
        return (target_node_id in source_node_id) and (source_node_id in self._workflow_config.stream_edges[target_node_id])

    def set_envs(self, envs: dict[str, str]) -> None:
        """
        set environment variables
        :param envs: envs
        """
        self._env.update(envs)

    def get_env(self, key: str) -> Any:
        """
        get environment variable by given key
        :param key: environment variable key
        :return: environment variable value
        """
        if key in self._env:
            return self._env[key]
        else:
            return None

    def __load_envs__(self) -> None:
        pass
