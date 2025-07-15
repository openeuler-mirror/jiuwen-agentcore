import asyncio
from typing import Iterator, AsyncIterator, Callable

from tenacity import sleep

from jiuwen.core.component.base import WorkflowComponent, StartComponent, EndComponent
from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Executable, Input, Output


class MockNodeBase(Executable, WorkflowComponent):
    def __init__(self, node_id: str):
        super().__init__()
        self.node_id = node_id

    async def invoke(self, inputs: Input, context: Context) -> Output:
        pass

    async def stream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        yield await self.invoke(inputs, context)

    async def collect(self, inputs: AsyncIterator[Input], contex: Context) -> Output:
        pass

    async def transform(self, inputs: AsyncIterator[Input], context: Context) -> AsyncIterator[Output]:
        pass

    async def interrupt(self, message: dict):
        return

    def to_executable(self) -> Executable:
        return self


class MockStartNode(StartComponent, MockNodeBase):
    def __init__(self, node_id: str):
        super().__init__(node_id)

    async def invoke(self, inputs: Input, context: Context) -> Output:
        context.state.set_outputs(self.node_id, inputs)
        print("start: output = " + str(inputs))
        return inputs


class MockEndNode(EndComponent, MockNodeBase):
    def __init__(self, node_id: str):
        super().__init__(node_id)
        self.node_id = node_id

    async def invoke(self, inputs: Input, context: Context) -> Output:
        context.state.set_outputs(self.node_id, inputs)
        print("endNode: output = " + str(inputs))
        return inputs


class Node1(MockNodeBase):
    def __init__(self, node_id: str):
        super().__init__(node_id)

    async def invoke(self, inputs: Input, context: Context) -> Output:
        print(self.node_id + ": inputs = " + str(inputs))
        return inputs

class CountNode(MockNodeBase):
    def __init__(self, node_id: str):
        super().__init__(node_id)
        self.times = 0

    async def invoke(self, inputs: Input, context: Context) -> Output:
        self.times += 1
        result = {"count" : self.times}
        print(self.node_id + ": results = " + str(result))
        return result

class SlowNode(MockNodeBase):
    def __init__(self, node_id: str, wait: int):
        super().__init__(node_id)
        self._wait = wait

    async def invoke(self, inputs: Input, context: Context) -> Output:
        await asyncio.sleep(self._wait)
        print(self.node_id + ": input = " + str(inputs))
        return inputs

class StreamNode(MockNodeBase):
    def __init__(self, node_id: str, datas: list[dict]):
        super().__init__(node_id)
        self._node_id = node_id
        self._datas: list[dict] = datas

    async def invoke(self, inputs: Input, context: Context) -> Output:
        for data in self._datas:
            await asyncio.sleep(1)
            await context.stream_writer_manager.get_custom_writer().write(data)
        print("StreamNode: output = " + str(inputs))
        return inputs
