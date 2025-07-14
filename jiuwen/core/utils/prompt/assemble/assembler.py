import re
from copy import deepcopy
from typing import Union, List, Dict

from jiuwen.core.common.exception.exception import JiuWenBaseException
from jiuwen.core.common.exception.status_code import StatusCode
from jiuwen.core.utils.llm.messages import BaseMessage
from jiuwen.core.utils.prompt.assemble.variables.textable import TextableVariable
from jiuwen.core.utils.prompt.assemble.variables.variable import Variable
from jiuwen.core.utils.prompt.assemble.message_handler import messages_to_template, template_to_messages


class Assembler:
    """class for creating prompt based on a given template"""

    def __init__(self,
                 template_content: Union[List[Dict], List[BaseMessage], str],
                 return_format: str = "message",
                 **variables):
        if isinstance(template_content, List):
            try:
                template_content = messages_to_template(template_content)
            except Exception as e:
                raise JiuWenBaseException(
                    error_code=StatusCode.PROMPT_ASSEMBLER_TEMPLATE_FORMAT_ERROR.code,
                    message="The List-type prompt should confirm to the format of LLM message, please check."
                ) from e
        self.return_format = return_format
        template_formater = TextableVariable(template_content, name="__inner__")
        for name, variable in variables.items():
            if name not in template_formater.input_keys:
                raise JiuWenBaseException(
                    error_code=StatusCode.PROMPT_ASSEMBLER_INIT_ERROR.code,
                    message=f"Variable {name} is not defined in the Template."
                )
            if not isinstance(variable, Variable):
                raise JiuWenBaseException(
                    error_code=StatusCode.PROMPT_ASSEMBLER_INIT_ERROR.code,
                    message=f"Variable {name} must be instantiated as a `Variable` object."
                )
        for placeholder in template_formater.input_keys:
            if placeholder in variables:
                variables[placeholder].name = placeholder
            else:
                variables[placeholder] = TextableVariable(name=placeholder, text="{{" + placeholder + "}}")
        self.prompt = ""
        self.variables = variables
        self._template_formater = template_formater

    @property
    def input_keys(self) -> List[str]:
        """Get the list of argument names for updating all the variables"""
        keys = []
        for variable in self.variables.values():
            keys.extend(variable.input_keys)
        return list(set(keys))

    def assemble(self, **kwargs) -> Union[str, List[dict]]:
        """Update the variables and format the template into a string-type or message-type prompt"""
        kwargs = {k: v for k, v in kwargs.items() if v is not None and k in self.input_keys}
        all_kwargs = {}
        for k in self.input_keys:
            if k not in kwargs:
                all_kwargs[k] = ""
        all_kwargs.update(**kwargs)
        self._update(**all_kwargs)
        return self._format()

    def _update(self, **kwargs) -> None:
        """Update the variables based on the arguments passed in as key-value pairs"""
        missing_keys = set(self.input_keys) - set(kwargs.keys())
        if missing_keys:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_ASSEMBLER_TEMPLATE_FORMAT_ERROR.code,
                message=f"Missing keys for updating the assembler: {list(missing_keys)}"
            )
        unexpected_keys = set(kwargs.keys()) - set(self.input_keys)
        if unexpected_keys:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_ASSEMBLER_TEMPLATE_FORMAT_ERROR.code,
                message=f"Unexpected keys for updating the assembler: {list(unexpected_keys)}"
            )
        for variable in self.variables.values():
            input_kwargs = {k: v for k, v in kwargs.items() if k in variable.input_keys}
            variable.eval(**input_kwargs)

    def _format(self) -> Union[str, List[dict]]:
        """Substitute placeholders in the template with variables values and get formatted prompt."""
        format_kwargs = {var.name: var.value for var in self.variables.values()}
        formatted_prompt = self._template_formater.eval(**format_kwargs)
        message_prefix_matches = list(re.finditer(r'`#(system|assistant|user|tool|function)#`', formatted_prompt))
        if self.return_format == "text" or not message_prefix_matches:
            self.prompt = formatted_prompt
            return formatted_prompt
        return deepcopy(template_to_messages(formatted_prompt))
