from enum import Enum
from typing import Dict, Any


class StreamMode(Enum):

    def __new__(cls, mode: str, desc: str, options: Dict[str, Any] = None):
        obj = object.__new__(cls)
        obj._value_ = mode
        obj.mode = mode
        obj.desc = desc
        obj.options = options or {}
        return obj

    def __str__(self):
        return f"StreamMode(mode={self.mode}, desc={self.desc}, options={self.options})"


class BaseStreamMode(StreamMode):
    OUTPUT = ("output", "Standard stream data defined by the framework")
    TRACE = ("trace", "Trace stream data produced by the graph")
    CUSTOM = ("custom", "Custom stream data defined by the runnable")
