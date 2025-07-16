import asyncio
from jiuwen.core.context.config import Config
from jiuwen.core.context.context import Context
from jiuwen.core.context.memory.base import InMemoryState
from jiuwen.core.graph.executable import Executable, Input, Output
from jiuwen.core.workflow.base import Workflow
from tests.unit_tests.workflow.test_mock_node import MockNodeBase


class StreamNodeWithTracer(MockNodeBase):
    def __init__(self, node_id: str, datas: list[dict]):
        super().__init__(node_id)
        self._node_id = node_id
        self._datas: list[dict] = datas

    async def invoke(self, inputs: Input, context: Context) -> Output:
        context.state.set_outputs(self.node_id, inputs)
        trace_workflow_span = context.tracer.tracer_workflow_span_manager().last_span
        await context.tracer.trigger("tracer_workflow", "on_invoke", span=trace_workflow_span,
                                     on_invoke_data={"on_invoke_data": "mock with" + str(inputs)})
        context.state.update_trace(trace_workflow_span.invoke_id, trace_workflow_span)
        await asyncio.sleep(5)
        for data in self._datas:
            await asyncio.sleep(1)
            await context.stream_writer_manager.get_custom_writer().write(data)
        print("StreamNode: output = " + str(inputs))
        return inputs


class CompositeWorkflowNode(MockNodeBase):
    def __init__(self, node_id: str, sub_workflow: Workflow):
        super().__init__(node_id)
        self._node_id = node_id
        self._sub_workflow = sub_workflow

    async def invoke(self, inputs: Input, context: Context) -> Output:
        return await self._sub_workflow.invoke(inputs, context)
