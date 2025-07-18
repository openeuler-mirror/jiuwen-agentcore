import uuid

from jiuwen.core.tracer.handler import TraceAgentHandler, TraceWorkflowHandler, TracerHandlerName
from jiuwen.core.tracer.span import SpanManager


class Tracer:
    def __init__(self, tracer_id=None, parent_node_id=""):
        self._callback_manager = None
        self._trace_id = str(uuid.uuid4()) if tracer_id is None else tracer_id
        self.tracer_agent_span_manager = SpanManager(self._trace_id)
        self.tracer_workflow_span_manager = SpanManager(self._trace_id, parent_node_id=parent_node_id)
        self._parent_node_id = parent_node_id

    def init(self, stream_writer_manager, callback_manager):
        # 用于注册子workflow tracer handler，子workflow中使用新的tracer handler
        if self._parent_node_id != "":
            trace_workflow_handler = TraceWorkflowHandler(callback_manager, stream_writer_manager,
                                                          self.tracer_workflow_span_manager)
            callback_manager.register_handler(
                {TracerHandlerName.TRACER_WORKFLOW.value + "." + self._parent_node_id: trace_workflow_handler})
        else:
            trace_agent_handler = TraceAgentHandler(callback_manager, stream_writer_manager,
                                                    self.tracer_agent_span_manager)
            trace_workflow_handler = TraceWorkflowHandler(callback_manager, stream_writer_manager,
                                                          self.tracer_workflow_span_manager)
            callback_manager.register_handler({TracerHandlerName.TRACE_AGENT.value: trace_agent_handler})
            callback_manager.register_handler({TracerHandlerName.TRACER_WORKFLOW.value: trace_workflow_handler})

        self._callback_manager = callback_manager

    async def trigger(self, handler_class_name: str, event_name: str, **kwargs):
        handler_class_name += "." + self._parent_node_id if self._parent_node_id != "" else ""
        await self._callback_manager.trigger(handler_class_name, event_name, **kwargs)
