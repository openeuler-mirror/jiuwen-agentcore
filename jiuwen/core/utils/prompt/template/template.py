from typing import Union, List, Dict

from pydantic import BaseModel, Field

from jiuwen.core.utils.llm.messages import BaseMessage
from jiuwen.core.utils.prompt.assemble.assembler import Assembler
from jiuwen.core.utils.prompt.assemble.message_handler import template_to_messages


class Template(BaseModel):
    """
    template data

    """
    name: str
    content: Union[List[Dict], List[BaseMessage], str]
    filters: dict = Field(default=None)

    def to_messages(self) -> List[BaseMessage]:
        """Return Template as a list of Messages."""
        messages = []
        if self.content is None or len(self.content) == 0:
            self.content = []
            return messages
        if isinstance(self.content, str):
            self.content = template_to_messages(self._content)

        for msg in self.content:
            if isinstance(msg, BaseMessage):
                messages.append(msg)
            elif isinstance(msg, dict):
                messages.append(BaseMessage(**msg))
            else:
                pass
        self.content = messages
        return self.content

    def format(self, keywords: dict = None):
        """format prompt"""
        assembler = Assembler(self.content)
        input_keys = assembler.input_keys
        format_dict = {}
        for key in input_keys:
            if keywords and keywords.get(key):
                format_dict[key] = keywords.get(key)
        self.content = assembler.assemble(**format_dict)
