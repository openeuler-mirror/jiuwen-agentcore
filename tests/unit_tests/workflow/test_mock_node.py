import asyncio
from typing import AsyncIterator

from jiuwen.core.common.logging.base import logger
from jiuwen.core.component.base import WorkflowComponent, StartComponent, EndComponent
from jiuwen.core.context.config import Config
from jiuwen.core.context.context import Context
from jiuwen.core.context.memory.base import InMemoryState
from jiuwen.core.graph.executable import Executable, Input, Output
from jiuwen.core.stream.writer import OutputSchema
from jiuwen.core.workflow.base import Workflow
from jiuwen.core.graph.interrupt.interaction import Interaction


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
        logger.info("start: output{%s} ", inputs)
        return inputs


class MockEndNode(EndComponent, MockNodeBase):
    def __init__(self, node_id: str):
        super().__init__(node_id)
        self.node_id = node_id

    async def invoke(self, inputs: Input, context: Context) -> Output:
        logger.info("endNode: output %s ", inputs)
        return inputs


class Node1(MockNodeBase):
    def __init__(self, node_id: str):
        super().__init__(node_id)

    async def invoke(self, inputs: Input, context: Context) -> Output:
        logger.info(self.node_id + ": inputs = " + str(inputs))
        return inputs


class CountNode(MockNodeBase):
    def __init__(self, node_id: str):
        super().__init__(node_id)
        self.times = 0

    async def invoke(self, inputs: Input, context: Context) -> Output:
        self.times += 1
        result = {"count": self.times}
        logger.info(self.node_id + ": results = " + str(result))
        return result


class SlowNode(MockNodeBase):
    def __init__(self, node_id: str, wait: int):
        super().__init__(node_id)
        self._wait = wait

    async def invoke(self, inputs: Input, context: Context) -> Output:
        await asyncio.sleep(self._wait)
        logger.info(self.node_id + ": input = " + str(inputs))
        return inputs


class StreamNode(MockNodeBase):
    def __init__(self, node_id: str, datas: list[dict]):
        super().__init__(node_id)
        self._node_id = node_id
        self._datas: list[dict] = datas

    async def invoke(self, inputs: Input, context: Context) -> Output:
        for data in self._datas:
            await asyncio.sleep(0.1)
            logger.info(f"StreamNode[{self._node_id}], stream frame: {data}")
            await context.stream_writer_manager.get_custom_writer().write(data)
        logger.info(f"StreamNode[{self._node_id}], batch output: {inputs}")
        return inputs


class StreamNodeWithSubWorkflow(MockNodeBase):
    def __init__(self, node_id: str, sub_workflow: Workflow):
        super().__init__(node_id)
        self._node_id = node_id
        self._sub_workflow = sub_workflow

    async def invoke(self, inputs: Input, context: Context) -> Output:
        async for chunk in self._sub_workflow.stream({"a": 1, "b": "haha"}, context):
            logger.info(f"StreamNodeWithSubWorkflow[{self._node_id}], stream frame: {chunk}")
            await context.stream_writer_manager.get_custom_writer().write(chunk)
        logger.info(f"StreamNodeWithSubWorkflow[{self._node_id}], batch output: {inputs}")
        return inputs


class MockStartNode4Cp(StartComponent, MockNodeBase):
    def __init__(self, node_id: str):
        super().__init__(node_id)
        self.runtime = 0

    async def invoke(self, inputs: Input, context: Context) -> Output:
        self.runtime += 1
        value = context.state.get("a")
        if value is not None:
            assert Exception("value is not None")
        print("start: output = " + str(inputs))
        context.state.update({"a": 10})
        return inputs


class Node4Cp(MockNodeBase):
    def __init__(self, node_id: str):
        super().__init__(node_id)
        self.runtime = 0

    async def invoke(self, inputs: Input, context: Context) -> Output:
        self.runtime += 1
        value = context.state.get("a")
        if value < 20:
            raise Exception("value < 20")
        return inputs


class AddTenNode4Cp(Executable, WorkflowComponent):
    raise_exception = True

    def __init__(self, node_id: str):
        super().__init__()
        self.node_id = node_id

    async def invoke(self, inputs: Input, context: Context) -> Output:
        if self.raise_exception:
            self.raise_exception = False
            raise Exception("inner error: " + str(inputs["source"]))
        self.raise_exception = True
        return {"result": inputs["source"] + 10}

    async def stream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        yield await self.invoke(inputs, context)

    async def collect(self, inputs: AsyncIterator[Input], contex: Context) -> Output:
        pass

    async def transform(self, inputs: AsyncIterator[Input], context: Context) -> AsyncIterator[Output]:
        pass

    async def interrupt(self, message: dict):
        pass

    def to_executable(self) -> Executable:
        return self


class InteractiveNode4Cp(MockNodeBase):
    def __init__(self, node_id: str):
        super().__init__(node_id)

    async def invoke(self, inputs: Input, context: Context) -> Output:
        interaction = Interaction(ctx=context)
        result1 = interaction.user_input("Please enter any key")
        print(result1)
        result = interaction.user_input("Please enter any key")
        return result


class InteractiveNode4StreamCp(MockNodeBase):
    def __init__(self, node_id):
        super().__init__(node_id)

    async def invoke(self, inputs: Input, context: Context) -> Output:
        interaction = Interaction(ctx=context)
        result = interaction.user_input("Please enter any key")
        stream_writer = context.stream_writer_manager.get_output_writer()
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(
                stream_writer.write(OutputSchema(type="output", index=0, payload=(self.node_id, result))))
        else:
            loop.run_until_complete(
                stream_writer.write(OutputSchema(type="output", index=0, payload=(self.node_id, result))))
        return result
