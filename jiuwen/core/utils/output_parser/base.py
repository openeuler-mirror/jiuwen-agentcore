from __future__ import annotations

from typing import Any, Iterator


class BaseOutputParser:
    """Base class for output parsers."""
    @classmethod
    def from_config(cls, parse_method: str, parse_config: dict = None) -> BaseOutputParser:
        """create a parser instance"""
        if parse_config is None:
            parse_config = dict()
        if parse_method == "novel_tool":
            from jiuwen.core.utils.output_parser.novel_tool_output_parser import NovelToolOutputParser
            output_parser_cls = NovelToolOutputParser
        else:
            from jiuwen.core.utils.output_parser.null_output_parser import NullOutputParser
            output_parser_cls = NullOutputParser
        return output_parser_cls(**parse_config)

    def parse(self, llm_output: str) -> Any:
        """convert content into its expected format"""
        raise NotImplementedError()

    def stream_parse(self, streaming_inputs: Iterator[dict]) -> Iterator[dict]:
        """parse in the streaming manner"""
        raise NotImplementedError()