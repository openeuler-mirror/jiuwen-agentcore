import asyncio
import unittest
from collections.abc import Callable

from jiuwen.core.common.logging.base import logger
from jiuwen.core.component.branch_comp import BranchComponent
from jiuwen.core.component.break_comp import BreakComponent
from jiuwen.core.component.condition.array import ArrayCondition
from jiuwen.core.component.condition.number import NumberCondition
from jiuwen.core.component.loop_callback.intermediate_loop_var import IntermediateLoopVarCallback
from jiuwen.core.component.loop_callback.output import OutputCallback
from jiuwen.core.component.loop_comp import LoopGroup, LoopComponent
from jiuwen.core.component.set_variable_comp import SetVariableComponent
from jiuwen.core.component.workflow_comp import ExecWorkflowComponent
from jiuwen.core.context.config import Config
from jiuwen.core.context.context import Context, WorkflowContext
from jiuwen.core.context.state import InMemoryState
from jiuwen.core.context.state import ReadableStateLike
from jiuwen.core.graph.base import Graph
from jiuwen.core.graph.executable import Input
from jiuwen.core.graph.graph_state import GraphState
from jiuwen.core.workflow.base import Workflow
from jiuwen.core.workflow.workflow_config import WorkflowConfig, ComponentAbility
from jiuwen.core.stream.base import BaseStreamMode
from jiuwen.core.stream.writer import CustomSchema
from jiuwen.core.workflow.base import WorkflowConfig, Workflow
from jiuwen.graph.pregel.graph import PregelGraph
from test_mock_node import SlowNode, CountNode, StreamCompNode, CollectCompNode, MultiCollectCompNode, TransformCompNode
from test_node import AddTenNode, CommonNode
from tests.unit_tests.workflow.test_mock_node import MockStartNode, MockEndNode, Node1, StreamNode


def create_context() -> Context:
    return WorkflowContext(config=Config(), state=InMemoryState(), store=None)


def create_graph() -> Graph:
    return PregelGraph()


def create_flow() -> Workflow:
    return Workflow(workflow_config=DEFAULT_WORKFLOW_CONFIG, graph=create_graph())


DEFAULT_WORKFLOW_CONFIG = WorkflowConfig()


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def invoke_workflow(self, inputs: Input, context: Context, flow: Workflow):
        feature = asyncio.ensure_future(flow.invoke(inputs=inputs, context=context))
        self.loop.run_until_complete(feature)
        return feature.result()

    def assert_workflow_invoke(self, inputs: dict, context: Context, flow: Workflow, expect_results: dict = None,
                               checker: Callable = None):
        if expect_results is not None:
            assert self.invoke_workflow(inputs, context, flow) == expect_results
        elif checker is not None:
            checker(self.invoke_workflow(inputs, context, flow))

    def test_simple_workflow(self):
        # flow1: start -> a -> end
        flow = create_flow()
        flow.set_start_comp("start", MockStartNode("start"),
                            inputs_schema={
                                "a": "${a}",
                                "b": "${b}",
                                "c": 1,
                                "d": [1, 2, 3]})
        flow.add_workflow_comp("a", Node1("a"),
                               inputs_schema={
                                   "aa": "${start.a}",
                                   "ac": "${start.c}"})
        flow.set_end_comp("end", MockEndNode("end"),
                          inputs_schema={
                              "result": "${a.aa}"})
        flow.add_connection("start", "a")
        flow.add_connection("a", "end")
        self.assert_workflow_invoke({"a": 1, "b": "haha"}, create_context(), flow, expect_results={"result": 1})

        flow2 = create_flow()
        flow2.set_start_comp("start", MockStartNode("start"),
                             inputs_schema={
                                 "a1": "${a1}",
                                 "a2": "${a2}"})

        # flow2: start->a1|a2->end
        flow2.add_workflow_comp("a1", Node1("a1"), inputs_schema={"value": "${start.a1}"})
        flow2.add_workflow_comp("a2", Node1("a2"), inputs_schema={"value": "${start.a2}"})

        flow2.set_end_comp("end", MockEndNode("end"), inputs_schema={"b1": "${a1.value}", "b2": "${a2.value}"})
        flow2.add_connection("start", "a1")
        flow2.add_connection("start", "a2")
        flow2.add_connection("a1", "end")
        flow2.add_connection("a2", "end")
        self.assert_workflow_invoke({"a1": 1, "a2": 2}, create_context(), flow2, expect_results={"b1": 1, "b2": 2})

    def test_simple_workflow_with_condition(self):
        """
        start -> condition[a,b] -> end
        """
        flow = create_flow()
        flow.set_start_comp("start", MockStartNode("start"),
                            inputs_schema={"a": "${a}",
                                           "b": "${b}",
                                           "c": 1,
                                           "d": [1, 2, 3]})
        choose = "a"

        def router(state: GraphState):
            return choose

        flow.add_conditional_connection("start", router=router)
        flow.add_workflow_comp("a", Node1("a"), inputs_schema={"a": "${start.a}", "b": "${start.c}"})
        flow.add_workflow_comp("b", Node1("b"), inputs_schema={"b": "${start.b}"})
        flow.set_end_comp("end", MockEndNode("end"), {"result1": "${a.a}", "result2": "${b.b}"})
        flow.add_connection("a", "end")
        flow.add_connection("b", "end")
        self.assert_workflow_invoke({"a": 1, "b": "haha"}, create_context(), flow,
                                    expect_results={"result1": 1, "result2": None})
        choose = "b"
        self.assert_workflow_invoke({"a": 1, "b": "haha"}, create_context(), flow,
                                    expect_results={"result1": None, "result2": "haha"})

    def test_workflow_with_wait_for_all(self):
        # flow: start -> (a->a1)|b|c|d -> collect -> end
        for waitForAll in [True, False]:
            flow = create_flow()

            def start_input_transformer(state: ReadableStateLike):
                start_input_schema = {"a": "${a}", "b": "${b}", "c": "${c}",
                                      "d": "${d}"}
                return state.get(start_input_schema)

            flow.set_start_comp("start", MockStartNode("start"), inputs_transformer=start_input_transformer)
            flow.add_workflow_comp("a", Node1("a"), inputs_schema={"a": "${start.a}"})
            flow.add_workflow_comp("a1", SlowNode("a1", 1), inputs_schema={"a": "${a.a}"})
            flow.add_workflow_comp("b", Node1("b"), inputs_schema={"b": "${start.b}"})
            flow.add_workflow_comp("c", Node1("c"), inputs_schema={"c": "${start.c}"})
            flow.add_workflow_comp("d", Node1("d"), inputs_schema={"d": "${start.d}"})
            flow.add_workflow_comp("collect", CountNode("collect"), wait_for_all=waitForAll)
            flow.set_end_comp("end", MockEndNode("end"), {"result": "${collect.count}"})
            flow.add_connection("start", "a")
            flow.add_connection("start", "b")
            flow.add_connection("start", "c")
            flow.add_connection("start", "d")
            flow.add_connection("a", "a1")
            flow.add_connection("a1", "collect")
            flow.add_connection("b", "collect")
            flow.add_connection("c", "collect")
            flow.add_connection("d", "collect")
            flow.add_connection("collect", "end")
            if waitForAll:
                self.assert_workflow_invoke({"a": 1, "b": 2, "c": 3, "d": 4}, create_context(), flow,
                                            expect_results={"result": 1})
            else:
                self.assert_workflow_invoke({"a": 1, "b": 2, "c": 3, "d": 4}, create_context(), flow,
                                            expect_results={"result": 2})

    def test_workflow_with_branch(self):
        flow = create_flow()
        flow.set_start_comp("start", MockStartNode("start"))
        flow.set_end_comp("end", MockEndNode("end"),
                          inputs_schema={"a": "${a.result}", "b": "${b.result}"})

        sw = BranchComponent()
        sw.add_branch("${a} <= 10", ["b"], "1")
        sw.add_branch("${a} > 10", ["a"], "2")

        flow.add_workflow_comp("sw", sw)

        flow.add_workflow_comp("a", CommonNode("a"),
                               inputs_schema={"result": "${a}"})

        flow.add_workflow_comp("b", AddTenNode("b"),
                               inputs_schema={"source": "${a}"})

        flow.add_connection("start", "sw")
        flow.add_connection("a", "end")
        flow.add_connection("b", "end")

        result = self.invoke_workflow({"a": 2}, create_context(), flow)
        assert result["b"] == 12

        result = self.invoke_workflow({"a": 15}, create_context(), flow)
        assert result["a"] == 15

    def test_workflow_with_loop(self):
        flow = create_flow()
        flow.set_start_comp("s", MockStartNode("s"))
        flow.set_end_comp("e", MockEndNode("e"),
                          inputs_schema={"array_result": "${b.array_result}", "user_var": "${b.user_var}"})
        flow.add_workflow_comp("a", CommonNode("a"),
                               inputs_schema={"array": "${input_array}"})
        flow.add_workflow_comp("b", CommonNode("b"),
                               inputs_schema={"array_result": "${l.results}", "user_var": "${l.user_var}"})

        # create  loop: (1->2->3)
        loop_group = LoopGroup(WorkflowConfig(), PregelGraph())
        loop_group.add_workflow_comp("1", AddTenNode("1"), inputs_schema={"source": "${l.arrLoopVar.item}"})
        loop_group.add_workflow_comp("2", AddTenNode("2"),
                                     inputs_schema={"source": "${l.intermediateLoopVar.user_var}"})
        set_variable_component = SetVariableComponent("3",
                                                      {"${l.intermediateLoopVar.user_var}": "${2.result}"})
        loop_group.add_workflow_comp("3", set_variable_component)
        loop_group.start_comp("1")
        loop_group.end_comp("3")
        loop_group.add_connection("1", "2")
        loop_group.add_connection("2", "3")
        output_callback = OutputCallback("l",
                                         {"results": "${1.result}", "user_var": "${l.intermediateLoopVar.user_var}"})
        intermediate_callback = IntermediateLoopVarCallback("l",
                                                            {"user_var": "${input_number}"})

        loop = LoopComponent("l", loop_group, PregelGraph(), ArrayCondition("l", {"item": "${a.array}"}),
                             callbacks=[output_callback, intermediate_callback],
                             set_variable_components=[set_variable_component])

        flow.add_workflow_comp("l", loop)

        # s->a->(1->2->3)->b->e
        flow.add_connection("s", "a")
        flow.add_connection("a", "l")
        flow.add_connection("l", "b")
        flow.add_connection("b", "e")

        result = self.invoke_workflow({"input_array": [1, 2, 3], "input_number": 1}, create_context(), flow)
        assert result == {"array_result": [11, 12, 13], "user_var": 31}

        result = self.invoke_workflow({"input_array": [4, 5], "input_number": 2}, create_context(), flow)
        assert result == {"array_result": [14, 15], "user_var": 22}

    def test_workflow_with_loop_break(self):
        flow = create_flow()
        flow.set_start_comp("s", MockStartNode("s"))
        flow.set_end_comp("e", MockEndNode("e"),
                          inputs_schema={"array_result": "${b.array_result}", "user_var": "${b.user_var}"})
        flow.add_workflow_comp("a", CommonNode("a"),
                               inputs_schema={"array": "${input_array}"})
        flow.add_workflow_comp("b", CommonNode("b"),
                               inputs_schema={"array_result": "${l.results}", "user_var": "${l.user_var}"})

        # create  loop: (1->2->3)
        loop_group = LoopGroup(WorkflowConfig(), PregelGraph())
        loop_group.add_workflow_comp("1", AddTenNode("1"), inputs_schema={"source": "${l.arrLoopVar.item}"})
        loop_group.add_workflow_comp("2", AddTenNode("2"),
                                     inputs_schema={"source": "${l.intermediateLoopVar.user_var}"})
        set_variable_component = SetVariableComponent("3",
                                                      {"${l.intermediateLoopVar.user_var}": "${2.result}"})
        loop_group.add_workflow_comp("3", set_variable_component)
        break_node = BreakComponent()
        loop_group.add_workflow_comp("4", break_node)
        loop_group.start_nodes(["1"])
        loop_group.end_nodes(["3"])
        loop_group.add_connection("1", "2")
        loop_group.add_connection("2", "3")
        loop_group.add_connection("3", "4")
        output_callback = OutputCallback("l",
                                         {"results": "${1.result}", "user_var": "${l.intermediateLoopVar.user_var}"})
        intermediate_callback = IntermediateLoopVarCallback("l",
                                                            {"user_var": "${input_number}"})

        loop = LoopComponent("l", loop_group, PregelGraph(), ArrayCondition("l", {"item": "${a.array}"}),
                             callbacks=[output_callback, intermediate_callback], break_nodes=[break_node],
                             set_variable_components=[set_variable_component])

        flow.add_workflow_comp("l", loop)

        # s->a->(1->2->3)->b->e
        flow.add_connection("s", "a")
        flow.add_connection("a", "l")
        flow.add_connection("l", "b")
        flow.add_connection("b", "e")

        result = self.invoke_workflow({"input_array": [1, 2, 3], "input_number": 1}, create_context(), flow)
        assert result == {"array_result": [11], "user_var": 11}

        result = self.invoke_workflow({"input_array": [4, 5], "input_number": 2}, create_context(), flow)
        assert result == {"array_result": [14], "user_var": 12}

    def test_workflow_with_loop_number_condition(self):
        flow = create_flow()
        flow.set_start_comp("s", MockStartNode("s"))
        flow.set_end_comp("e", MockEndNode("e"),
                          inputs_schema={"array_result": "${b.array_result}", "user_var": "${b.user_var}"})
        flow.add_workflow_comp("a", CommonNode("a"))
        flow.add_workflow_comp("b", CommonNode("b"),
                               inputs_schema={"array_result": "${l.results}", "user_var": "${l.user_var}"})

        # create  loop: (1->2->3)
        loop_group = LoopGroup(WorkflowConfig(), PregelGraph())
        loop_group.add_workflow_comp("1", AddTenNode("1"), inputs_schema={"source": "${l.index}"})
        loop_group.add_workflow_comp("2", AddTenNode("2"),
                                     inputs_schema={"source": "${l.intermediateLoopVar.user_var}"})
        set_variable_component = SetVariableComponent("3",
                                                      {"${l.intermediateLoopVar.user_var}": "${2.result}"})
        loop_group.add_workflow_comp("3", set_variable_component)
        loop_group.start_nodes(["1"])
        loop_group.end_nodes(["3"])
        loop_group.add_connection("1", "2")
        loop_group.add_connection("2", "3")
        output_callback = OutputCallback("l",
                                         {"results": "${1.result}", "user_var": "${l.intermediateLoopVar.user_var}"})
        intermediate_callback = IntermediateLoopVarCallback("l",
                                                            {"user_var": "${input_number}"})

        loop = LoopComponent("l", loop_group, PregelGraph(), NumberCondition("l", "${loop_number}"),
                             callbacks=[output_callback, intermediate_callback],
                             set_variable_components=[set_variable_component])

        flow.add_workflow_comp("l", loop)

        # s->a->(1->2->3)->b->e
        flow.add_connection("s", "a")
        flow.add_connection("a", "l")
        flow.add_connection("l", "b")
        flow.add_connection("b", "e")

        result = self.invoke_workflow({"input_number": 1, "loop_number": 3}, create_context(), flow)
        assert result == {"array_result": [10, 11, 12], "user_var": 31}

        result = self.invoke_workflow({"input_number": 2, "loop_number": 2}, create_context(), flow)
        assert result == {"array_result": [10, 11], "user_var": 22}

    def test_simple_stream_workflow(self):
        async def stream_workflow():
            flow = create_flow()
            flow.set_start_comp("start", MockStartNode("start"),
                                inputs_schema={
                                    "a": "${a}",
                                    "b": "${b}",
                                    "c": 1,
                                    "d": [1, 2, 3]})
            expected_datas = [
                {"id": 1, "data": "1"},
                {"id": 2, "data": "2"},
            ]
            expected_datas_model = [CustomSchema(**item) for item in expected_datas]

            flow.add_workflow_comp("a", StreamNode("a", expected_datas),
                                   inputs_schema={
                                       "aa": "${start.a}",
                                       "ac": "${start.c}"})
            flow.set_end_comp("end", MockEndNode("end"),
                              inputs_schema={
                                  "result": "${a.aa}"})
            flow.add_connection("start", "a")
            flow.add_connection("a", "end")

            index = 0
            async for chunk in flow.stream({"a": 1, "b": "haha"}, create_context()):
                if not isinstance(chunk, CustomSchema):
                    continue
                assert chunk == expected_datas_model[index], f"Mismatch at index {index}"
                logger.info(f"stream chunk: {chunk}")
                index += 1

        self.loop.run_until_complete(stream_workflow())

    def test_seq_exec_stream_workflow(self):
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
            flow.add_workflow_comp("a", StreamNode("a", node_a_expected_datas),
                                   inputs_schema={
                                       "aa": "${start.a}",
                                       "ac": "${start.c}"})

            node_b_expected_datas = [
                {"node_id": "b", "id": 1, "data": "1"},
                {"node_id": "b", "id": 2, "data": "2"},
            ]
            node_b_expected_datas_model = [CustomSchema(**item) for item in node_b_expected_datas]
            flow.add_workflow_comp("b", StreamNode("b", node_b_expected_datas),
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
            async for chunk in flow.stream({"a": 1, "b": "haha"}, create_context()):
                if not isinstance(chunk, CustomSchema):
                    continue
                node_id = chunk.node_id
                index = index_dict[node_id]
                assert chunk == expected_datas_model[node_id][index], f"Mismatch at node {node_id} index {index}"
                logger.info(f"stream chunk: {chunk}")
                index_dict[node_id] = index_dict[node_id] + 1

        self.loop.run_until_complete(stream_workflow())

    def test_parallel_exec_stream_workflow(self):
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
            flow.add_workflow_comp("a", StreamNode("a", node_a_expected_datas),
                                   inputs_schema={
                                       "aa": "${start.a}",
                                       "ac": "${start.c}"})

            node_b_expected_datas = [
                {"node_id": "b", "id": 1, "data": "1"},
                {"node_id": "b", "id": 2, "data": "2"},
            ]
            node_b_expected_datas_model = [CustomSchema(**item) for item in node_b_expected_datas]
            flow.add_workflow_comp("b", StreamNode("b", node_b_expected_datas),
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
            async for chunk in flow.stream({"a": 1, "b": "haha"}, create_context()):
                if not isinstance(chunk, CustomSchema):
                    continue
                node_id = chunk.node_id
                index = index_dict[node_id]
                assert chunk == expected_datas_model[node_id][index], f"Mismatch at node {node_id} index {index}"
                logger.info(f"stream chunk: {chunk}")
                index_dict[node_id] = index_dict[node_id] + 1

        self.loop.run_until_complete(stream_workflow())

    def test_sub_stream_workflow(self):
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

            sub_workflow.add_workflow_comp("sub_a", StreamNode("a", expected_datas),
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
            async for chunk in main_workflow.stream({"a": 1, "b": "haha"}, create_context(),
                                                    stream_modes=[BaseStreamMode.CUSTOM]):
                assert chunk == expected_datas_model[index], f"Mismatch at index {index}"
                logger.info(f"stream chunk: {chunk}")
                index += 1

        self.loop.run_until_complete(stream_workflow())

    def test_nested_workflow(self):
        flow1 = create_flow()
        flow1.set_start_comp("start", MockStartNode("start"),
                             inputs_schema={
                                 "a1": "${a1}",
                                 "a2": "${a2}"})

        # start2->a2->end2
        flow2 = create_flow()
        flow2.set_start_comp("start2", MockStartNode("start2"), inputs_schema={"a1": "${result}"})
        flow2.add_workflow_comp("a2", Node1("a2"), inputs_schema={"value": "${start2.a1}"})
        flow2.set_end_comp("end2", MockEndNode("end2"), inputs_schema={"result": "${a2.value}"})
        flow2.add_connection("start2", "a2")
        flow2.add_connection("a2", "end2")

        # flow2: start->a1|composite->end
        flow1.add_workflow_comp("a1", Node1("a1"), inputs_schema={"value": "${start.a1}"})
        flow1.add_workflow_comp("composite", ExecWorkflowComponent("composite", flow2),
                                inputs_schema={"result": "${start.a2}"})

        flow1.set_end_comp("end", MockEndNode("end"), inputs_schema={"b1": "${a1.value}", "b2": "${composite.result}"})
        flow1.add_connection("start", "a1")
        flow1.add_connection("start", "composite")
        flow1.add_connection("a1", "end")
        flow1.add_connection("composite", "end")
        self.assert_workflow_invoke({"a1": 1, "a2": 2}, create_context(), flow1, expect_results={"b1": 1, "b2": 2})

    def test_stream_comp_workflow(self):
        # start -> a ---> b -> end
        flow = create_flow()
        flow.set_start_comp("start", MockStartNode("start"), inputs_schema={"a": "${a}"})
        flow.add_workflow_comp("a", StreamCompNode("a"), inputs_schema={"value": "${start.a}"}, comp_ability=[ComponentAbility.STREAM])
        flow.add_workflow_comp("b", CollectCompNode("b"), inputs_schema={"value": "${a.value}"}, stream_inputs_schema={"value": "${a.value}"}, comp_ability=[ComponentAbility.COLLECT])
        flow.set_end_comp("end", MockEndNode("end"), inputs_schema={"result": "${b.value}"})
        flow.add_connection("start", "a")
        flow.add_stream_connection("a", "b")
        flow.add_connection("b", "end")
        idx = 1
        self.assert_workflow_invoke({"a": idx}, create_context(), flow, expect_results={"result": idx * sum(range(1, 3))})

    def test_transform_workflow(self):
        # start -> a ---> b ---> c -> end
        flow = create_flow()
        flow.set_start_comp("start", MockStartNode("start"), inputs_schema={"a": "${a}"})
        # a: throw 2 frames: {value: 1}, {value: 2}
        flow.add_workflow_comp("a", StreamCompNode("a"), inputs_schema={"value": "${start.a}"}, comp_ability=[ComponentAbility.STREAM])
        # b: transform 2 frames to c
        flow.add_workflow_comp("b", TransformCompNode("b"), inputs_schema={"value": "${a.value}"}, stream_inputs_schema={"value": "${a.value}"}, comp_ability=[ComponentAbility.TRANSFORM])
        # c: value = sum(value of frames)
        flow.add_workflow_comp("c", CollectCompNode("c"), inputs_schema={"value": "${b.value}"}, stream_inputs_schema={"value": "${b.value}"}, comp_ability=[ComponentAbility.COLLECT])
        flow.set_end_comp("end", MockEndNode("end"), inputs_schema={"result": "${c.value}"})
        flow.add_connection("start", "a")
        flow.add_stream_connection("a", "b")
        flow.add_stream_connection("b", "c")
        flow.add_connection("c", "end")

        self.assert_workflow_invoke({"a": 1}, create_context(), flow, expect_results={"result": 3})