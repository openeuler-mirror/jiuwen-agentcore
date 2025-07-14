"""
Interface for template index
"""
import copy
import json
from abc import ABC, abstractmethod

from jiuwen.core.utils.prompt.template.template import Template


class TemplateStore(ABC):
    """Template operation"""
    @staticmethod
    def _convert_to_dict(input_template: Template) -> dict[str, any]:
        """convert template value to str"""
        template = copy.deepcopy(input_template)
        for attr, value in input_template.__dict__.items():
            if value is None:
                setattr(template, attr, '')
            elif isinstance(value, dict):
                setattr(template, attr, json.dumps(value))
            else:
                setattr(template, attr, str(value))
        return template.model_dump()

    @abstractmethod
    def delete_template(self, name: str, filters: dict) -> bool:
        """delete template by name"""

    @abstractmethod
    def register_template(self, template: Template) -> bool:
        """register template"""

    @abstractmethod
    def search_template(self, name: str, filters: dict) -> Template:
        """search template by name"""

    @abstractmethod
    def update_template(self, template: Template, **kwargs) -> bool:
        """update template by name"""
