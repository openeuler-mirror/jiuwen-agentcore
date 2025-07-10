#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from abc import ABC, abstractmethod
from typing import Any, Union, Optional


class Store(ABC):
    """
    Store is the abstract base class for
    """

    @abstractmethod
    def read(self, key: Union[str, dict]) -> Optional[Any]:
        pass

    @abstractmethod
    def write(self, value: dict) -> None:
        pass


class FileStore(Store):
    def read(self, key: Union[str, dict]) -> Optional[Any]:
        pass

    def write(self, value: dict) -> None:
        pass


class MemoryStore(Store):
    def read(self, key: Union[str, dict]) -> Optional[Any]:
        pass

    def write(self, value: dict) -> None:
        pass
