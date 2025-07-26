# 使用Open JiuWen搭建一个ReAct Agent：天气查询助手

> 运行环境：Python ≥ 3.11，仅需 `pip install jiuwen`。

---

## 1. 背景：ReAct Agent

| 概念                 | 定义                    | 适用场景                 |
|--------------------|-----------------------|----------------------|
| **Workflow Agent** | LLM 与工具按**预定义代码路径**编排 | 任务可拆成固定步骤，追求稳定 & 低延迟 |
| **ReAct Agent**    | LLM **动态决定**下一步骤与工具   | 步骤数量不可预期，需长期自主决策     |

本教程实现一个**ReAct Agent**，依赖大模型动态决定下一步骤。
![](../resource/react_agent.png)
---

## 2. 安装依赖

```bash
pip install jiuwen
```

---

## 3. 创建一个天气查询插件

```python
from jiuwen.core.utils.tool.service_api.restful_api import RestfulApi
from jiuwen.core.utils.tool.service_api.param import Param

def _create_tool():
    weather_plugin = RestfulApi(
        name="WeatherReporter",
        description="天气查询插件",
        params=[
            Param(name="location", description="天气查询的地点，必须为英文", type="string", required=True),
            Param(name="date", description="天气查询的时间，格式为YYYY-MM-DD", type="string", required=True),
        ],
        path="http://127.0.0.1:9000/weather",  # 天气查询服务部署在本地，端口9000
        headers={},
        method="GET",
        response=[],
    )
    return weather_plugin

def _create_tool_schema():
    tool_info = PluginSchema(
        name='WeatherReporter',
        description='天气查询插件',
        inputs={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "天气查询的地点。\n注意：地点名称必须为英文",
                    "required": True
                },
                "date": {
                    "type": "string",
                    "description": "天气查询的时间，格式为YYYY-MM-DD",
                    "required": True
                }
            }
        }
    )
    return tool_info
```

## 4. 定义大模型配置

```python
import os
from jiuwen.core.utils.llm.base import BaseModelInfo
from jiuwen.core.component.common.configs.model_config import ModelConfig

API_BASE = os.getenv("API_BASE", "")
API_KEY = os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")


def _create_model_config() -> ModelConfig:
    return ModelConfig(
        model_provider=MODEL_PROVIDER,
        model_info=BaseModelInfo(
            model=MODEL_NAME,
            api_base=API_BASE,
            api_key=API_KEY,
            temperature=0.7,
            top_p=0.9,
            timeout=30,
        ),
    )
```

---

## 5. 自定义天气查询助手的提示词

```python
def _create_prompt_template():
    system_prompt = "你是一个AI助手，在适当的时候调用合适的工具，帮助我完成任务！今天的日期为：{}\n注意：1. 如果用户请求中未指定具体时间，则默认为今天。"
    return [
        dict(role="system", content=system_prompt.format(build_current_date()))
    ]
```

## 6. 创建ReActAgentConfig对象

天气查询助手依赖的插件、大模型和提示词。Open JiuWen提供了方法`create_react_agent_config`，能够快速创建ReActAgentConfig对象。

代码：

```python
from jiuwen.agent.react_agent import create_react_agent_config

react_agent_config = create_react_agent_config(
            agent_id="react_agent_123",
            agent_version="0.0.1",
            description="AI助手",
            plugins=[_create_tool_schema()],  # 天气查询插件的元数据信息
            workflows=[],
            model=_create_model_config(),    # 大模型的配置信息
            prompt_template=_create_prompt_template()  # 自定义提示词
        )
```

`create_react_agent_config`实际上调用了ReActAgentConfig的初始化方法：
```python
from typing import Dict, List
from jiuwen.agent.config.react_config import ReActAgentConfig
from jiuwen.agent.common.schema import WorkflowSchema, PluginSchema
from jiuwen.core.component.common.configs.model_config import ModelConfig

def create_react_agent_config(agent_id: str,
                              agent_version: str,
                              description: str,
                              workflows: List[WorkflowSchema],
                              plugins: List[PluginSchema],
                              model: ModelConfig,
                              prompt_template: List[Dict]):
    config = ReActAgentConfig(id=agent_id,
                              version=agent_version,
                              description=description,
                              workflows=workflows,
                              plugins=plugins,
                              model=model,
                              prompt_template=prompt_template)
    return config
```
---

## 7. 创建ReAct Agent对象

Open JiuWen提供了方法`create_react_agent`，能够快速创建ReAct Agent对象。

```python
from jiuwen.agent.react_agent import create_react_agent

react_agent = create_react_agent(
            agent_config=react_agent_config,  # 天气查询助手配置：第6步中创建的ReActAgentConfig对象
            workflows=[],
            tools=[_create_tool()]  # 天气查询助手关联：第3步中创建的插件对象
        )
```

`create_react_agent`实际上调用了ReActAgent的初始化方法：
```python
from typing import List
from jiuwen.agent.config.react_config import ReActAgentConfig
from jiuwen.agent.react_agent import ReActAgent
from jiuwen.core.utils.tool.base import Tool
from jiuwen.core.workflow.base import Workflow

def create_react_agent(agent_config: ReActAgentConfig,
                       workflows: List[Workflow] = None,
                       tools: List[Tool] = None):
    agent = ReActAgent(agent_config)
    agent.bind_workflows(workflows)
    agent.bind_tools(tools)
    return agent
```
---

## 8. 运行ReActAgent

基于第7步创建的ReActAgent对象，调用invoke方法，获取天气查询助手的返回结果。

```python
result = await react_agent.invoke({"query": "查询杭州的天气"})
```

执行天气查询助手成功后，会得到如下的结果：
```text
{'output': '\n\n当前杭州的天气情况如下：\n- 天气现象：小雨\n- 实时温度：30.78℃\n- 体感温度：37.78℃\n- 空气湿度：74%\n- 风速：0.77米/秒（约2.8公里/小时）\n\n建议外出时携带雨具，注意防雨防滑。需要其他天气信息可以随时告诉我哦~'}
```

ReActAgent的invoke方法实现了ReAct规划流程，代码如下：
```python
class ReActAgent(Agent):
    async def invoke(self, inputs: Dict) -> Dict:
        task: Task = self._task_manager.create_task(inputs.get("conversation_id"))
        context = task.context
        context.set_controller_context_manager(self._controller_context_manager)
        self._load_state_from_context(context)
        controller_output = ReActControllerOutput()
        while self._state.current_iteration < self._config.constrain.max_iteration:
            # 调用大模型生成每次规划的结果
            controller_output = self._controller.invoke(ReActControllerInput(**inputs), context)
            self._state.handle_llm_response_event(controller_output.llm_output, controller_output.sub_tasks)
            self._store_state_to_context(context)
            if controller_output.should_continue:
                # 如果生成了工具调用命令，就执行工具
                completed_sub_tasks = await self._execute_sub_tasks(context)
            else:
                # 否则就退出迭代流程
                break
            self._state.handle_tool_invoked_event(completed_sub_tasks)
            self._state.increment_iteration()
            self._store_state_to_context(context)

        self._state.handle_react_completed_event(controller_output.llm_output.content)
        self._store_state_to_context(context)
        return dict(output=self._state.final_result)
```

恭喜你，成功搭建了第一个ReAct Agent！
---
