import json
import sys
import types
from unittest.mock import Mock

from jiuwen.core.component.workflow_comp import ExecWorkflowComponent

fake_base = types.ModuleType("base")
fake_base.logger = Mock()

fake_exception_module = types.ModuleType("base")
fake_exception_module.JiuWenBaseException = Mock()

sys.modules["jiuwen.core.common.logging.base"] = fake_base
sys.modules["jiuwen.core.common.exception.base"] = fake_exception_module

from tests.unit_tests.tracer.test_mock_node_with_tracer import StreamNodeWithTracer, CompositeWorkflowNode
from jiuwen.core.common.logging.base import logger

import asyncio
import unittest
from collections.abc import Callable

from jiuwen.core.context.config import Config
from jiuwen.core.context.context import Context
from jiuwen.core.context.memory.base import InMemoryState
from jiuwen.core.graph.base import Graph
from jiuwen.core.workflow.base import WorkflowConfig, Workflow
from jiuwen.core.stream.writer import CustomSchema
from jiuwen.graph.pregel.graph import PregelGraph
from tests.unit_tests.workflow.test_mock_node import MockStartNode, MockEndNode
from jiuwen.core.stream.writer import TraceSchema


def create_context_with_tracer() -> Context:
    return Context(config=Config(), state=InMemoryState(), store=None)


def create_graph() -> Graph:
    return PregelGraph()


def create_flow() -> Workflow:
    return Workflow(workflow_config=DEFAULT_WORKFLOW_CONFIG, graph=create_graph())


DEFAULT_WORKFLOW_CONFIG = WorkflowConfig()


def record_tracer_info(tracer_chunks, file_path):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            for chunk in tracer_chunks:
                json_data = json.dumps(chunk.model_dump(), default=str, ensure_ascii=False)
                f.write(json_data + "\n")
        print(f"调测信息已保存到文件：{file_path}")
    except Exception as e:
        print(f"调测信息保存失败：{e}")


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def invoke_workflow(self, inputs: dict, context: Context, flow: Workflow):
        feature = asyncio.ensure_future(flow.invoke(inputs=inputs, context=context))
        self.loop.run_until_complete(feature)
        return feature.result()

    def assert_workflow_invoke(self, inputs: dict, context: Context, flow: Workflow, expect_results: dict = None,
                               checker: Callable = None):
        if expect_results is not None:
            assert self.invoke_workflow(inputs, context, flow) == expect_results
        elif checker is not None:
            checker(self.invoke_workflow(inputs, context, flow))

    def test_seq_exec_stream_workflow_with_tracer(self):
        """
        start -> a -> b -> end
        """
        tracer_chunks = []

        async def stream_workflow():
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

            async for chunk in flow.stream({"a": 1, "b": "haha"}, create_context_with_tracer()):
                if not isinstance(chunk, TraceSchema):
                    node_id = chunk.node_id
                    index = index_dict[node_id]
                    assert chunk == expected_datas_model[node_id][index], f"Mismatch at node {node_id} index {index}"
                    logger.info(f"stream chunk: {chunk}")
                    index_dict[node_id] = index_dict[node_id] + 1
                else:
                    print(f"stream chunk: {chunk}")
                    tracer_chunks.append(chunk)

        self.loop.run_until_complete(stream_workflow())
        record_tracer_info(tracer_chunks, "test_seq_exec_stream_workflow_with_tracer.json")

    def test_parallel_exec_stream_workflow_with_tracer(self):
        """
        start -> a | b -> end
        """
        tracer_chunks = []

        async def stream_workflow():
            flow = create_flow()
            flow.set_start_comp("start", MockStartNode("start"),
                                inputs_schema={
                                    "a": "${user.inputs.a}",
                                    "b": "${user.inputs.b}",
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
                                       "ba": "${start.b}",
                                       "bc": "${start.d}"})

            flow.set_end_comp("end", MockEndNode("end"),
                              inputs_schema={
                                  "result": "${b.ba}"})

            flow.add_connection("start", "a")
            flow.add_connection("start", "b")
            flow.add_connection("a", "end")
            flow.add_connection("b", "end")

            expected_datas_model = {
                "a": node_a_expected_datas_model,
                "b": node_b_expected_datas_model
            }
            index_dict = {key: 0 for key in expected_datas_model.keys()}
            async for chunk in flow.stream({"a": 1, "b": "haha"}, create_context_with_tracer()):
                if not isinstance(chunk, TraceSchema):
                    node_id = chunk.node_id
                    index = index_dict[node_id]
                    assert chunk == expected_datas_model[node_id][index], f"Mismatch at node {node_id} index {index}"
                    logger.info(f"stream chunk: {chunk}")
                    index_dict[node_id] = index_dict[node_id] + 1
                else:
                    print(f"stream chunk: {chunk}")
                    tracer_chunks.append(chunk)

        self.loop.run_until_complete(stream_workflow())
        record_tracer_info(tracer_chunks, "test_parallel_exec_stream_workflow_with_tracer.json")

    def test_sub_stream_workflow_with_tracer(self):
        """
        main_workflow: start -> a(sub_workflow) -> end
        sub_workflow: sub_start -> sub_a -> sub_end
        """
        tracer_chunks = []

        async def stream_workflow():
            # sub_workflow: start->a(stream out)->end
            sub_workflow = create_flow()
            sub_workflow.set_start_comp("sub_start", MockStartNode("start"),
                                        inputs_schema={
                                            "a": "${a}",
                                            "b": "${b}",
                                            "c": 1,
                                            "d": [1, 2, 3]})
            expected_datas = [
                {"node_id": "sub_start", "id": 1, "data": "1"},
                {"node_id": "sub_start", "id": 2, "data": "2"},
            ]
            expected_datas_model = [CustomSchema(**item) for item in expected_datas]

            sub_workflow.add_workflow_comp("sub_a", StreamNodeWithTracer("a", expected_datas),
                                           inputs_schema={
                                               "aa": "${sub_start.a}",
                                               "ac": "${sub_start.c}"})
            sub_workflow.set_end_comp("sub_end", MockEndNode("end"),
                                      inputs_schema={
                                          "result": "${sub_a.aa}"})
            sub_workflow.add_connection("sub_start", "sub_a")
            sub_workflow.add_connection("sub_a", "sub_end")

            # main_workflow: start->a(sub workflow)->end
            main_workflow = create_flow()
            main_workflow.set_start_comp("start", MockStartNode("start"),
                                         inputs_schema={
                                             "a": "${a}",
                                             "b": "${b}",
                                             "c": 1,
                                             "d": [1, 2, 3]})

            main_workflow.add_workflow_comp("a", ExecWorkflowComponent("a", sub_workflow),
                                            inputs_schema={
                                                "aa": "${start.a}",
                                                "ac": "${start.c}"})
            main_workflow.set_end_comp("end", MockEndNode("end"),
                                       inputs_schema={
                                           "result": "${a.aa}"})
            main_workflow.add_connection("start", "a")
            main_workflow.add_connection("a", "end")

            index = 0
            async for chunk in main_workflow.stream({"a": 1, "b": "haha"}, create_context_with_tracer()):
                if not isinstance(chunk, TraceSchema):
                    assert chunk == expected_datas_model[index], f"Mismatch at index {index}"
                    logger.info(f"stream chunk: {chunk}")
                    index += 1
                else:
                    print(f"stream chunk: {chunk}")
                    tracer_chunks.append(chunk)

        self.loop.run_until_complete(stream_workflow())
        record_tracer_info(tracer_chunks, "test_sub_stream_workflow_with_tracer.json")

    def test_nested_stream_workflow_with_tracer(self):
        """
        main_workflow: start -> a(sub_workflow) | b -> end
        sub_workflow: sub_start -> sub_a -> sub_end
        """
        tracer_chunks = []

        async def stream_workflow():
            # sub_workflow: start->a(stream out)->end
            sub_workflow = create_flow()
            sub_workflow.set_start_comp("sub_start", MockStartNode("start"),
                                        inputs_schema={
                                            "a": "${a}",
                                            "b": "${b}",
                                            "c": 1,
                                            "d": [1, 2, 3]})
            expected_datas = [
                {"node_id": "sub_start", "id": 1, "data": "1"},
                {"node_id": "sub_start", "id": 2, "data": "2"},
            ]
            expected_datas_model = [CustomSchema(**item) for item in expected_datas]

            sub_workflow.add_workflow_comp("sub_a", StreamNodeWithTracer("a", expected_datas),
                                           inputs_schema={
                                               "aa": "${sub_start.a}",
                                               "ac": "${sub_start.c}"})
            sub_workflow.set_end_comp("sub_end", MockEndNode("end"),
                                      inputs_schema={
                                          "result": "${sub_a.aa}"})
            sub_workflow.add_connection("sub_start", "sub_a")
            sub_workflow.add_connection("sub_a", "sub_end")

            # main_workflow: start->a(sub workflow) | b ->end
            main_workflow = create_flow()
            main_workflow.set_start_comp("start", MockStartNode("start"),
                                         inputs_schema={
                                             "a": "${a}",
                                             "b": "${b}",
                                             "c": 1,
                                             "d": [1, 2, 3]})

            main_workflow.add_workflow_comp("a", ExecWorkflowComponent("a", sub_workflow),
                                            inputs_schema={
                                                "aa": "${start.a}",
                                                "ac": "${start.c}"})

            node_b_expected_datas = [
                {"node_id": "b", "id": 1, "data": "1"},
                {"node_id": "b", "id": 2, "data": "2"},
            ]
            node_b_expected_datas_model = [CustomSchema(**item) for item in node_b_expected_datas]
            main_workflow.add_workflow_comp("b", StreamNodeWithTracer("b", node_b_expected_datas),
                                            inputs_schema={
                                                "ba": "${start.b}",
                                                "bc": "${start.d}"})

            main_workflow.set_end_comp("end", MockEndNode("end"),
                                       inputs_schema={
                                           "result": "${a.aa}"})
            main_workflow.add_connection("start", "a")
            main_workflow.add_connection("a", "end")
            main_workflow.add_connection("start", "b")
            main_workflow.add_connection("b", "end")

            async for chunk in main_workflow.stream({"a": 1, "b": "haha"}, create_context_with_tracer()):
                if isinstance(chunk, TraceSchema):
                    print(f"stream chunk: {chunk}")
                    tracer_chunks.append(chunk)

        self.loop.run_until_complete(stream_workflow())
        for chunk in tracer_chunks:
            payload = chunk.payload
            payload.get("parentInvokeId")
            payload.get("parentNodeId")
            if payload.get("invokeId") == "start":
                assert payload.get("parentInvokeId") == None, f"start node parent_invoke_id should be None"
                assert payload.get("parentNodeId") == "", f"a node parent_node_id should be ''"
            elif payload.get("invokeId") == "a":
                assert payload.get("parentInvokeId") == "start", f"a node parent_invoke_id should be start"
                assert payload.get("parentNodeId") == "", f"a node parent_node_id should be ''"
            elif payload.get("invokeId") == "b":
                assert payload.get("parentInvokeId") == "a", f"b node parent_invoke_id should be a"
                assert payload.get("parentNodeId") == "", f"b node parent_node_id should be ''"
            elif payload.get("invokeId") == "end":
                assert payload.get("parentInvokeId") == "b", f"b node parent_invoke_id should be a"
                assert payload.get("parentNodeId") == "", f"b node parent_node_id should be ''"
            elif payload.get("invokeId") == "sub_start":
                assert payload.get("parentInvokeId") == None, f"sub_start node parent_invoke_id should be None"
                assert payload.get("parentNodeId") == "a", f"sub_start node parent_node_id should be a"
            elif payload.get("invokeId") == "sub_a":
                assert payload.get("parentInvokeId") == "sub_start", f"sub_a node parent_invoke_id should be sub_start"
                assert payload.get("parentNodeId") == "a", f"sub_a node parent_node_id should be a"
            elif payload.get("invokeId") == "sub_end":
                assert payload.get("parentInvokeId") == "sub_a", f"sub_end node parent_invoke_id should be sub_a"
                assert payload.get("parentNodeId") == "a", f"sub_end node parent_node_id should be a"
        record_tracer_info(tracer_chunks, "test_nested_stream_workflow_with_tracer.json")
