import ast

from front.packetstream import PacketStream
from front.operators import OperatorFactory, Operator
from front.symboltable import is_default_header
from udf.tree_partition import pre_process as udf_pre_process
from udf.sketch_parser import s_parser as udf_parser
from udf.sketch_ast import FunDefAst as UDFFunDefAst

class Task:
    def __init__(self, merge=True) -> None:
        self.factory = OperatorFactory(merge = merge)
        self.global_dict = {}
        self.start = self.factory.start()
        self.packetstreams = []
        self.udfs = {}
        self.is_post_processing = False
        self.last_list = []
    def new_packet_stream(self, raw_codes):
        if self.is_post_processing == True:
            raise Exception("can't add new packet stream after post processing")
        # print("get a packet stream:\n{}\n\n".format(raw_codes))
        name = raw_codes[0][0:raw_codes[0].find("[")].strip()
        # print(name)
        requirements_str = raw_codes[0][raw_codes[0].find("[")+1:raw_codes[0].find("]")].strip()
        # print(requirements_str)
        req_list = []
        last_pos = 0
        for i in range(len(requirements_str)):
            if requirements_str[i] == ",":
                req_list.append(requirements_str[last_pos:i].strip())
                last_pos = i + 1
        if last_pos < len(requirements_str):
            req_list.append(requirements_str[last_pos:].strip())
        # print(req_list)
        requirements_str = "{"
        for req in req_list:
            split_pos = req.find("=")
            requirements_str += "\"{}\":{},".format(req[:split_pos].strip(), req[split_pos + 1:].strip())
        requirements_str += "}"
        requirements_dict = ast.literal_eval(requirements_str)
        # print(requirements_dict)
        # print(requirements_str)
        packetstream = PacketStream(self, name, requirements_dict)
        self.factory.present_packetstream = packetstream
        for raw in raw_codes[1:]:
            op_name = raw[raw.find(".") + 1:raw.find("(")]
            # 处理参数
            args = raw[raw.find("(")+1:raw.rfind(")")]
            # print(op_name, args)
            args_list = []
            last_pos = 0
            depth = 0
            for i in range(len(args)):
                if args[i] in {"(", "{", "["}:
                    depth += 1
                if args[i] in {")", "}", "]"}:
                    depth -= 1
                if args[i] == ',' and depth == 0:
                    args_list.append(args[last_pos:i].strip())
                    last_pos = i+1
            if last_pos < len(args):
                args_list.append(args[last_pos:].strip())
            # print(args_list)
            args_dict = "{"
            for arg in args_list:
                equal_pos = arg.find("=")
                args_dict += "\"" + arg[:equal_pos] + "\":" + arg[equal_pos+1:] + ","
            if args_dict[-1] == ",":
                args_dict = args_dict[:-1]
            args_dict += "}"
            # print(args_dict)
            args_dict = ast.literal_eval(args_dict)
            # print(args_dict)
            # 参数处理完成，接下来根据 operator 的名字调用对应的生成器
            if op_name == "filter":
                packetstream = packetstream.filter(left_value=args_dict["left_value"],
                                                  op=args_dict["op"],
                                                  right_value=args_dict["right_value"])
            elif op_name == "map":
                packetstream = packetstream.map(map_keys=args_dict["map_keys"],
                                                new_import=args_dict["new_import"])
            elif op_name == "distinct":
                packetstream = packetstream.distinct(distinct_keys=args_dict["distinct_keys"])
            elif op_name == "reduce":
                packetstream = packetstream.reduce(reduce_keys=args_dict["reduce_keys"],
                                                   result=args_dict["result"])
            elif op_name == "zip":
                packetstream = packetstream.zip(stream_name=args_dict["stream_name"],
                                                left_key=args_dict["left_key"],
                                                right_key=args_dict["right_key"])
            elif op_name == "groupby":
                packetstream = packetstream.groupby(func_name=args_dict["func_name"],
                                                    index=args_dict["index"],
                                                    args=args_dict["args"],
                                                    registers=args_dict["registers"],
                                                    out=args_dict["out"])
        self.last_list.append(packetstream.lastop)
        self.packetstreams.append(packetstream)
    def new_udf_definition(self, raw_codes):
        if self.is_post_processing == True:
            raise Exception("can't add new udf after post processing")
        # print("get a udf definition:\n{}\n\n".format(raw_codes))
        code, total_states = udf_pre_process(raw_codes)
        root = udf_parser.parse(code)
        isinstance(root, UDFFunDefAst)
        self.udfs[root.func_name] = {"code":code, "total_states":total_states, "root":root}
        # print(root.func_name)
        # root.show(0)
    
    def post_processing(self): # 开始分析依赖
        if self.is_post_processing == True:
            raise Exception("can't post processing multiple times")
        self.is_post_processing = True
        
        # 获取那些作为最后结果的 operator，用于识别每个任务（主要是处理 zip 带来的合并）
        tmp_list = []
        for last in self.last_list:
            if len(last.next) == 0 :
                tmp_list.append(last)
        self.last_list = tmp_list
        
        # 标记所有的前置无状态算子
        def dfs_find_pre_stateless_operator(op: Operator):
            if op.type == "filter" or op.type == "empty" or op.type == "start":
                op.is_pre_stateless = True
                for next in op.next:
                    dfs_find_pre_stateless_operator(next)
        dfs_find_pre_stateless_operator(self.start)
        
        start_ops = []
        # 标记分割所有的子任务
        def dfs_mark_divide(op: Operator, start_op_list: list):
            if hasattr(op, "is_pre_stateless") == True:
                return
            for prev in op.prev:
                dfs_mark_divide(prev, start_op_list)
            flag = True
            for prev in op.prev:
                if hasattr(prev, "is_pre_stateless") == False:
                    flag = False
            if flag == True:
                start_op_list.append(op)
        for last in self.last_list:
            tmp_list = []
            dfs_mark_divide(last, tmp_list)
            start_ops.append(tmp_list)
        self.start_ops = start_ops
        
        # 标记每个 operator 属于哪个判断分支
        # 和上面的子任务有不同，子任务划分是把必须分配到同一个交换机的任务挂载到同一个 start 下
        # 这里则是识别每一个 filter 分支
        filter_branch_cnt = 0
        def dfs_filter_branch(op):
            nonlocal filter_branch_cnt
            if hasattr(op, "is_pre_stateless") == False:
                if hasattr(op, "filter_branch") == False:
                    op.filter_branch = []
                op.filter_branch.append(filter_branch_cnt - 1)
            for nxt in op.next:
                if hasattr(op, "is_pre_stateless") != hasattr(nxt, "is_pre_stateless"):
                    filter_branch_cnt += 1
                dfs_filter_branch(nxt)
        dfs_filter_branch(self.start)
        
        # 分析变量使用
        def dfs_var_analysis_down_top(op: Operator):
            # 首先自下而上分析，计算到每个 operator 时，定义域内能够使用的变量
            if hasattr(op, "var_stream_down_top"):
                return set.union(op.var_can_be_used, set(op.claim))
            op.var_stream_down_top = True
            op.var_can_be_used = set()
            # for item in op.claim:
            #     op.var_can_be_used.add(item)
            for prev_op in op.prev:
                tmp = dfs_var_analysis_down_top(prev_op)
                op.var_can_be_used = set().union(op.var_can_be_used, tmp)
            return set.union(op.var_can_be_used, set(op.claim))
        for last in self.last_list:
            dfs_var_analysis_down_top(last)
        
        def dfs_var_analysis_top_down(op: Operator):
            # 然后自顶向下分析，计算每个 operator 需要向前索要哪些计算结果
            if hasattr(op, "var_stream_top_down"):
                return op.var_need_transmit
            op.var_stream_top_down = True
            op.var_need_transmit = set()
            for next_op in op.next:
                tmp = dfs_var_analysis_top_down(next_op)
                op.var_need_transmit = set.union(op.var_need_transmit, tmp)
            for item in op.claim:
                op.var_need_transmit.discard(item)
            for item in op.used:
                if is_default_header(item) == False:
                    op.var_need_transmit.add(item)
            op.var_need_transmit = set.intersection(op.var_need_transmit, op.var_can_be_used)
            return op.var_need_transmit
        dfs_var_analysis_top_down(self.start)
    