import asyncio
import uuid

import sys
import types
import unittest
from unittest.mock import Mock


fake_base = types.ModuleType("base")
fake_base.logger = Mock()

fake_exception_module = types.ModuleType("base")
fake_exception_module.JiuWenBaseException = Mock()

sys.modules["jiuwen.core.common.logging.base"] = fake_base
sys.modules["jiuwen.core.common.exception.base"] = fake_exception_module

from jiuwen.core.runtime.callback_manager import CallbackManager
from jiuwen.core.stream.emitter import StreamEmitter
from jiuwen.core.stream.manager import StreamWriterManager
from jiuwen.core.tracer.handler import TraceAgentHandler, TraceWorkflowHandler
from jiuwen.core.tracer.span import SpanManager

def generate_tracer_id():
    """
    Generate tracer_id, which is also the execution_id.
    """
    return str(uuid.uuid4())
    
    
trace_id = generate_tracer_id()
callback_manager = CallbackManager()
stream_writer_manager = StreamWriterManager(StreamEmitter())
trace_agent_span_manager = SpanManager(trace_id)
trace_workflow_span_manager = SpanManager(trace_id)
trace_agent_handler = TraceAgentHandler(callback_manager, stream_writer_manager, trace_agent_span_manager)
trace_workflow_handler = TraceWorkflowHandler(callback_manager, stream_writer_manager, trace_workflow_span_manager)
callback_manager.register_handler({"tracer_agent": trace_agent_handler})
callback_manager.register_handler({"tracer_workflow": trace_workflow_handler})
tracer_agent_span = trace_agent_span_manager.create_agent_span()
tracer_workflow_span = trace_workflow_span_manager.create_workflow_span()

def tracer_agent():
    callback_manager.trigger("tracer_agent", "on_chain_start", span=tracer_agent_span, inputs={},
                            instance_info={"class_name": "testagentnode"})
    
def tracer_workflow():
    callback_manager.trigger("tracer_workflow", "on_pre_invoke", span=tracer_workflow_span, inputs={},
                            component_metadata={"component_type": "testworkflownode"})
    
async def stream_output():
    async for data in stream_writer_manager.stream_output():
        print(f"Received data: {data}")
            
async def test_stream_output():
    # loop = asyncio.get_event_loop()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop=loop)

    # 创建 asyncio 任务
    task1 = loop.run_in_executor(None, tracer_agent)
    task2 = loop.run_in_executor(None, tracer_workflow)
    task3 = stream_output()
    
    # 并发运行所有任务
    await asyncio.gather(task1, task2, task3)
    
asyncio.run(test_stream_output())
