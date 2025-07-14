from abc import abstractmethod
from typing import List, Optional

from jiuwen.core.common.exception.exception import JiuWenBaseException
from jiuwen.core.common.exception.status_code import StatusCode


class Variable:
    """Base class for variable."""
    def __init__(self, name: str, input_keys: Optional[List] = None):
        self.name = name
        self.input_keys = input_keys
        self.value = ""

    @abstractmethod
    def update(self, **kwargs):
        """update variable."""

    def eval(self, **kwargs):
        """Validate the input key-values, update `self.value`, perform selection (if there is), and return value.
        Args:
            **kwargs: input key-value pairs for validate the variable.
        Returns:
            str: updated value of variable.
        """
        input_kwargs = self._prepare_inputs(**kwargs)
        self.update(**input_kwargs)
        return self.value

    def _prepare_inputs(self, **kwargs) -> dict:
        """prepare input key-value pairs."""
        missing_keys = set(self.input_keys) - set(kwargs.keys())
        if missing_keys:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_ASSEMBLER_INPUT_KEY_ERROR.code,
                message=f"Missing keys for updating the variable {self.name}: {list(missing_keys)}"
            )
        unexpected_keys = set(kwargs.keys()) - set(self.input_keys)
        if unexpected_keys:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_ASSEMBLER_INPUT_KEY_ERROR.code,
                message=f"Unexpected keys for updating the variable {self.name}: {list(unexpected_keys)}"
            )
        input_kwargs = {k:v for k, v in kwargs.items() if k in self.input_keys}
        return input_kwargs