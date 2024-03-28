import copy
from front.symboltable import is_const

class Operator :
    def __init__(self, type='empty'):
        self.next = []
        self.prev = []
        self.used = []
        self.type = type
        self.claim = []
    def add_next(self, next):
        self.next.append(next)
    def add_prev(self, prev):
        self.prev.append(prev)
    def add_used(self, used: str):
        self.used.append(used)
    def add_claim(self, claim: str):
        self.claim.append(claim)
    def dump(self):
        print("{} object at 0x{:x}".format(self.__module__, id(self)))
        print(f"type={self.type}\nnext={self.next}\nprev={self.prev}\nused={self.used}\nclaim={self.claim}\n")
    def equal(self, op) -> bool:
        if self.type != op.type:
            return False
        return self.equal_inner(op)
    def equal_inner(self, op) -> bool:
        return self.type == op.type
    def get_self_id(self) -> str:
        return "{:x}".format(id(self))[-4:]
    def dump_graph(self) -> str:
        pre_description = ""
        if len(self.used) > 0:
            pre_description += "<br> used = {}".format(self.used)
        if len(self.claim) > 0:
            pre_description += "<br> claim = {}".format(self.claim)
        if hasattr(self, "is_pre_stateless"):
            pre_description += "<br>pre_stateless"
        if hasattr(self, "filter_branch"):
            pre_description += "<br>filter_branch = {}".format(self.filter_branch)
        if hasattr(self, "var_stream_down_top") and len(self.var_can_be_used) > 0:
            pre_description += "<br>var_can_be_used = {}".format(self.var_can_be_used)
        if hasattr(self, "var_stream_top_down") and len(self.var_need_transmit) > 0:
            pre_description += "<br>var_transmit = {}".format(self.var_need_transmit).replace("set()", "{{empty_set}}")
        self_id = "{:x}".format(id(self))[-4:]
        return "  {}({}_0x{}{})\n".format(id(self), self.type, self_id, pre_description)
        

class OpFilter(Operator):
    def __init__(self, left_value, op: str, right_value):
        super().__init__()
        self.type = 'filter'
        self.left_value = left_value
        self.op = op
        self.right_value = right_value
        if is_const(left_value) == False:
            self.add_used(left_value)
        if is_const(right_value) == False:
            self.add_used(right_value)
    def equal_inner(self, op) -> bool:
        # print("{}{}{}".format(self.left_value == op.left_value, self.op == op.op, self.right_value == op.right_value))
        if self.left_value == op.left_value and self.op == op.op and self.right_value == op.right_value:
            return True
        return False
    def dump_graph(self) -> str:
        return super().dump_graph()[:-2] + "<br>left_value = {}<br>op = {}<br>right_value = {})\n".format(self.left_value, self.op, self.right_value)
    

class OpMap(Operator):
    def __init__(self, map_keys: list, new_import: dict):
        super().__init__()
        self.type = 'map'
        self.map_keys = map_keys
        self.new_import = new_import
        for key in map_keys:
            if new_import.get(key) == None:
                self.add_used(key)
        for (key, value) in new_import.items():
            self.add_claim(key)
            if isinstance(value, dict):
                for inner_val in value.get("values"):
                    self.add_used(inner_val)
    def equal_inner(self, op) -> bool:
        self.map_keys.sort()
        op.map_keys.sort()
        if self.map_keys == op.map_keys and self.new_import == op.new_import:
            return True
        return False
    def dump_graph(self) -> str:
        return super().dump_graph()[:-2] + "<br>map_keys = {}<br>new_import = {})\n".format(self.map_keys, self.new_import)

class OpDistinct(Operator):
    def __init__(self, distinct_keys: list):
        super().__init__()
        self.type = "distinct"
        self.distinct_keys = distinct_keys
        for key in distinct_keys:
            self.add_used(key)
    def equal_inner(self, op) -> bool:
        self.distinct_keys.sort()
        op.distinct_keys.sort()
        if self.distinct_keys == op.distinct_keys:
            return True
        return False
    def dump_graph(self) -> str:
        return super().dump_graph()[:-2] + "<br>distinct_keys = {})\n".format(self.distinct_keys)

class OpReduce(Operator):
    def __init__(self, reduce_keys: list, result: str):
        super().__init__()
        self.type = "reduce"
        self.reduce_keys = reduce_keys
        self.result = result
        for key in reduce_keys:
            self.add_used(key)
        self.add_claim(result)
    def equal_inner(self, op) -> bool:
        self.reduce_keys.sort()
        op.reduce_keys.sort()
        if self.result == op.result and self.reduce_keys == op.reduce_keys:
            return True
        return False
    def dump_graph(self) -> str:
        return super().dump_graph()[:-2] + "<br>reduce_keys = {}<br>result = {})\n".format(self.reduce_keys, self.result)
            
class OpZip(Operator):
    def __init__(self, left_key: str, right_key: str):
        super().__init__()
        self.type = "zip"
        self.zip_left_key = left_key
        self.zip_right_key = right_key
        self.add_used(left_key)
        self.add_used(right_key)
    def equal_inner(self, op) -> bool:
        if self.zip_left_key == op.zip_left_key and self.zip_right_key == op.zip_right_key:
            return True
        return False
    def dump_graph(self) -> str:
        return super().dump_graph()[:-2] + "<br>zip_left_key = {}<br>zip_right_key = {})\n".format(self.zip_left_key, self.zip_right_key)

class OpGroupBy(Operator): # TODO
    def __init__(self, func_name: str, index:list, args: list, registers: list, out: list):
        super().__init__()
        self.type = "groupby"
        self.func_name = func_name
        self.index = index
        self.args = args
        self.registers = registers
        self.out = out
        for arg in args:
            self.add_used(arg)
        for item in out:
            self.add_claim(item)
    def equal_inner(self, op) -> bool:
        return False
    def dump_graph(self) -> str:
        return super().dump_graph()[:-2] + "<br>func_name = {}<br>index = {}<br>args = {}<br>registers = {}<br>out = {})\n".format(self.func_name, self.index, self.args, self.registers, self.out)

class OperatorFactory:
    def __init__(self, merge=False): # merge 定义是否允许相同的算子合并
        self.ops = []
        self.merge = merge
        self.present_packetstream = None
    def add(self, prev: Operator, new_op: Operator):
        if self.merge == True and prev != None: # 需要判断是否可合并
            for op in prev.next :
                if op.equal(new_op):
                    return op
        if prev != None:
            prev.add_next(new_op)
            new_op.add_prev(prev)
        self.ops.append(new_op)
        if self.present_packetstream != None:
            new_op.packetstream = self.present_packetstream
        return new_op
    def filter(self, prev, left_value, op, right_value) -> Operator:
        return self.add(prev, OpFilter(left_value, op, right_value))
    def map(self, prev, map_keys, new_imports) -> Operator:
        return self.add(prev, OpMap(map_keys, new_imports))
    def distinct(self, prev, distinct_keys) -> Operator:
        return self.add(prev, OpDistinct(distinct_keys))
    def reduce(self, prev, reduce_keys, result) -> Operator:
        return self.add(prev, OpReduce(reduce_keys, result))
    def zip(self, prev, left_key, right_key) -> Operator:
        return self.add(prev, OpZip(left_key, right_key))
    def groupby(self, prev, func_name, index, args, registers, out) -> Operator:
        return self.add(prev, OpGroupBy(func_name, index, args, registers, out))
    def start(self) -> Operator:
        return self.add(None, Operator("start"))
    def empty(self, prev) -> Operator:
        return self.add(prev, Operator())
    def tmp(self, name: str) -> Operator: # 创建临时用的 operator
        op = Operator(name)
        if self.present_packetstream != None:
            op.packetstream = self.present_packetstream
        return op
    def dump(self):
        print("dump from facory 0x{:x}".format(id(self)))
        for op in self.ops:
            op.dump()
    def dump_graph(self, filename=None, write_policy="w", first_line="graph TD\n"):
        tmp = first_line
        for op in self.ops:
            tmp += op.dump_graph()
        for op in self.ops:
            for next in op.next:
                tmp += "  {} --> {}\n".format(id(op), id(next))
        tmp = tmp.replace("[", "&#91 ")
        tmp = tmp.replace("{", "&#123 ")
        tmp = tmp.replace("]", " &#93")
        tmp = tmp.replace("}", " &#125")
        # print(tmp)
        if filename == None:
            print(tmp)
        else:
            f = open(filename, write_policy)
            f.write(tmp)
            f.close()
    def metacopy(self, op: Operator, prev: Operator) -> Operator:
        tmp = copy.deepcopy(op)
        tmp.next.clear()
        tmp.prev.clear()
        return self.add(prev, tmp)