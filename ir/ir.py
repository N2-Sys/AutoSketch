import copy

from front.operators import Operator, OperatorFactory
from front.task import Task
from ir.resona import Resona

class CompUnit:
    def __init__(self, subtaskid: int, entry: list, full_map, udf_dict: dict):
        self.subtaskid = subtaskid
        self.factory = OperatorFactory(False)
        self.start = self.factory.add(None, self.factory.tmp("start{}".format(subtaskid)))
        
        # 递归地将涉及到的算子复制过来，注意不重不漏
        def copy_iter(original_node: Operator, new_node: Operator):
            full_map[original_node] = new_node
            for next_op in original_node.next:
                if full_map.get(next_op) == None:
                    tmp = self.factory.metacopy(next_op, new_node)
                    copy_iter(next_op, tmp)
                else:
                    tmp = full_map[next_op]
                    new_node.add_next(tmp)
                    tmp.add_prev(new_node)
        for item in entry:
            if full_map.get(item):
                tmp = full_map[item]
                self.start.add_next(tmp)
                tmp.add_prev(self.start)
            else:
                tmp = self.factory.metacopy(item, self.start)
                copy_iter(item, tmp)
        # 开始生成二次中间表示
        self.resona = Resona(self.start, udf_dict)
        # self.resona.dump()

class TransmitTable:
    def __init__(self, up_table=None) -> None:
        self.table = {}
        self.compunit = []
        self.up_table = up_table
    def walk(self, key_name, op, value):
        if self.table.get((key_name, op)) == None:
            self.table[(key_name, op)] = {}
        if self.table[(key_name, op)].get(value) == None:
            self.table[(key_name, op)][value] = TransmitTable(self)
        return self.table[(key_name, op)][value]
    def add_code(self, code: CompUnit):
        self.compunit.append(code)
    def dump(self) -> str:
        tmp = ""
        self_id = "{:x}".format(id(self))[-4:]
        tmp += "  {}[(table_0x{})]\n".format(id(self), self_id)
        for (iter, table) in self.table.items():
            (key_name, op) = iter
            # print(key_name, op)
            tmp += "  {}((key_name = {}<br>op= {}))\n".format(id(table), key_name, op)
            tmp += "  {} --- {}\n".format(id(self), id(table))
            for (value, sub_table) in table.items():
                tmp += "  {} -->|{}| {}\n".format(id(table), value, id(sub_table))
        unit_dump = {}
        for unit in self.compunit:
            if unit not in unit_dump:
                ret = unit.resona.dump()
                ret = ret.replace(" ", "&nbsp ")
                ret = ret.replace("[", "&#91 ")
                ret = ret.replace("{", "&#123 ")
                ret = ret.replace("]", " &#93")
                ret = ret.replace("}", " &#125")
                ret = ret.replace("(", "&#40 ")
                ret = ret.replace(")", " &#41")
                ret = ret.replace("\n", "<br>")
                unit_dump[unit] = ret
                tmp += "  {}(<p align=\"left\">{}</p>)\n".format(id(unit), ret)
            tmp += "  {} --> {}\n".format(id(self), id(unit))
            # tmp += "  {} ..- {}\n".format(id(self), id(op))
        for (_, table) in self.table.items():
            for (_, sub_table) in table.items():
                tmp += sub_table.dump()
        return tmp

class IRFactory:
    def __init__(self, task: Task) -> None:
        if task.is_post_processing == False:
            raise Exception("Please do post processing on task before convert it to IR")
        compunits = []
        full_map = {}
        tmp_set = set()
        op_2_unit = {}
        for start_op in task.start_ops:
            tmp_tuple = tuple(start_op)
            if tmp_tuple in tmp_set:
                continue
            tmp_set.add(tmp_tuple)
            unit = CompUnit(len(tmp_set) - 1, start_op, full_map, task.udfs)
            compunits.append(unit)
            for op in start_op:
                op_2_unit[op] = unit

        self.compuints = compunits
        
        table = TransmitTable()
        def init_transmit_table_iter(op: Operator, table: TransmitTable) :
            for next in op.next:
                if hasattr(next, "is_pre_stateless") == True:
                    if next.type == "filter":
                        init_transmit_table_iter(next, table.walk(next.left_value, next.op, next.right_value))
                    else:
                        init_transmit_table_iter(next, table)
                else:
                    table.add_code(op_2_unit[next])
        init_transmit_table_iter(task.start, table)
        self.table = table
        
        
    def dump_table(self, filename=None, write_policy="w", first_line="graph TD\n") -> str:
        output = self.table.dump()
        if filename == None:
            print(output)
        else:
            f = open(filename, write_policy)
            f.write(first_line + output)
            f.close()
        return output