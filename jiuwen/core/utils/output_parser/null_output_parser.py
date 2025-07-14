from typing import Iterator

from jiuwen.core.utils.output_parser.base import BaseOutputParser


class NullOutputParser(BaseOutputParser):
    """Null output parser class"""
    def __init__(self, llm_output: dict = None):
        pass

    def stream_parse(self, streaming_input: Iterator[dict]) -> Iterator[dict]:
        """parse in the streaming manner"""
        return streaming_input