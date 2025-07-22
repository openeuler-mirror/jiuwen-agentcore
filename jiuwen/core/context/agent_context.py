from jiuwen.core.context.context import Context
from jiuwen.core.context.state import State
from jiuwen.core.context.store import Store


class AgentContext:
    context_map: dict[str, Context] = {}
    store: Store = None
