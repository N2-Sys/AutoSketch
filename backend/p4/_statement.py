from ir import resona
from typing import List

def get_subtaskid_bitmap(subtask_list: List) -> int:
    mask = 0
    for id in subtask_list:
        mask = mask | (1 << id)
    return mask

def get_statement(statement : resona.StatementBase) -> str:
    def _get_id(id : str) -> str:
        if id.startswith("var_task_mask"):
            return "var_task_mask"
        else:
            return id
    _op_map = {"ge" : "{} - {} >= 0",
               "eq" : "{} == {}",
               "bit_and" : "({} & {}) != 0",
               "gt" : "{1} - {0} < 0",
               "lt" : "{} - {} < 0",
               "ne" : "{} != {}"
              }

    if isinstance(statement, resona.StatementCompare):
        if isinstance(statement.left_value, resona.StatefullBase):
            left = statement.left_value.get_id()
        else:
            left = "hdr." + statement.left_value
        if isinstance(statement.right_value, resona.StatefullBase):
            right = statement.right_value.get_id()
        else:
            right = "hdr." + statement.right_value
        return _op_map[statement.op].format(_get_id(left), right)
    else:
        assert False, f"get_statement() not support : {statement.dump()}"