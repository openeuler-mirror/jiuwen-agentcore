import json
import unittest

from jiuwen.core.common.exception.exception import JiuWenBaseException
from jiuwen.core.utils.prompt.assemble.message_handler import validate, messages_to_template, template_to_messages


class TestMessageHandler(unittest.TestCase):
    def test_validate_valid_data(self):
        schema = {"role": str, "content": str}
        data = {"role": "user", "content": "test"}
        try:
            validate(data, schema)
        except JiuWenBaseException as e:
            self.fail("validate raised JiuWenBaseException unexpectedly")

    def test_validate_extra_key(self):
        schema = {"role": str}
        data = {"role": "user", "content": "test"}
        with self.assertRaises(JiuWenBaseException):
            validate(data, schema)

    def test_validate_wrong_type(self):
        schema = {"role": str}
        data = {"role": 234}
        with self.assertRaises(JiuWenBaseException):
            validate(data, schema)

    def test_validate_nested_schema(self):
        data = {"function_call": {"name": "func", "arguments": '{}'}}
        schema = {"function_call": dict}
        extra_schema = {"name": str, "arguments": str}
        try:
            validate(data, schema)
            validate(data["function_call"], extra_schema)
        except JiuWenBaseException:
            self.fail("nested validation raised JiuWenBaseException unexpectedly")

    def test_messages_to_template_basic(self):
        messages = [{"role": "user", "content": "Hello"}]
        expected = "`#user#`\nHello\n"
        self.assertEqual(messages_to_template(messages), expected)

    def test_messages_to_template_with_function_call(self):
        messages = [{
            "role": "assistant", "content": None,
            "function_call": {"name": "func", "arguments": '{}'}
        }]
        expected = "`#assistant#`\n\n`*function_call*`\n" + json.dumps(
            {"name": "func", "arguments": '{}'}, ensure_ascii=False
        ) + "\n"
        self.assertEqual(messages_to_template(messages), expected)

    def test_messages_to_template_invalid_role(self):
        messages = [{"role": "invalid", "content": "test"}]
        with self.assertRaises(JiuWenBaseException):
            messages_to_template(messages)

    def test_template_to_messages_simple(self):
        template = "`#user#`\nHello\n`#system#`\nWelcome\n"
        messages = template_to_messages(template)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0], {"role": "user", "content": "Hello"})
        self.assertEqual(messages[1], {"role": "system", "content": "Welcome"})

    def test_template_to_messages_with_function_call(self):
        template = ("`#assistant#`\n\n`*function_call*`\n"
                    '{"name": "func", "arguments": "{}"}\n')
        messages = template_to_messages(template)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "assistant")
        self.assertIsNone(messages[0]["content"])
        self.assertEqual(messages[0]["function_call"], {"name": "func", "arguments": "{}"})

    def test_template_to_messages_invalid_json(self):
        template = ("`#assistant#`\n\n`*function_call*`\n"
                    'invalid json\n')
        with self.assertRaises(JiuWenBaseException):
            template_to_messages(template)

