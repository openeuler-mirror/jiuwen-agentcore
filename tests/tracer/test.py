import asyncio
import uuid

from jiuwen.core.runtime.callback_manager import CallbackManager
from jiuwen.core.stream.manager import StreamWriterManager
from jiuwen.core.tracer.handler import TraceAgentHandler, TraceWorkflowHandler
from jiuwen.core.tracer.span import SpanManager

def generate_tracer_id():
    """
    Generate tracer_id, which is also the execution_id.
    """
    return str(uuid.uuid4())

async def main():
    trace_id = generate_tracer_id()
    callback_manager = CallbackManager()
    stream_writer_manager = StreamWriterManager()
    trace_agent_span_manager = SpanManager(trace_id)
    trace_workflow_span_manager = SpanManager(trace_id)
    trace_agent_handler = TraceAgentHandler(callback_manager, stream_writer_manager, trace_agent_span_manager)
    trace_workflow_handler = TraceWorkflowHandler(callback_manager, stream_writer_manager, trace_workflow_span_manager)
    callback_manager.register_handler({"tracer_agent": trace_agent_handler})
    callback_manager.register_handler({"tracer_workflow": trace_workflow_handler})
    tracer_agent_span = trace_agent_span_manager.create_agent_span()
    tracer_workflow_span = trace_workflow_span_manager.create_workflow_span()
    callback_manager.trigger("tracer_agent", "on_chain_start", span=tracer_agent_span, inputs={},
                             instance_info={"class_name": "testagentnode"})
    callback_manager.trigger("tracer_workflow", "on_pre_invoke", span=tracer_workflow_span, inputs={},
                             component_metadata={"component_type": "testworkflownode"})
    
if __name__ == '__main__':
    asyncio.run(main())