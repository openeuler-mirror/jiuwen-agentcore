from typing import Iterator, AsyncIterator, Callable

from jiuwen.core.component.base import WorkflowComponent, StartComponent, EndComponent
from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Executable, Input, Output


class MockNodeBase(Executable, WorkflowComponent):
    def invoke(self, inputs: Input, context: Context) -> Output:
        pass

    def __init__(self, node_id: str):
        super().__init__()
        self.node_id = node_id

    def stream(self, inputs: Input, context: Context) -> Iterator[Output]:
        yield self.invoke(inputs, context)

    async def ainvoke(self, inputs: Input, context: Context) -> Output:
        yield await self.invoke(inputs, context)

    async def astream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        yield await self.invoke(inputs, context)

    def interrupt(self, message: dict):
        return

    def to_executable(self) -> Executable:
        return self

class MockStartNode(StartComponent, MockNodeBase):
    def __init__(self, node_id: str):
        super().__init__(node_id)

    def invoke(self, inputs: Input, context: Context) -> Output:
        return inputs

class MockEndNode(EndComponent, MockNodeBase):
    def __init__(self, node_id: str):
        super().__init__(node_id)

    def invoke(self, inputs: Input, context: Context) -> Output:
        return inputs


class Node1(MockNodeBase):
    def __init__(self, node_id: str):
        super().__init__(node_id)

    def invoke(self, inputs: Input, context: Context) -> Output:
        return {}