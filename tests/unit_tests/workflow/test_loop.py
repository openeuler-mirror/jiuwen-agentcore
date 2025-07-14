#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from jiuwen.core.component.base import StartComponent, EndComponent
from jiuwen.core.component.condition.array import ArrayCondition
from jiuwen.core.component.loop_callback.intermediate_loop_var import IntermediateLoopVarCallback
from jiuwen.core.component.loop_callback.output import OutputCallback
from jiuwen.core.component.loop_comp import LoopGroup, LoopComponent
from jiuwen.core.component.set_variable_comp import SetVariableComponent
from jiuwen.core.context.context import Context
from jiuwen.core.workflow.base import Workflow
from tests.unit_tests.workflow.test_node import CommonNode, AddTenNode


def test_loop_array_condition():
    context = Context()

    flow = Workflow()
    s = StartComponent()
    e = EndComponent()
    flow.set_start_comp("s", s)
    flow.set_end_component("e", e, inputs_schema={"array_result": "${b.array_result}", "user_var": "${b.user_var}"})
    flow.add_workflow_comp("a", CommonNode("a"), inputs_schema={"array": "${user.inputs.input_array}"})
    flow.add_workflow_comp("b", CommonNode("b"),
                           inputs_schema={"array_result": "${l.results}", "user_var": "${l.user_var}"})

    loop_group = LoopGroup(context)
    node1 = AddTenNode("1")
    loop_group.add_component("1", node1, inputs={"source": "${l.arrLoopVar.item}"})
    node2 = AddTenNode("2")
    loop_group.add_component("2", node2, inputs={"source": "${l.intermediateLoopVar.user_var}"})
    node3 = SetVariableComponent(context, {"${l.intermediateLoopVar.user_var}": "${2.result}"})
    loop_group.add_component("3", node3)
    loop_group.start_nodes(["1"])
    loop_group.end_nodes(["3"])
    loop_group.add_connection("1", "2")
    loop_group.add_connection("2", "3")

    loop_condition = ArrayCondition(context, "l", {"item": "${a.loop_array}"})
    output_callback = OutputCallback(context, "l",
                                     {"results": "${1.result}", "user_var": "${l.intermediateLoopVar.user_var}"})
    intermediate_callback = IntermediateLoopVarCallback(context, "l",
                                                        {"user_var": "${user.inputs.input_number}"})

    loop = LoopComponent(context, "l", loop_group, loop_condition,
                         callbacks=[output_callback, intermediate_callback])
    flow.add_workflow_comp("l", loop)

    flow.add_connection("s", "a")
    flow.add_connection("a", "l")
    flow.add_connection("l", "b")
    flow.add_connection("b", "e")

    result = flow.invoke({"input_array": [1, 2, 3], "input_number": 1}, context=context)
    assert result == {"array_result": [11, 12, 13], "user_var": 31}

    result = flow.invoke({"input_array": [4, 5], "input_number": 2}, context=context)
    assert result == {"array_result": [14, 15], "user_var": 22}
