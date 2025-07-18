#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
import re
from typing import Optional, Any, Union

from jiuwen.core.common.exception.exception import JiuWenBaseException

REGEX_MAX_LENGTH = 1000
NESTED_PATH_LIST_PATTERN = re.compile(r'^([\w]+)((?:\[\d+\])*)$')
NESTED_PATH_SPLIT = '.'
NESTED_PATH_LIST_SPLIT = "["


def update_dict(update: dict, source: dict) -> None:
    """
    update source dict by update dict
    Note: source is unnested structure, update is nested structure

    :param update: update dict, which key is nested
    :param source: source dict, which key must not be nested
    """
    for key, value in update.items():
        current_key, current = root_to_path(key, source, create_if_absent=True)
        update_by_key(current_key, value, current)

    def get(self, key: Union[str, list, dict]) -> Optional[Any]:
        if isinstance(key, str):
            origin_key = extract_origin_key(key)
            return get_value_by_nested_path(origin_key, self._state)
        elif isinstance(key, dict):
            result = {}
            for target_key, target_schema in key.items():
                result[target_key] = self.get(target_schema)
            return result
        elif isinstance(key, list):
            result = []
            for item in key:
                result.append(self.get(item))
            return result
        else:
            return key

def get_by_schema(schema: Union[str, list, dict], data: dict) -> Any:
    if schema is None or data is None:
        return None
    if isinstance(schema, str):
        origin_key = extract_origin_key(schema)
        return get_value_by_nested_path(origin_key, data)
    elif isinstance(schema, dict):
        result = {}
        for target_key, target_schema in schema.items():
            result[target_key] = get_by_schema(target_schema, data)
        return result
    elif isinstance(schema, list):
        result = []
        for item in schema:
            result.append(get_by_schema(item, data))
        return result
    else:
        return schema


def get_value_by_nested_path(nested_key: str, source: dict) -> Optional[Any]:
    result = root_to_path(nested_key, source)
    if result[1] is None:
        return None
    if result[0] not in result[1]:
        return None
    return result[1][result[0]]


def split_nested_path(nested_key: str) -> list:
    '''
    split nested path
    :param nested_key: path
    :return: e.g. a_1.b.c[1].d -> ["a_1", "b", "c", 1, "d"]
    '''

    if (NESTED_PATH_SPLIT not in nested_key) and (NESTED_PATH_LIST_SPLIT not in nested_key):
        return []
    final_list = []
    params = nested_key.split(NESTED_PATH_SPLIT)
    pattern = re.compile(r'^([\w]+)((?:\[\d+\])*)$')
    for param in params:
        match = re.match(pattern, param)
        if match:
            index = match.group(2)
            if len(index) > 0:
                numbers = re.findall(r'\d+', index)
                idxes = [int(num) if str.isdigit(num) else num for num in numbers]
                if len(idxes) == 0:
                    raise JiuWenBaseException(1, "failed to split nested path")
                final_list.append((match.group(1), idxes))
            else:
                final_list.append(match.group(1))
    return final_list

def is_ref_path(path: str) -> bool:
    return len(path) > 3 and path.startswith("${") and path.endswith("}")

def extract_origin_key(key: str) -> str:
    """
    extract the origin key from given key if the given key is reference structure
    e.g. "${start123.p2}" -> "start123.p2"
    :param key: reference key
    :return: origin key
    """
    if '$' not in key:
        return key
    pattern = re.compile(r"\${(.+?)\}")
    match = pattern.search(key, endpos=REGEX_MAX_LENGTH)
    if match:
        return match.group(1)
    return key

def update_by_key(key: Union[str, int], new_value: Any, source: dict) -> None:
    if key not in source:
        source[key] = expand_nested_structure(new_value)
        return
    if isinstance(source[key], dict) and isinstance(new_value, dict):
        update_dict(new_value, source[key])
    else:
        source[key] = expand_nested_structure(new_value)


def expand_nested_structure(data: Any) -> Any:
    if isinstance(data, list) or isinstance(data, tuple):
        result = []
        for item in data:
            result.append(expand_nested_structure(item))
        return result
    elif isinstance(data, dict):
        result = {}
        for key, value in data.items():
            current_key, current = root_to_path(key, result, create_if_absent=True)
            current[current_key] = expand_nested_structure(value)
        return result
    else:
        return data


def root_to_path(nested_path: str, source: dict, create_if_absent: bool = False) -> tuple[Union[str, int], dict]:
    paths = split_nested_path(nested_path)
    if len(paths) == 0:
        return (nested_path, source)
    current = source
    for i in range(len(paths)):
        if not isinstance(current, dict):
            return (None, None)
        path = paths[i]
        if isinstance(path, str):
            if path not in current:
                if not create_if_absent:
                    return (None, None)
                current[path] = {}
            if i == len(paths) - 1:
                return (path, current)
            elif not isinstance(current[path], dict) and create_if_absent:
                current[path] = {}
            current = current[path]
        else:
            token = path[0]
            if token not in current:
                if not create_if_absent:
                    return (None, None)
                current[token] = []
            current = current[token]
            if i == len(paths) - 1:
                return root_to_index(path[1], current, create_if_absent)
            else:
                idx, current = root_to_index(path[1], current, create_if_absent)
                if current is None:
                    return (None, None)
                current = current[idx]
    return (None, None)


def root_to_index(idxes: list[int], source: dict, create_if_absent: bool = False) -> Optional[tuple[int, dict]]:
    current = source
    if len(idxes) > 1:
        for idx in idxes[:-1]:
            if idx >= len(current):
                if not create_if_absent:
                    return None
                current += [None] * (idx - len(source) - idx)
                current.append([])
        current = current[idx]
    if idxes[-1] >= len(source):
        if not create_if_absent:
            return None
        current += [None] * (idxes[-1] - len(source))
        current.append({})
    return idxes[-1], current


if __name__ == '__main__':
    source = {}
    # 增加a.b: nums属性
    update_dict({"a.b.nums": [1, 2, 3]}, source)
    print(source)
    # 增加a.b: name属性
    update_dict({
        "a.b.name": "shanghai"
    }, source)
    print(source)
    # 增加a.b: class属性
    update_dict({"a.b": {"class":"hha"}}, source)
    print(source)
    # 覆盖a.b所有
    update_dict({"a.b": [1,2,3]}, source)
    print(source)
