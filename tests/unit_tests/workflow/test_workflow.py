import asyncio
import unittest
from collections.abc import Callable

import random

from jiuwen.core.component.branch_comp import BranchComponent
from jiuwen.core.component.condition.array import ArrayCondition
from jiuwen.core.component.loop_callback.intermediate_loop_var import IntermediateLoopVarCallback
from jiuwen.core.component.loop_callback.output import OutputCallback
from jiuwen.core.component.loop_comp import LoopGroup, LoopComponent
from jiuwen.core.component.set_variable_comp import SetVariableComponent
from jiuwen.core.context.config import Config
from jiuwen.core.context.context import Context
from jiuwen.core.context.memory.base import InMemoryState
from jiuwen.core.graph.base import Graph
from jiuwen.core.graph.graph_state import GraphState
from jiuwen.core.workflow.base import WorkflowConfig, Workflow
from jiuwen.graph.pregel.graph import PregelGraph
from test_node import AddTenNode, CommonNode
from tests.unit_tests.workflow.test_mock_node import MockNodeBase, MockStartNode, MockEndNode, Node1


def create_context() -> Context:
    return Context(config=Config(), state=InMemoryState(), store=None, tracer=None)


def create_graph() -> Graph:
    return PregelGraph()


def create_flow() -> Workflow:
    return Workflow(workflow_config=DEFAULT_WORKFLOW_CONFIG, graph=create_graph())


DEFAULT_WORKFLOW_CONFIG = WorkflowConfig(metadata={})


class WorkflowTest(unittest.TestCase):
    def assert_workflow_invoke(self, inputs: dict, context: Context, flow: Workflow, expect_results: dict = None,
                               checker: Callable = None):
        results = flow.invoke(inputs=inputs, context=context)
        if expect_results is not None:
            assert results == expect_results
        elif checker is not None:
            checker(results)

    def assert_workflow_ainvoke(self, inputs: dict, context: Context, flow: Workflow, expect_results: dict = None,
                                checker: Callable = None):
        loop = asyncio.get_event_loop()
        feature = asyncio.ensure_future(flow.ainvoke(inputs=inputs, context=context))
        loop.run_until_complete(feature)
        if expect_results is not None:
            assert feature.result() == expect_results
        elif checker is not None:
            checker(feature.result())

    def test_simple_workflow(self):
        """
        graph : start->a->end
        """
        flow = create_flow()
        flow.set_start_comp("start", MockStartNode("start"),
                            inputs_schema={
                                "a": "${user.inputs.a}",
                                "b": "${user.inputs.b}",
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
        self.assert_workflow_ainvoke({"a": 1, "b": "haha"}, create_context(), flow, expect_results={"result": 1})

    def test_simple_workflow_with_condition(self):
        """
        start -> condition[a,b] -> end
        :return:
        """
        flow = create_flow()
        flow.set_start_comp("start", MockStartNode("start"),
                            inputs_schema={"a": "${user.inputs.a}",
                                           "b": "${user.inputs.b}",
                                           "c": 1,
                                           "d": [1, 2, 3]})

        def router(state: GraphState):
            condition_nodes = ["a", "b"]
            randomIdx = random.randint(1, 2)
            return condition_nodes[randomIdx - 1]

        flow.add_conditional_connection("start", router=router)
        flow.add_workflow_comp("a", Node1("a"), inputs_schema={"a": "${start.a}", "b": "${start.c}"})
        flow.add_workflow_comp("b", Node1("b"), inputs_schema={"b": "${start.b}"})
        flow.set_end_comp("end", MockEndNode("end"), {"result1": "${a.a}", "result2": "${b.b}"})
        flow.add_connection("a", "end")
        flow.add_connection("b", "end")

        def checker(results):
            if "result1" in results:
                assert results["result1"] == 1
            elif "result2" in results:
                assert results["result2"] == "haha"

        self.assert_workflow_invoke({"a": 1, "b": "haha"}, create_context(), flow, checker=checker)
        self.assert_workflow_ainvoke({"a": 1, "b": "haha"}, create_context(), flow, checker=checker)

    def test_workflow_with_branch(self):
        context = create_context()
        flow = create_flow()
        flow.set_start_comp("start", MockStartNode("start"))
        flow.set_end_comp("end", MockEndNode("end"),
                          inputs_schema={"a": "${a.result}", "b": "${b.result}"})

        sw = BranchComponent(context)
        sw.add_branch("${user.inputs.a} <= 10", ["b"], "1")
        sw.add_branch("${user.inputs.a} > 10", ["a"], "2")

        flow.add_workflow_comp("sw", sw)

        flow.add_workflow_comp("a", CommonNode("a"),
                               inputs_schema={"result": "${user.inputs.a}"})

        flow.add_workflow_comp("b", AddTenNode("b"),
                               inputs_schema={"source": "${user.inputs.a}"})

        flow.add_connection("start", "sw")
        flow.add_connection("a", "end")
        flow.add_connection("b", "end")

        result = flow.invoke({"a": 2}, context=context)
        assert result["b"] == 12

        result = flow.invoke({"a": 15}, context=context)
        assert result["a"] == 15

    def test_workflow_with_loop(self):
        flow = create_flow()
        flow.set_start_comp("s", MockStartNode("s"))
        flow.set_end_comp("e", MockEndNode("e"),
                          inputs_schema={"array_result": "${b.array_result}", "user_var": "${b.user_var}"})
        flow.add_workflow_comp("a", CommonNode("a"),
                               inputs_schema={"array": "${user.inputs.input_array}"})
        flow.add_workflow_comp("b", CommonNode("b"),
                               inputs_schema={"array_result": "${l.results}", "user_var": "${l.user_var}"})

        # create  loop: (1->2->3)
        context = create_context()
        loop_group = LoopGroup(context)
        loop_group.add_component("1", AddTenNode("1"), inputs_schema={"source": "${l.arrLoopVar.item}"})
        loop_group.add_component("2", AddTenNode("2"), inputs_schema={"source": "${l.intermediateLoopVar.user_var}"})
        loop_group.add_component("3", SetVariableComponent("3", context,
                                                           {"${l.intermediateLoopVar.user_var}": "${2.result}"}))
        loop_group.start_nodes(["1"])
        loop_group.end_nodes(["3"])
        loop_group.add_connection("1", "2")
        loop_group.add_connection("2", "3")
        output_callback = OutputCallback(context, "l",
                                         {"results": "${1.result}", "user_var": "${l.intermediateLoopVar.user_var}"})
        intermediate_callback = IntermediateLoopVarCallback(context, "l",
                                                            {"user_var": "${user.inputs.input_number}"})

        loop = LoopComponent(context, "l", loop_group, ArrayCondition(context, "l", {"item": "${a.array}"}),
                             callbacks=[output_callback, intermediate_callback])

        flow.add_workflow_comp("l", loop)

        # s->a->(1->2->3)->b->e
        flow.add_connection("s", "a")
        flow.add_connection("a", "l")
        flow.add_connection("l", "b")
        flow.add_connection("b", "e")

        result = flow.invoke({"input_array": [1, 2, 3], "input_number": 1}, context=context)
        assert result == {"array_result": [11, 12, 13], "user_var": 31}

        result = flow.invoke({"input_array": [4, 5], "input_number": 2}, context=context)
        assert result == {"array_result": [14, 15], "user_var": 22}
