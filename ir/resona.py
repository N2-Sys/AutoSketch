from front.operators import Operator, OpMap, OpZip
from queue import SimpleQueue
from front.symboltable import get_width, is_const, get_const, is_default_header
from udf.sketch_ast import BaseAst

ID_NAME_CONFLICT_AVOID_MAGIC_NUMBER = 4
UDF_OP_TRANS_DICT = {"==":"eq", "<":"lt", ">":"gt", "!=":"ne", ">=":"ge", "<=":"le", "+":"add", "-":"minus"}

class StatefullBase:
    def __init__(self, type:str, name:str) -> None:
        self.name = name
        self.type = type
        self.unique_id = "{:x}".format(id(self))[-ID_NAME_CONFLICT_AVOID_MAGIC_NUMBER:]
    def get_id(self) -> str:
        return "{}_{}_{}".format(self.type, self.name, self.unique_id)

class Value(StatefullBase):
    def __init__(self, name:str, width:int) -> None:
        super().__init__("var", name)
        self.width = width
    def dump(self) -> str:
        return "var " + self.get_id() + ": w{}".format(self.width) + ";\n"

class ConstValue(StatefullBase):
    def __init__(self, name:str, width:int, value:int) -> None:
        super().__init__("const", name)
        self.width = width
        self.value = value
    def get_value(self) -> str:
        if isinstance(self.value, str) == True:
            return self.value
        if self.value >= 0:
            return "{}w{}".format(self.width, self.value)
        else:
            return "-{}w{}".format(self.width, -self.value)
    def dump(self) -> str:
        return "const " + self.get_id() + " = {}".format(self.get_value()) + ": w{}".format(self.width) + ";\n"
    def get_id(self) -> str:
        if self.name == "":
            return self.get_value()
        return super().get_id()

class ValueFactory:
    def __init__(self) -> None:
        self.value_list = []
        self.const_dict = {}
        # self.new_const("UNUSUAL_EGRESS_PORT", 32, "UNUSUAL_EGRESS_PORT")
    def new_value(self, name:str, width:int) -> Value:
        tmp = Value(name, width)
        self.value_list.append(tmp)
        return tmp
    def new_const(self, name:str, width:int, value:int) -> ConstValue:
        # print("new_const:", name)
        sig = tuple([name, width, value])
        if sig in self.const_dict:
            return self.const_dict[sig]
        self.const_dict[sig] = tmp = ConstValue(name, width, value)
        return tmp
    def find_value(self, name:str) -> Value:
        for value in self.value_list:
            if value.name == name:
                return value
        return None
    def dump(self) -> str:
        tmp = ""
        for value in self.value_list:
            tmp += value.dump()
        for (_, const) in self.const_dict.items():
            if const.name != "":
                tmp += const.dump()
        return tmp

class RegisterTable(StatefullBase):
    def __init__(self, name:str, value_width:int) -> None:
        super().__init__("table", name)
        self.value_width = value_width
        # self.table_size = table_size
    def dump(self) -> str:
        return "register " + self.get_id() + "(value_width = {});\n".format(self.value_width)

class RegisterTableFactory:
    def __init__(self) -> None:
        self.table_list = []
    def new_register_table(self, name:str, value_width:int) -> RegisterTable:
        tmp = RegisterTable(name, value_width)
        self.table_list.append(tmp)
        return tmp
    def dump(self) -> str:
        tmp = ""
        for table in self.table_list:
            tmp += table.dump()
        return tmp

class StatementBase:
    def __init__(self, type:str, original_op:Operator) -> None:
        self.type = type
        self.original_op = original_op
    def dump(self) -> str:
        return ";"

class StatementCompare(StatementBase):
    def __init__(self, left_value:StatefullBase, op, right_value:StatefullBase, original_op:Operator) -> None:
        super().__init__("cmp", original_op)
        self.left_value = left_value
        self.op = op
        self.right_value = right_value
    def dump(self) -> str:
        # print(self.left_value, self.op, self.right_value)
        lft = self.left_value
        if isinstance(lft, StatefullBase):
            lft = self.left_value.get_id()
        rft = self.right_value
        if isinstance(rft, StatefullBase):
            rft = self.right_value.get_id()
        return "({} {} {})".format(lft, self.op, rft)

class StatementIf(StatementBase):
    def __init__(self, condition:StatementCompare, original_op:Operator) -> None:
        super().__init__("if", original_op)
        self.condition = condition
        self.true_list = []
        self.false_list = []
    def dump(self) -> str:
        tmp = ""
        tmp += "if {} {{\n".format(self.condition.dump())
        # print(self.true_list)
        for stat in self.true_list:
            # print(stat)
            tmp += "  " + stat.dump().replace("\n", "\n  ")[:-2]
        if len(self.false_list) >= 1:
            tmp += "}\nelse {\n"
            for stat in self.false_list:
                tmp += "  " + stat.dump().replace("\n", "\n  ")[:-2]
        tmp += "}\n"
        return tmp

class StatementAssignment(StatementBase):
    def __init__(self, left_value: Value, right_value, original_op:Operator) -> None:
        super().__init__("assignment", original_op)
        self.left_value = left_value
        self.right_value = right_value
    def dump(self) -> str:
        if isinstance(self.right_value, StatefullBase) == False:
            return "{} = {};\n".format(self.left_value.get_id(), self.right_value)
        else:
            return "{} = {};\n".format(self.left_value.get_id(), self.right_value.get_id())

class StatementSimpleCalc(StatementBase):
    def __init__(self, result: Value, left_value, op:str, right_value, original_op:Operator):
        super().__init__("simplecalc", original_op)
        self.result = result
        self.op = op
        self.left_value = left_value
        self.right_value = right_value
    def dump(self) -> str:
        lstr = ""
        rstr = ""
        if isinstance(self.left_value, StatefullBase):
            lstr = self.left_value.get_id()
        else:
            lstr = self.left_value
        if isinstance(self.right_value, StatefullBase):
            rstr = self.right_value.get_id()
        else:
            rstr = self.right_value
        return "{} = {} {} {};\n".format(self.result.get_id(), lstr, self.op, rstr)

class StatementRegisterAssignment(StatementBase):
    def __init__(self, register_table: RegisterTable, index: Value, op:str, key:Value, original_op:Operator, return_value = None) -> None:
        super().__init__("register_assignment", original_op)
        self.register_table = register_table
        self.index = index
        self.op = op
        self.key = key
        self.return_value = return_value
    def dump(self) -> str:
        tmp = self.key
        if isinstance(tmp, StatefullBase):
            tmp = tmp.get_id()
        tmp = "{}[{}].calc(op = {}, key = {});\n".format(self.register_table.get_id(), self.index.get_id(), self.op, tmp)
        if self.return_value == None:
            return tmp
        return "{} = {}".format(self.return_value.get_id(), tmp)

class StatementRegisterGet(StatementBase):
    def __init__(self, register_table: RegisterTable, index: Value, output: Value, original_op:Operator) -> None:
        super().__init__("register_get", original_op)
        self.register_table = register_table
        self.index = index
        self.output = output
    def dump(self) -> str:
        return "{} = {}[{}];\n".format(self.output.get_id(), self.register_table.get_id(), self.index.get_id())
        
class StatementCalcIndex(StatementBase):
    def __init__(self, inputs: list, output: Value) -> None:
        super().__init__("calc_index", None)
        self.inputs = inputs
        self.output = output
    def dump(self) -> str:
        tmp = ""
        for input in self.inputs:
            if type(input) == str:
                tmp += "{}, ".format(input)
            else:
                tmp += "{}, ".format(input.get_id())
        return "{} = CALC_HASH_INDEX({});\n".format(self.output.get_id(), tmp)

class StatementGroupBy(StatementBase):
    def __init__(self, groupby_op, index: Value, registers:list, outputs: list) -> None:
        super().__init__("groupby")
        raise Exception("Don't use statement groupby")
        self.groupby_op = groupby_op
        self.index = index
        self.registers = registers
        self.outputs = outputs
    def dump(self) -> str:
        raise Exception("Don't use statement groupby")
        tmp = "("
        for output in self.outputs:
            tmp += "{}, ".format(output.get_id())
        tmp += ") = groupby(func = {}, index = {}, registers = (".format(self.groupby_op.func_name, self.index.get_id())
        for register in self.registers:
            tmp += "{}, ".format(register.get_id())
        tmp += "));\n"
        return tmp

class StatementSetEgressPort(StatementBase):
    def __init__(self, egress_port:Value, op:Operator) -> None:
        super().__init__("set_egress_port", op)
        self.egress_port = egress_port
    def dump(self) -> str:
        tmp = "set_egress_port({});\n".format(self.egress_port.get_id())
        return tmp

class StatementGroup(StatementBase):
    def __init__(self, op:Operator) -> None:
        super().__init__("group", op)
        self.statements = []
        self.index = None
        self.registers = []
        self.outs = []
    def dump(self) -> str:
        addon_str = ""
        if self.original_op.type == "groupby":
            addon_str = "//groupby: " + self.original_op.func_name + "; "
            if self.index != None:
                addon_str += "index = {}, ".format(self.index.get_id())
            if len(self.registers) >= 1:
                addon_str += "registers = ["
                for register in self.registers:
                    addon_str += register.name + ", "
                addon_str += "],"
            if len(self.outs) >= 1:
                addon_str += "out = ["
                for out in self.outs:
                    addon_str += out.name + ", "
                addon_str += "]"
            addon_str += "\n"
        tmp = ""
        for stmt in self.statements:
            tmp += stmt.dump()
        tmp = addon_str + "{\n  " + tmp.replace("\n", "\n  ")[:-2] + "}\n"
        return tmp

class Resona:
    def __init__(self, start: Operator, udf_dict: dict) -> None:
        self.value_factory = ValueFactory()
        self.table_factory = RegisterTableFactory()
        self.statements = []
        self.index_manager = {}
        self.filter_branch_all = 0
        self.udf_dict = udf_dict
        # 判断是否是 zip-diff 的特殊形式
        q = SimpleQueue()
        ops = []
        q.put(start)
        ops.append(start)
        zip_op = None
        map_diff_op = None
        while q.empty() == False:
            now_op = q.get()
            if hasattr(now_op, "filter_branch"):
                self.filter_branch_all = self.filter_branch_all | self.get_filter_branch_bitmap(now_op.filter_branch)
            if now_op.type == "zip":
                zip_op = now_op
            if zip_op != None and now_op.type == "map":
                for (name, value) in now_op.new_import.items():
                    if type(value) is dict:
                        if ("op" in value) and value["op"] == "diff":
                            map_diff_op = now_op
                            break
            for nxt in now_op.next:
                if (nxt in ops) == False:
                    q.put(nxt)
                    ops.append(nxt)
        # print(map_diff_op, zip_op)
        # print(ops)
        if map_diff_op != None and zip_op != None:
            self.zip_diff_convert(start, zip_op, map_diff_op)
            return
        # 若非该特殊形式，则正常翻译
        self.normal_convert(start)

    
    def get_value_class(self, var_map, str: str):
        if str in var_map:
            return var_map[str]
        if is_const(str) == True:
            var_map[str] = self.value_factory.new_const(str, get_width(str), get_const(str))
        else:
            var_map[str] = self.value_factory.new_value(str, 32)
        return var_map[str]
    def get_index(self, index_list:list, statements) -> Value:
        index_list.sort()
        index_list = tuple(index_list)
        if index_list in self.index_manager:
            return self.index_manager[index_list]
        #if len(index_list) == 1 and self.value_factory.find_value(index_list[0]) != None:
        #     return self.value_factory.find_value(index_list[0])
        self.index_manager[index_list] = tmp = self.value_factory.new_value("index", 32)
        _index_list = []
        for index in index_list:
            if self.value_factory.find_value(index) != None:
                _index_list.append(self.value_factory.find_value(index))
            else:
                _index_list.append(index)
        statements.append(StatementCalcIndex(_index_list, tmp))
        return self.index_manager[index_list]
    def set_index_manager(self, index_list:list, value: Value) -> None:
        index_list.sort()
        index_list = tuple(index_list)
        self.index_manager[index_list] = value
        
    def get_filter_branch_bitmap(self, filter_branch_list: list) -> int:
        mask = 0
        for id in filter_branch_list:
            mask = mask | (1 << id)
        return mask
    
    def dfs_next(self, op, task_mask, dfs_func, statements):
        for nxt in op.next:
            # print(op, nxt)
            if nxt.type == "zip":
                continue
            substatements = dfs_func(nxt)
            if op.type.find("start") != -1 or (hasattr(op, "filter_branch") and hasattr(nxt, "filter_branch") and op.filter_branch != nxt.filter_branch):
                s_if = StatementIf(StatementCompare(task_mask, "bit_and", self.value_factory.new_const("", 32, self.get_filter_branch_bitmap(nxt.filter_branch)), None), None)
                s_if.true_list = substatements
                statements.append(s_if)
            else:
                statements.extend(substatements)
    
    def dfs_normal_routine(self, op, var_map) -> tuple: #[list, list]:
        statements = []
        if op.type == "map":
            for (key, value) in op.new_import.items():
                if type(value) == int:
                    value_class = self.value_factory.new_const(key, 32, value)
                    var_map[key] = value_class
                else:
                    raise Exception("Invalid new value import type in map-operator.")
            return (statements, statements)
        elif op.type == "reduce":
            # print(op.reduce_keys)
            index = self.get_index(op.reduce_keys, statements)
            
            key_width = 0
            for key in op.reduce_keys:
                key_width += get_width(key)
            register = self.table_factory.new_register_table("reduce_table", 32)
            # register_map[op] = register
            statements.append(StatementRegisterAssignment(register, index, "add", var_map[op.result], op))
            
            var_result = self.value_factory.new_value(op.result, 32)
            var_map[op.result] = var_result
            statements.append(StatementRegisterGet(register, index, var_result, op))
            
            return (statements, statements)
        elif op.type == "filter":
            left = self.get_value_class(var_map, op.left_value)
            right = self.get_value_class(var_map, op.right_value)
            # 对于那些最后执行的 filter 和 distinct，简化为一个等于判断和端口改变
            if len(op.next) == 1 and (op.op == "ge" or op.op == "gt"):
                nxt = op.next[0]
                if nxt.type == "distinct" and len(nxt.next) == 0:
                    s_if = StatementIf(StatementCompare(left, "eq", right, op), op)
                    statements.append(s_if)
                    s_if.true_list.append(StatementSetEgressPort(self.get_value_class(var_map, "UNUSUAL_EGRESS_PORT"), op))
                    return (statements, s_if.true_list)
            s_if = StatementIf(StatementCompare(left, op.op, right, op), op)
            statements.append(s_if)
            return (statements, s_if.true_list)
        elif op.type == "distinct":
            if len(op.next) == 0: # 对于那些最后执行的 distinct，在上面的 filter 已经处理过了，直接跳过即可
                # statements.append(StatementRegisterAssignment(register, index, "assign", self.value_factory.new_const("", 1, 1), op))
                return (statements, statements)
            else:
                index = self.get_index(op.distinct_keys, statements)
                register = self.table_factory.new_register_table("distinct_table", 1)
                query_result = self.value_factory.new_value("distinct_query", 1)
                statements.append(StatementRegisterAssignment(register, index, "assign", self.value_factory.new_const("", 1, 1), op, query_result))
                # statements.append(StatementRegisterGet(register, index, query_result, op))
                s_if = StatementIf(StatementCompare(query_result, "eq", self.value_factory.new_const("", 1, 0), op), op)
                # s_if.true_list.append(StatementRegisterAssignment(register, index, "assign", self.value_factory.new_const("", 1, 1), op))
                statements.append(s_if)
                return (statements, s_if.true_list)
        elif op.type == "groupby":
            grp = StatementGroup(op)
            flag_stateless_groupby = False
            if len(op.registers) == 0:
                flag_stateless_groupby = True
            index = None
            if len(op.index) >= 1:
                index = self.get_index(op.index, statements)
                grp.index = index
            registers = {}
            for reg in op.registers:
                registers[reg] = self.table_factory.new_register_table(reg, 32)
                grp.registers.append(registers[reg])
            for out in op.out:
                tmp = self.get_value_class(var_map, out)
                grp.outs.append(tmp)

            def groupby_translate_dfs(udf_stmt: BaseAst, resona_stmt:list):
                def unwrap_value(udf_stmt: BaseAst, resona_list: list) -> Value:
                    if udf_stmt.ast_type == "Identifier":
                        if udf_stmt.identifier in registers:
                            ret = self.value_factory.new_value("tmp", 32)
                            resona_list.append(StatementRegisterGet(registers[udf_stmt.identifier], index, ret, op))
                        elif is_const(udf_stmt.identifier) :
                            ret = self.value_factory.new_const(udf_stmt.identifier, get_width(udf_stmt.identifier), get_const(udf_stmt.identifier))
                        elif is_default_header(udf_stmt.identifier):
                            return udf_stmt.identifier
                        else:
                            ret = self.get_value_class(var_map, udf_stmt.identifier)
                        return ret
                    elif udf_stmt.ast_type == "Number":
                        ret = self.value_factory.new_const("", 32, udf_stmt.number)
                        return ret
                    elif udf_stmt.ast_type == "BinaryExp":
                        tmp = self.value_factory.new_value("tmp", 32)
                        left = unwrap_value(udf_stmt.lhs, resona_list)
                        right = unwrap_value(udf_stmt.rhs, resona_list)
                        resona_list.append(StatementSimpleCalc(tmp, left, UDF_OP_TRANS_DICT[udf_stmt.op], right, op))
                        return tmp
                    elif udf_stmt.ast_type == "UnaryExp":
                        tmp = self.value_factory.new_value("tmp", 32)
                        right = unwrap_value(udf_stmt.opr, resona_list)
                        resona_list.append(StatementSimpleCalc(tmp, self.value_factory.new_const("", 32, 0), UDF_OP_TRANS_DICT[udf_stmt.op], right, op))
                        return tmp
                    else:
                        raise Exception("Unsupport udf ast type when unwrap value {}".format(udf_stmt.ast_type))
                
                if udf_stmt == None:
                    return
                    
                if udf_stmt.ast_type == "Assign":
                    rexp = udf_stmt.exp
                    if rexp.ast_type == "BinaryExp" and rexp.lhs.ast_type == "Identifier" and rexp.lhs.identifier == udf_stmt.identifier.identifier and udf_stmt.identifier.identifier in registers:
                        right = unwrap_value(rexp.rhs, resona_stmt)
                        resona_stmt.append(StatementRegisterAssignment(registers[udf_stmt.identifier.identifier], index, UDF_OP_TRANS_DICT[rexp.op], right, op))
                    else:
                        right = unwrap_value(rexp, resona_stmt)
                        if udf_stmt.identifier.identifier in registers:
                            resona_stmt.append(StatementRegisterAssignment(registers[udf_stmt.identifier.identifier], index, "assign", right, op))
                        else:
                            left_value = self.get_value_class(var_map, udf_stmt.identifier.identifier)
                            resona_stmt.append(StatementAssignment(left_value, right, op))
                elif udf_stmt.ast_type == "If":
                    condl = None
                    condr = None
                    cond = udf_stmt.cond
                    if cond.ast_type == "BinaryExp":
                        condl = unwrap_value(cond.lhs, resona_stmt)
                        condr = unwrap_value(cond.rhs, resona_stmt)
                    else:
                        raise Exception("Unsupport udf ast cond type {}".format(cond.ast_type))
                    s_if = StatementIf(StatementCompare(condl, UDF_OP_TRANS_DICT[cond.op], condr, op), op)
                    resona_stmt.append(s_if)
                    groupby_translate_dfs(udf_stmt.then, s_if.true_list)
                    groupby_translate_dfs(udf_stmt.else_then, s_if.false_list)
                    # print(s_if.true_list)
                    # print(s_if.false_list)
                elif udf_stmt.ast_type == "Block":
                    for item in udf_stmt.items:
                        groupby_translate_dfs(item, resona_stmt)
                else:
                    raise Exception("Unsupport udf ast {}".format(udf_stmt.ast_type))
            
            # print(op.func_name)
            # print(self.udf_dict[op.func_name])
            # self.udf_dict[op.func_name]["root"].show(0)
            func_ast = self.udf_dict[op.func_name]["root"].body
            # print(func_ast)
            tmp_list = grp.statements
            if flag_stateless_groupby:
                tmp_list = []
            groupby_translate_dfs(func_ast, tmp_list)

            for out in op.out:
                if out in registers:
                    tmp_list.append(StatementRegisterGet(registers[out], index, var_map[out], op))

            if flag_stateless_groupby:
                statements.extend(tmp_list)
            else:
                statements.append(grp)
            # statements.append(StatementGroupBy(op, index, registers, outputs))
            return (statements, statements)
        elif op.type.find("start") != -1 or op.type.find("empty") != -1:
            return (statements, statements)
        else:
            print(op.dump())
            raise Exception("Unsupported operators")
    
    def zip_diff_convert(self, start, zip_op: OpZip, map_diff_op: OpMap):
        add_key = None
        dec_key = None
        for (key, value) in map_diff_op.new_import.items():
            if type(value) == dict and value["op"] == "diff":
                add_key = value["values"][0]
                dec_key = value["values"][1]
        zip_left_key = zip_op.zip_left_key
        zip_right_key = zip_op.zip_right_key
        var_map = {}
        task_mask = self.value_factory.new_value("task_mask", 32)
        merge_value = self.value_factory.new_value("merge_value", 32)
        merge_index_origin = self.value_factory.new_value("merge_index_origin", get_width(zip_left_key))
        merge_index = self.value_factory.new_value("merge_index", 32)
        
        # 处理 zip 前的部分
        def dfs_before_zip(op) -> list:
            if op == zip_op:
                return list()
            normal_flag = True
            statements = []
            next_statements = statements
            if op.type == "map":
                normal_flag = False
                for (key, value) in op.new_import.items():
                    if key == add_key or key == dec_key:
                        if type(value) == int:
                            if key == add_key:
                                statements.append(StatementAssignment(merge_value, self.value_factory.new_const("", 32, value), op))
                            elif key == dec_key:
                                statements.append(StatementAssignment(merge_value, self.value_factory.new_const("", 32, -value), op))
                        else:
                            raise Exception("Invali type of new import item in OpMap!")
                    else:
                        if type(value) == int:
                            value_class = self.value_factory.new_const(key, get_width(key), value)
                            var_map[key] = value_class
                        else:
                            raise Exception("Invalid new value import type in map-operator.")
            elif op.type == "reduce" and len(op.reduce_keys) == 1:
                if (zip_left_key in op.reduce_keys) or (zip_right_key in op.reduce_keys):
                    normal_flag = False
                    statements.append(StatementAssignment(merge_index_origin, op.reduce_keys, op))
            if normal_flag == True:
                (statements, next_statements) = self.dfs_normal_routine(op, var_map)
            
            self.dfs_next(op, task_mask, dfs_before_zip, next_statements)
            return statements
        
        statements_before_zip = []
        self.dfs_next(start, task_mask, dfs_before_zip, statements_before_zip)
        # self.statements = statements_before_zip
        
        def dfs_after_zip(op) -> list:
            nonlocal var_map
            normal_flag = True
            statements = []
            next_statements = statements
            if op == map_diff_op:
                normal_flag = False
                statements.append(StatementCalcIndex((merge_index_origin,), merge_index))
                self.set_index_manager([zip_left_key], merge_index)
                self.set_index_manager([zip_right_key], merge_index)
                merge_register_table = self.table_factory.new_register_table("merge", 32)
                statements.append(StatementRegisterAssignment(merge_register_table, merge_index, "add", merge_value, op))
                merge_result = self.value_factory.new_value("merge_result", 32)
                statements.append(StatementRegisterGet(merge_register_table, merge_index, merge_result, op))
                for (key, value) in op.new_import.items():
                    if type(value) == dict and value["op"] == "diff":
                        var_map[key] = merge_result
            if normal_flag == True:
                (statements, next_statements) = self.dfs_normal_routine(op, var_map)
            
            self.dfs_next(op, task_mask, dfs_after_zip, next_statements)
            return statements
        
        statements_after_zip = []
        self.dfs_next(zip_op, task_mask, dfs_after_zip, statements_after_zip)
        
        s_if = StatementIf(StatementCompare(task_mask, "bit_and", self.value_factory.new_const("", 32, self.filter_branch_all), None), None)
        s_if.true_list.extend(statements_before_zip)
        s_if.true_list.extend(statements_after_zip)
        self.statements.append(s_if)
            
    def normal_convert(self, start):
        var_map = {}
        task_mask = self.value_factory.new_value("task_mask", 32)
        
        def dfs(op) -> list:
            (statements, next_statements) = self.dfs_normal_routine(op, var_map)
            self.dfs_next(op, task_mask, dfs, next_statements)
            # print(op, statements)
            return statements
            
        
        statements = dfs(start)

        # s_if = StatementIf(StatementCompare(task_mask, "bit_and", self.value_factory.new_const("", 32, self.filter_branch_all)))
        # s_if.true_list = statements
        self.statements = statements
    def dump(self, filename=None, write_policy="w"):
        tmp = ""
        tmp += "value_definition {\n  " + self.value_factory.dump().replace("\n", "\n  ")[:-2] + "}\n"
        tmp += "table_definition {\n  " + self.table_factory.dump().replace("\n", "\n  ")[:-2] + "}\n"
        tmp += "apply {\n"
        for statement in self.statements:
            tmp += "  " + statement.dump().replace("\n", "\n  ")[:-2]
        tmp += "}\n\n"
        # print(tmp)
        if filename == None:
            pass #print(tmp)
        else:
            f = open(filename, write_policy)
            f.write(tmp)
            f.close()
        return tmp