import asyncio
import unittest

from jiuwen.core.common.logging.base import logger
from jiuwen.core.context.config import Config
from jiuwen.core.context.context import WorkflowContext
from jiuwen.core.context.state import InMemoryState
from jiuwen.core.stream.emitter import StreamEmitter
from jiuwen.core.stream.manager import StreamWriterManager
from jiuwen.core.stream.writer import TraceSchema, CustomSchema
from jiuwen.core.tracer.tracer import Tracer
from tests.unit_tests.tracer.test_mock_node_with_tracer import StreamNodeWithTracer
from tests.unit_tests.tracer.test_workflow import record_tracer_info, create_flow
from tests.unit_tests.workflow.test_mock_node import MockEndNode, MockStartNode


class MockLLM:
    def __init__(self, tracer):
        self.tracer = tracer

    async def stream(self, span):
        try:
            await self.tracer.trigger("tracer_agent", "on_llm_start", span=span, inputs={"llm": "mock llm"},
                                      instance_info={"class_name": "Openai"})
            await asyncio.sleep(2)
        except Exception as e:
            await self.tracer.trigger("tracer_agent", "on_llm_error", span=span, error=e,
                                      )
            raise e
        finally:
            await self.tracer.trigger("tracer_agent", "on_llm_end", span=span, outputs={"outputs": "mock llm"},
                                      )


class MockPlugin:
    def __init__(self, tracer):
        self.tracer = tracer

    async def stream(self, span):
        try:
            await self.tracer.trigger("tracer_agent", "on_plugin_start", span=span, inputs={"llm": "mock plugin"},
                                      instance_info={"class_name": "RestFulAPI"})
            await asyncio.sleep(2)
        except Exception as e:
            await self.tracer.trigger("tracer_agent", "on_plugin_error", span=span, error=e,
                                      )
            raise e
        finally:
            await self.tracer.trigger("tracer_agent", "on_plugin_end", span=span, outputs={"outputs": "mock plugin"},
                                      )


class MockAgent(unittest.TestCase):
    """
    Agent(llm -> plugin -> workflow)
    """

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.tracer_chunks = []

    def tearDown(self):
        record_tracer_info(self.tracer_chunks, "test_agent_workflow_seq_exec_stream_workflow_with_tracer.json")

    async def run_workflow_seq_exec_stream_workflow_with_tracer(self, tracer: Tracer):
        """
        start -> a -> b -> end
        """

        # workflow与agent共用一个tracer
        context = WorkflowContext(config=Config(), state=InMemoryState(), store=None)
        context.set_tracer(tracer)

        # async def stream_workflow():
        flow = create_flow()
        flow.set_start_comp("start", MockStartNode("start"),
                            inputs_schema={
                                "a": "${a}",
                                "b": "${b}",
                                "c": 1,
                                "d": [1, 2, 3]})

        node_a_expected_datas = [
            {"node_id": "a", "id": 1, "data": "1"},
            {"node_id": "a", "id": 2, "data": "2"},
        ]
        node_a_expected_datas_model = [CustomSchema(**item) for item in node_a_expected_datas]
        flow.add_workflow_comp("a", StreamNodeWithTracer("a", node_a_expected_datas),
                               inputs_schema={
                                   "aa": "${start.a}",
                                   "ac": "${start.c}"})

        node_b_expected_datas = [
            {"node_id": "b", "id": 1, "data": "1"},
            {"node_id": "b", "id": 2, "data": "2"},
        ]
        node_b_expected_datas_model = [CustomSchema(**item) for item in node_b_expected_datas]
        flow.add_workflow_comp("b", StreamNodeWithTracer("b", node_b_expected_datas),
                               inputs_schema={
                                   "ba": "${a.aa}",
                                   "bc": "${a.ac}"})

        flow.set_end_comp("end", MockEndNode("end"),
                          inputs_schema={
                              "result": "${b.ba}"})

        flow.add_connection("start", "a")
        flow.add_connection("a", "b")
        flow.add_connection("b", "end")

        expected_datas_model = {
            "a": node_a_expected_datas_model,
            "b": node_b_expected_datas_model
        }
        index_dict = {key: 0 for key in expected_datas_model.keys()}

        async for chunk in flow.stream({"a": 1, "b": "haha"}, context):
            if not isinstance(chunk, TraceSchema):
                node_id = chunk.node_id
                index = index_dict[node_id]
                assert chunk == expected_datas_model[node_id][index], f"Mismatch at node {node_id} index {index}"
                logger.info(f"stream chunk: {chunk}")
                index_dict[node_id] = index_dict[node_id] + 1
            else:
                print(f"stream chunk: {chunk}")
                self.tracer_chunks.append(chunk)

    async def run_agent_workflow_seq_exec_stream_workflow_with_tracer(self):
        # context手动初始化tracer，agent和workflow共用一个tracer
        context = WorkflowContext(config=Config(), state=InMemoryState(), store=None)
        context.set_stream_writer_manager(StreamWriterManager(StreamEmitter()))
        tracer = Tracer()
        tracer.init(context.stream_writer_manager(), context.callback_manager())
        context.set_tracer(tracer)
        self.tracer = tracer

        agent_span = self.tracer.tracer_agent_span_manager.create_agent_span()
        try:
            await self.tracer.trigger("tracer_agent", "on_chain_start", span=agent_span,
                                      inputs={"intput": "mock chain"},
                                      instance_info={"class_name": "Agent"})  # class_name为必选参数

            # 模拟需要运行llm、plugin
            for runner in [MockLLM(self.tracer), MockPlugin(self.tracer)]:
                runner_span = self.tracer.tracer_agent_span_manager.create_agent_span(agent_span)  # 用于记录父子span关系
                await runner.stream(runner_span)

            # 模拟运行workflow
            await self.run_workflow_seq_exec_stream_workflow_with_tracer(context.tracer())

            await self.tracer.trigger("tracer_agent", "on_chain_end", span=agent_span,
                                      outputs={"outputs": "mock chain"},
                                      )

        except Exception as e:
            await self.tracer.trigger("tracer_agent", "on_chain_error", span=agent_span, error=e,
                                      )
            raise e
        finally:
            await context.stream_writer_manager().stream_emitter.close()

    async def get_stream_output(self):
        async for item in self.tracer._stream_writer_manager.stream_output(need_close=True):
            self.tracer_chunks.append(item)

    def test_agent_workflow_seq_exec_stream_workflow_with_tracer(self):
        async def main():
            await self.run_agent_workflow_seq_exec_stream_workflow_with_tracer()
            await self.get_stream_output()

        self.loop.run_until_complete(main())
