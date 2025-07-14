import unittest

from jiuwen.core.utils.output_parser.novel_tool_output_parser import NovelToolOutputParser


class TestOutputParser(unittest.TestCase):
    def setUp(self):
        self.parser = NovelToolOutputParser()

    def test_parser_valid_function_call(self):
        llm_output = {
            "message": {
                "content": "[my_function(param1='value1', param2=123, param3=True)]"
            }
        }
        expected_output = {
            'message':
                {
                    'content': '',
                    'llm_content': "[my_function(param1='value1', param2=123, param3=True)]",
                    'tool_calls':
                        [
                            {
                                'function': {
                                    'arguments': '{"param1=\'value1\'": "param1", "param2=123": "param2", "param3=True": "param3"}',
                                    'name': 'my_function'
                                },
                                'type': 'function'
                            }
                        ]
                }
        }
        output = self.parser.parse(llm_output)

        self.assertEqual(output, expected_output)

    def test_parser_invalid_function_call(self):
        llm_output = {
            "message": {
                "content": "invalid_function_call_string"
            }
        }
        self.assertEqual(self.parser.parse(llm_output), llm_output)