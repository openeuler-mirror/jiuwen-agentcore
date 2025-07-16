import uuid

from jiuwen.core.tracer.handler import TraceAgentHandler, TraceWorkflowHandler, TracerHandlerName
from jiuwen.core.tracer.span import SpanManager


class Tracer:
    def __init__(self):
        self._callback_manager = None
        self._trace_id = str(uuid.uuid4())
        self._tracer_agent_span_manager = SpanManager(self._trace_id)
        self._tracer_workflow_span_manager = SpanManager(self._trace_id)

    def init(self, stream_writer_manager, callback_manager):
        trace_agent_handler = TraceAgentHandler(callback_manager, stream_writer_manager,
                                                self._tracer_agent_span_manager)
        trace_workflow_handler = TraceWorkflowHandler(callback_manager, stream_writer_manager,
                                                      self._tracer_workflow_span_manager)
        callback_manager.register_handler({TracerHandlerName.TRACE_AGENT.value: trace_agent_handler})
        callback_manager.register_handler({TracerHandlerName.TRACER_WORKFLOW.value: trace_workflow_handler})

        self._callback_manager = callback_manager

    async def trigger(self, handler_class_name: str, event_name: str, **kwargs):
        await self._callback_manager.trigger(handler_class_name, event_name, **kwargs)

    def tracer_agent_span_manager(self):
        return self._tracer_agent_span_manager

    def tracer_workflow_span_manager(self):
        return self._tracer_workflow_span_manager
