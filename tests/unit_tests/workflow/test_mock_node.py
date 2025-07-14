import asyncio
from typing import Iterator, AsyncIterator, Callable

from tenacity import sleep

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
        context.state.set_outputs(self.node_id, inputs)
        print("start: output = " + str(inputs))
        return inputs

class MockEndNode(EndComponent, MockNodeBase):
    def __init__(self, node_id: str):
        super().__init__(node_id)
        self.node_id = node_id

    def invoke(self, inputs: Input, context: Context) -> Output:
        context.state.set_outputs(self.node_id, inputs)
        print("endNode: output = " + str(inputs))
        return inputs


class Node1(MockNodeBase):
    def __init__(self, node_id: str):
        super().__init__(node_id)

    def invoke(self, inputs: Input, context: Context) -> Output:
        context.state.set_outputs(self.node_id, inputs)
        print("node1: output = " + str(inputs))
        return inputs


class StreamNode(MockNodeBase):
    def __init__(self, node_id: str, datas: list[dict]):
        super().__init__(node_id)
        self._node_id = node_id
        self._datas:list[dict] = datas

    def stream(self, inputs: Input, context: Context) -> Output:
        for data in self._datas:
            sleep(1)
            context.stream_writer_manager.get_custom_writer().write(data)
            yield data

    async def astream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        for data in self._datas:
            await asyncio.sleep(1)
            await context.stream_writer_manager.get_custom_writer().write(data)
            yield data
