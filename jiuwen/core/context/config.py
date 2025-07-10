#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from abc import ABC
from typing import TypedDict, Any


class MetadataLike(TypedDict):
    name: str
    event: str


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
        self._stream_edges: dict[str, list[str]] = {}
        self._io_schemas: dict[str, tuple[dict, dict]] = {}
        self.__load_envs__()

    def init(self, io_schemas: dict[str, tuple[dict, dict]], stream_edges: dict[str, list[str]] = None) -> bool:
        self.set_io_schemas(io_schemas)
        self.set_stream_edges(stream_edges)
        return True

    def set_io_schema(self, node_id: str, schema: tuple[dict, dict]) -> None:
        """
        set io schema of single node
        :param node_id: node id
        :param schema: (inputs_schema, outputs_schema)
        """
        self._io_schemas[node_id] = schema

    def set_io_schemas(self, schemas: dict[str, tuple[dict, dict]]) -> None:
        """
        set io schemas
        :param schemas: schemas
        """
        self._io_schemas.update(schemas)

    def get_inputs_schema(self, node_id: str) -> dict:
        """
        get inputs schemas by specific node id
        :param node_id: node id
        :return: inputs schema
        """
        if node_id not in self._io_schemas:
            return {}
        else:
            return self._io_schemas[node_id][0]

    def set_stream_edge(self, source_node_id: str, target_node_id: str) -> None:
        """
        set a single stream edge
        :param source_node_id: source node id
        :param target_node_id: target node id
        """
        self._stream_edges[target_node_id].append(source_node_id)

    def set_stream_edges(self, edges: dict[str, list[str]]) -> None:
        """
        set stream edges
        :param edges: stream edges
        """
        self._stream_edges.update(edges)

    def is_stream_edge(self, source_node_id: str, target_node_id: str) -> bool:
        """
        whether the given edge is a stream edge
        :param source_node_id: source node id
        :param target_node_id: target node id
        :return: true if is stream edge
        """
        return (target_node_id in source_node_id) and (source_node_id in self._stream_edges[target_node_id])

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
