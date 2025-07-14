import json
import re
from typing import Iterator

from jiuwen.core.utils.output_parser.base import BaseOutputParser

MESSAGE_KEY = "message"
CONTENT_KEY = "content"
TOOL_CALLS_KEY = "tool_calls"
LLM_CONTENT_KEY = "llm_content"


class NovelToolOutputParser(BaseOutputParser):
    """Novel tool output parser"""
    def parse(self, llm_output: dict) -> dict:
        """parse the llm output content"""
        content = llm_output.get(MESSAGE_KEY, {}).get(CONTENT_KEY, "")
        match_result = re.findall(r'^\[([a-zA-Z\d_]+)\(([\s\S]*)\)\]', content.strip())
        if match_result:
            function_match = match_result[0]
            arguments = dict()
            params_pattern = re.compile(r'(\w+)\s*=\s*(.*?)(?=\s*,\s*\w+\s*=|$)')
            for argument_match in params_pattern.finditer(function_match[1]):
                value_str = argument_match[1].strip().replace('\'', '"')
                try:
                    arg_value = json.loads(value_str)
                except json.JSONDecodeError as _:
                    arg_value = argument_match[1]
                arguments[argument_match[0]] = arg_value
            function_call = {
                "type": "function",
                "function": {
                    "name": function_match[0].strip(),
                    "arguments": json.dumps(arguments, ensure_ascii=False)
                }
            }
        else:
            function_call = {}
        if function_call:
            message = llm_output.setdefault(MESSAGE_KEY, {})
            message[TOOL_CALLS_KEY] = [function_call]
            message[LLM_CONTENT_KEY] = message.get(CONTENT_KEY, '')
            message[CONTENT_KEY] = ''
        return llm_output

    def stream_parse(self, streaming_inputs: Iterator[dict]) -> Iterator[dict]:
        """parse the streaming input"""
        is_valid_tool_call = True
        cached_tokens = ""

        for output in streaming_inputs:
            if output.get("type", "") == "full_result":
                output = self.parse(output)
                yield output
            else:
                cached_tokens += output.get(MESSAGE_KEY, {}).get(TOOL_CALLS_KEY, "")
                if is_valid_tool_call:
                    if len(cached_tokens) > 0 and cached_tokens[0] != "[":
                        is_valid_tool_call = False
                    if len(cached_tokens) > 1:
                        if "(" in cached_tokens:
                            func_name = cached_tokens[1: cached_tokens.index("(")]
                        else:
                            func_name = cached_tokens[1:]
                        res = re.match(r"^[a-zA-Z\d_]+$", func_name)
                        if not res:
                            is_valid_tool_call = False
                    if not is_valid_tool_call:
                        output[MESSAGE_KEY][CONTENT_KEY] = cached_tokens
                        yield output
                        continue
                if not is_valid_tool_call:
                    yield output