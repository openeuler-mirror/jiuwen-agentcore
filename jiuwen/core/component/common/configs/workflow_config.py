from pydantic import BaseModel, Field


class WorkflowMetadata(BaseModel):
    name: str = Field(default="")
    id: str = Field(default="")
    version: str = Field(default="")
