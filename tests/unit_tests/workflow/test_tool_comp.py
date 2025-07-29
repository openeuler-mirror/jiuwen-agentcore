from unittest.mock import patch, Mock, MagicMock

import pytest

from jiuwen.core.agent.task.task_context import TaskContext
from jiuwen.core.component.tool_comp import ToolComponentConfig, ToolExecutable, ToolComponent
from jiuwen.core.context.context import Context
from jiuwen.core.utils.tool.service_api.param import Param
from jiuwen.core.utils.tool.service_api.restful_api import RestfulApi
from tests.unit_tests.workflow.test_mock_node import MockStartNode, MockEndNode
from tests.unit_tests.workflow.test_workflow import create_flow


@pytest.fixture
def fake_ctx():
    from unittest.mock import MagicMock
    ctx = MagicMock(spec=Context)
    ctx.store = MagicMock()
    ctx.store.read.return_value = []
    return ctx


@pytest.fixture()
def mock_tool_config():
    return ToolComponentConfig(
        needValidate=False
    )


@pytest.fixture
def mock_tool_input():
    return {
        'userFields': {
            'location': 'Beijing',
            'date': 15
        },
        'validated': False
    }


@pytest.fixture
def mock_tool():
    return RestfulApi(
        name="test",
        description="test",
        params=[Param(name="location", description="location", type='string'),
                Param(name="date", description="date", type='int')],
        path="http://127.0.0.1:8000",
        headers={},
        method="GET",
        response=[],
    )


@patch('requests.request')
@patch('jiuwen.core.component.tool_comp.ToolExecutable.get_tool')
@pytest.mark.asyncio
async def test_tool_comp_invoke(mock_get_tool, mock_request, mock_tool, mock_tool_config, mock_tool_input, fake_ctx):
    mock_get_tool.return_value = mock_tool
    tool_executable = ToolExecutable(mock_tool_config)

    # mock request的response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "{}"
    mock_response.content = b"{}"
    mock_request.return_value = mock_response
    res = await tool_executable.invoke(mock_tool_input, fake_ctx)

    assert res.get('errCode') == 0


@patch('jiuwen.core.component.tool_comp.ToolExecutable.invoke')
@patch('jiuwen.core.component.tool_comp.ToolExecutable.get_tool')
@pytest.mark.asyncio
async def test_tool_comp_in_workflow(mock_get_tool, mock_invoke, mock_tool, mock_tool_config, fake_ctx):
    mock_get_tool.return_value = mock_tool
    mock_invoke.return_value = 'res'
    context = TaskContext(id="test")
    flow = create_flow()

    start_component = MockStartNode("s")
    end_component = MockEndNode("e")
    tool_component = ToolComponent(mock_tool_config)

    flow.set_start_comp("s", start_component)
    flow.set_end_comp("e", end_component)
    flow.add_workflow_comp("tool", tool_component)

    flow.add_connection("s", "tool")
    flow.add_connection("tool", "e")

    await flow.invoke({}, context.create_workflow_context())
