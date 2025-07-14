from sqlalchemy.testing.suite.test_reflection import metadata

from jiuwen.core.component.base import StartComponent, EndComponent
from jiuwen.core.context.config import Config
from jiuwen.core.context.context import Context
from jiuwen.core.context.memory.base import InMemoryState
from jiuwen.core.graph.executable import Input, Output
from jiuwen.core.workflow.base import WorkflowConfig, Workflow
from jiuwen.graph.pregel.graph import PregelGraph
from tests.unit_tests.workflow.test_mock_node import MockNodeBase, MockStartNode, MockEndNode


class Node1(MockNodeBase):
    def __init__(self, node_id: str):
        super().__init__(node_id)

    def invoke(self, inputs: Input, context: Context) -> Output:
        return {}


def test_workflow_base():
    workflow_config = WorkflowConfig(metadata = {})
    graph = PregelGraph()

    flow = Workflow(workflow_config=workflow_config, graph=graph)
    flow.add_workflow_comp("a", Node1("a"), inputs_schema={})
    flow.set_start_comp("start", MockStartNode("start"))
    flow.set_end_comp("end", MockEndNode("end"))

    context = Context(config = Config(), state = InMemoryState(), store = None, tracer = None)
    flow.invoke({}, context)


if __name__ == "__main__":
    test_workflow_base()
