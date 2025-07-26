# 使用Open JiuWen提示词自优化功能: 优化信息抽取类提示词

> 运行环境：Python ≥ 3.11

---
本教程基于一个信息（人名）抽取类提示词，通过给定真实用例，优化提示词并提执行高成功率。

## 1. 准备待优化提示词

```
你是一个信息抽取助手，请从给定句子中提取所有的人名名称
输出格式为[人名1, 人名2, ...]的列表形式，不要输出其他内容
以下是用户输入：
```

## 2. 准备场景用例

| 用户问题                | 期望回答                  | 模型回答                                                                            |
|---------------------|-----------------------|---------------------------------------------------------------------------------|
| 潘之恒（约1536—1621）字景升，号鸾啸生，冰华生，安徽歙县、岩寺人，侨寓金陵（今江苏南京）| [潘之恒] | [潘之恒, 景升, 啸生, 冰华生]                                                              |
| 高祖二十二子：窦皇后生建成（李建成）、太宗皇帝（李世民）、玄霸（李玄霸）、元吉（李元吉），万贵妃生智云（李智云），莫嫔生元景（李元景），孙嫔生元昌（李元昌）    | [李建成, 李世民, 李玄霸, 李元吉, 李智云, 李元景, 李元昌]   | [窦皇后, 李建成, 太宗皇帝, 李世民, 玄霸, 李玄霸, 元吉, 李元吉, 万贵妃, 智云, 李智云, 莫嫔, 元景, 李元景, 孙嫔, 元昌, 李元昌] |
| 郭造卿（1532—1593），字建初，号海岳，福建福清县化南里人（今福清市人），郭遇卿之弟，郭造卿少年的时候就很有名气，曾游学吴越| [郭造卿, 郭遇卿] | [郭造卿]                                                                           |
| 沈自邠，字茂仁，号几轩，又号茂秀，浙江秀水长溪（今嘉兴南汇）人| [沈自邠]| [沈自邠, 茂仁, 几轩, 茂秀]                                                                 |

**期望回答**: 用户期望模型的回答，为ground truth
**模型回答**: 模型基于当前提示词和问题的真实回答

## 3. 构造用例集
基于**用户问题**和**期望回答**，构造用例集
用例集构造需要遵从：
* case中的一条消息由`role`和`content`组成，表示消息的角色和内容。
* 消息类型可以为[`user`, `system`, `assistant`]中的一种，其中assistant表示模型的回答
* 一条case可以包含多条message，但要求最后一条角色为`assistant`，表示期望模型的期望输出，即ground truth。
```python
from jiuwen.agent_builder.prompt_builder.tune.base.case import Case
INFORMATION_EXTRACTION_CASES = [
    Case(messages=[
        {
            "role": "user",
            "content": "潘之恒（约1536—1621）字景升，号鸾啸生，冰华生，安徽歙县、岩寺人，侨寓金陵（今江苏南京）"
        },
        {
            "role": "assistant",
            "content": "[潘之恒]"
        }
    ]),
    Case(messages=[
        {
            "role": "user",
            "content": "高祖二十二子：窦皇后生建成（李建成）、太宗皇帝（李世民）、玄霸（李玄霸）、元吉（李元吉），万贵妃生智云（李智云），莫嫔生元景（李元景），孙嫔生元昌（李元昌）"
        },
        {
            "role": "assistant",
            "content": "[李建成, 李世民, 李玄霸, 李元吉, 李智云, 李元景, 李元昌]"
        }
    ]),
    Case(messages=[
        {
            "role": "user",
            "content": "郭造卿（1532—1593），字建初，号海岳，福建福清县化南里人（今福清市人），郭遇卿之弟，郭造卿少年的时候就很有名气，曾游学吴越"
        },
        {
            "role": "assistant",
            "content": "[郭造卿, 郭遇卿]"
        }
    ]),
    Case(messages=[
        {
            "role": "user",
            "content": "沈自邠，字茂仁，号几轩，又号茂秀，浙江秀水长溪（今嘉兴南汇）人"
        },
        {
            "role": "assistant",
            "content": "[沈自邠]"
        }
    ])
]
```
## 4. 创建提示词优化器
提示词优化器的创建无需参数，直接创建即可
```python
from jiuwen.agent_builder.prompt_builder.tune.joint_optimizer import JointOptimizer

optimizer = JointOptimizer()
```

## 5. 运行前准备
1. 设置任务基本信息
注: task_id为提示词自优化任务的唯一标识，不可重复
```python
from jiuwen.agent_builder.prompt_builder.tune.base.utils import TaskInfo
task_id = "JOINT_123456"
task_info = TaskInfo(
    task_id=task_id,
    task_name="information extraction task"
)
```
2. 设置优化器超参数
优化器超参包含：
* cases: 之前创建的用例集。
* num_iterations: 优化迭代轮次，轮次越多，更有可能优化出好的提示词，但优化时间也会相应增加。限制不超过20。
* num_parallel: 模型并发度，并发度越高，优化速度越快。使用时请考虑实际模型服务吞吐能力
* user_compare_rules: 用户自定义评价标准，如果用户针对结果好坏的评价有一套自己的标准或规则，可以通过这个参数设置
* 其他参数请参考接口文档
```python
from jiuwen.agent_builder.prompt_builder.tune.base.utils import OptimizeInfo
        optimize_info = OptimizeInfo(
            cases=INFORMATION_EXTRACTION_CASES,
            num_iterations=1,
            num_parallel=5,
            user_compare_rules=""
        )
```
3. 设置模型
可以设置两个模型的参数
* 算法优化模型: 优化、评估提示词效果的模型，推荐使用更好的模型
* 推理模型: 基于提示词和用户输入推理的模型，推荐和实际场景中的模型保持一致或近似
```python
from jiuwen.agent_builder.prompt_builder.tune.base.utils import LLMModelInfo
opt_model_info = LLMModelInfo(
    url="",
    model="",
    api_key="",
    model_source=""
)
# 初始化推理模型信息
infer_model_info = LLMModelInfo(
    url="",
    model="",
    api_key="",
    model_source=""
)
```
## 6. 启动自优化任务
启动任务，需要包含如下参数：
* task_info: 任务基本信息
* optimize_info: 优化器超参数
* raw_templates: 待优化提示词，注：为方便后续扩展，当前输入为列表
* opt_model_info: 算法优化模型
* infer_model_info: 推理模型
```python
optimizer.do_optimize(task_info=task_info,
                      optimize_info=optimize_info,
                      raw_templates=[INFORMATION_EXTRACTION_TEMPLATE],
                      opt_model_info=self.opt_model_info,
                      infer_model_info=self.infer_model_info)
```
启动优化任务后，只需等待一会，即可查看优化结果

## 7. 获取优化结果
`ContextManager`为优化任务进度/上下文管理单例，可以通过`get_task_progress`获取优化进度，实时查询
```python
from jiuwen.agent_builder.prompt_builder.tune.base.context_manager import ContextManager
progress = ContextManager().get_task_progress(task_id)
print("[优化后成功率]:", progress.best_accuracy)
print("[优化后提示词]:", progress.best_prompt)
```