from typing import Union, List, Dict, Optional

from pydantic import BaseModel


class BaseMessage(BaseModel):
    role: str
    content: Union[str, List[Union[str, Dict]]]
    name: Optional[str] = None