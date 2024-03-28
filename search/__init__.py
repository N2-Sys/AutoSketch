import argparse
import re
import os
import sys
import jinja2

from front.task import Task, PacketStream
from front.operators import Operator, OpReduce, OpDistinct, OpGroupBy
from ir.ir import IRFactory, CompUnit, TransmitTable
from ir.resona import (
    StatefullBase, Value, ConstValue, RegisterTable,
    StatementBase, StatementCompare, StatementIf, StatementAssignment,
    StatementRegisterAssignment, StatementRegisterGet, StatementCalcIndex,
    StatementSimpleCalc, StatementGroup, StatementSetEgressPort
)

_CPP_INTS = {
    w: 'bool' if w == 1 else f'int{w}_t' for w in [1, 8, 16, 32, 64]
}

_CPP_CMPS = {
    'bit_and': '&',
    'eq': '==',
    'le': '<=',
    'ge': '>=',
    'lt': '<',
    'gt': '>',
    'ne': '!='
}

_CPP_CALCS = {
    'add': '+',
    'minus': '-',
}

_CPP_FIELDS = {
    'ipv4.src_addr': ('pkt.key.src_ip', 32),
    'ipv4.dst_addr': ('pkt.key.dst_ip', 32),
    'ipv4.protocol': ('pkt.key.proto', 8),
    'tcp.sport': ('pkt.key.src_port', 16),
    'tcp.dport': ('pkt.key.dst_port', 16),
    'tcp.src_port': ('pkt.key.src_port', 16), # both are used in sample code (?)
    'tcp.dst_port': ('pkt.key.dst_port', 16),
    'tcp.timestamp': ('static_cast<int64_t>(pkt.pkt_ts * 1e9)', 64),
    'tcp.flags': ('pkt.tcp_flag', 8),
    'tcp.flag': ('pkt.tcp_flag', 8), # both are used in sample code (?)
    'tcp.seq': ('pkt.tcp_seq', 32),
    'tcp.ack': ('pkt.tcp_ack', 32),

    'TCP_FLAG_SYN_ACK': ('TCP_FLAG_SYN_ACK', 8),
}

def _addIndent(s: str) -> str:
    return ('  ' + s.replace('\n', '\n  '))[:-2]

def _getVal(v) -> str:
    if isinstance(v, Value):
        return v.get_id()
    elif isinstance(v, ConstValue):
        if v.name:
            return v.get_id()
        else:
            return v.value
    elif type(v) == str:
        if v in _CPP_FIELDS:
            return _CPP_FIELDS[v][0]
        else:
            print(f'Warning unknown value \'{v}\'')
            return v
    else:
        raise

# def _isResAssign(v: StatementRegisterAssignment):
#     if len(v.original_op.next) != 0:
#         return False
#     if isinstance(v.original_op, OpGroupBy):
#         v.original_op: OpGroupBy
#         resName, = v.original_op.out
#         if resName != v.register_table.name:
#             return False
#     return True

class SearchGen:
    def __init__(self, ir: IRFactory, task: Task):
        self._packetStream: PacketStream
        self._packetStream, = task.packetstreams
        self._appName = self._packetStream.name
        self._queryName = f'Query_{self._appName}'

        self._tranStmts = []
        curTrans: TransmitTable = ir.table
        while len(curTrans.table) != 0:
            ((keyName, op), ds), = curTrans.table.items()
            (val, nxt), = ds.items()
            self._tranStmts.append(f'if (!({_CPP_FIELDS[keyName][0]} {_CPP_CMPS[op]} {val})) return;')
            curTrans = nxt

        compUnit: CompUnit
        compUnit, = curTrans.compunit

        self._resKeyType = None
        self._idxTypes = dict()
        self._regOrig = dict()
        self._regIdx = dict()
        # self._resAssign = None

        def genStmt(v: StatementBase) -> str:
            if isinstance(v, StatementCompare):
                v: StatementCompare
                return f'{_getVal(v.left_value)} {_CPP_CMPS[v.op]} {_getVal(v.right_value)}'

            elif isinstance(v, StatementIf):
                v: StatementIf
                r = f'if ({genStmt(v.condition)})' + ' {\n'
                for s in v.true_list:
                    r += _addIndent(genStmt(s))
                if len(v.false_list) >= 1:
                    r += '} else {\n'
                    for s in v.false_list:
                        r += _addIndent(genStmt(s))
                r += '}\n'
                return r

            elif isinstance(v, StatementAssignment):
                v: StatementAssignment
                return f'{_getVal(v.left_value)} = {_getVal(v.right_value)};\n'

            elif isinstance(v, StatementRegisterAssignment):
                v: StatementRegisterAssignment
                if v.register_table not in self._regIdx:
                    self._regIdx[v.register_table] = v.index
                    self._regOrig[v.register_table] = v.original_op
                r = ''

                # if _isResAssign(v):
                #     assert self._resAssign is None
                #     self._resAssign = v
                #     r += f'resKeys_.insert({v.index.get_id()});\n'
                #     if isinstance(v.original_op, OpDistinct):
                #         return r
                if v.return_value:
                    r += f'{v.return_value.get_id()} = {v.register_table.get_id()}->get({v.index.get_id()});\n'
                r += f'{v.register_table.get_id()}->{v.op}({v.index.get_id()}, {_getVal(v.key)});\n'
                return r

            elif isinstance(v, StatementRegisterGet):
                v: StatementRegisterGet
                return f'{v.output.get_id()} = {v.register_table.get_id()}->get({v.index.get_id()});\n'

            elif isinstance(v, StatementCalcIndex):
                v: StatementCalcIndex
                if v.output.get_id() not in self._idxTypes:
                    ts = [_CPP_INTS[_CPP_FIELDS[x][1] if type(x) == str else x.width] for x in v.inputs]
                    if len(ts) == 1:
                        self._idxTypes[v.output] = ts[0]
                    elif len(ts) == 0:
                        self._idxTypes[v.output] = ['int padding;']
                    else:
                        self._idxTypes[v.output] = [f'{tx} v{i};' for i, tx in enumerate(ts)]
                rs = ', '.join(_getVal(x) for x in v.inputs)
                if len(v.inputs) != 1:
                    rs = '{' + rs + '}'
                return f'{v.output.get_id()} = {rs};\n'

            elif isinstance(v, StatementSimpleCalc):
                v: StatementSimpleCalc
                return f'{v.result.get_id()} = {_getVal(v.left_value)} {_CPP_CALCS[v.op]} {_getVal(v.right_value)};\n'

            elif isinstance(v, StatementGroup):
                v: StatementGroup
                r = '{\n'
                for x in v.statements:
                    r += _addIndent(genStmt(x))
                r += '}\n'
                return r

            elif isinstance(v, StatementSetEgressPort):
                v: StatementSetEgressPort
                resOp: OpDistinct = v.original_op.next[0]
                assert type(resOp) == OpDistinct and len(resOp.next) == 0
                kts = []
                ks = []
                # TODO: move this to frontend
                for k in resOp.distinct_keys:
                    kv = compUnit.resona.value_factory.find_value(k)
                    if kv is not None:
                        kts.append(_CPP_INTS[kv.width])
                        ks.append(_getVal(kv))
                    else:
                        kts.append(_CPP_INTS[_CPP_FIELDS[k][1]])
                        ks.append(_getVal(k))
                if len(ks) == 1:
                    self._resKeyType = kts[0]
                    return f'resKeys_.insert({ks[0]});\n'
                else:
                    self._resKeyType = [f'{tx} v{i};' for i, tx in enumerate(kts)]
                    return f'resKeys_.insert({{{", ".join(ks)}}});\n'

            else:
                print(v)
                raise ValueError

        self._stmts = ''
        for s in compUnit.resona.statements:
            self._stmts += genStmt(s)

        self._valDefs = []
        for v in compUnit.resona.value_factory.value_list:
            v: Value
            vType = f'Idx_{v.get_id()}' if v.name == 'index' else _CPP_INTS[v.width]
            if v.name == 'task_mask':
                self._valDefs.append(f'constexpr {vType} {v.get_id()} = ~({vType})0;')
            else:
                self._valDefs.append(f'{vType} {v.get_id()};')
        for v in compUnit.resona.value_factory.const_dict.values():
            v: ConstValue
            if v.name:
                self._valDefs.append(f'constexpr {_CPP_INTS[v.width]} {v.get_id()} = {v.value};')

        self._regs = []
        self._regDefs = []
        self._regCreateBaseline = []
        self._regCreate = []
        self._regReset = []
        self._regNum = 0
        for v in compUnit.resona.table_factory.table_list:
            v: RegisterTable
            origOp = self._regOrig[v]

            # if v is self._resAssign.register_table:
            #     if isinstance(origOp, OpDistinct):
            #         continue

            curNum = self._regNum
            self._regNum += 1
            idxType = f'Idx_{self._regIdx[v].get_id()}'
            valType = _CPP_INTS[v.value_width]

            self._regs.append(v)
            self._regDefs.append(
                f'std::unique_ptr<Register<{idxType}, {valType}>> {v.get_id()};'
            )
            self._regReset.append(f'{v.get_id()}->reset();')
            self._regCreateBaseline.append(f'p->{v.get_id()} = std::make_unique<BaselineRegister<{idxType}, {valType}>>();')

            d = f'c[{curNum}].d'
            w = f'c[{curNum}].w * (PAGE_SIZE * 8 / {v.value_width})'
            if isinstance(origOp, OpDistinct):
                assert v.value_width == 1
                self._regCreate.append(f'p->{v.get_id()} = std::make_unique<BloomFilter<{idxType}>>({d}, {w});')
            elif isinstance(origOp, OpReduce):
                self._regCreate.append(f'p->{v.get_id()} = std::make_unique<CountMin<{idxType}, {valType}>>({d}, {w});')
            elif isinstance(origOp, OpGroupBy):
                self._regCreate.append(f'p->{v.get_id()} = std::make_unique<GroupByCM<{idxType}, {valType}>>({d}, {w});')

        # self._resKeyType = 'ResKey' # f'Idx_{self._resAssign.index.get_id()}'
        self._baseQuery = f'QueryRecallPrecision<{self._regNum}, ResKey>'
        self._baseQueryInit = 'QueryRecallPrecision'
        self._collectWin = [
            'Result res = std::move(resKeys_);',
            'resKeys_.clear();'
        ]
        self._evalConfType = 'RecallPrecisionConf'
        self._evalConfInit = [
            '.precisionMin = 0.9,',
            '.recallMin = 0.9,',
            '.confidence = 0.85,'
        ]

        # if isinstance(self._resAssign.original_op, OpDistinct):
        #     self._resKeyType = f'Idx_{self._resAssign.index.get_id()}'
        #     self._baseQuery = f'QueryRecallPrecision<{self._regNum}, {self._resKeyType}>'
        #     self._baseQueryInit = 'QueryRecallPrecision'
        #     self._collectWin = [
        #         'Result res = std::move(resKeys_);',
        #         'resKeys_.clear();'
        #     ]
        #     self._evalConfType = 'RecallPrecisionConf'
        #     self._evalConfInit = [
        #         '.precisionMin = 0.9,',
        #         '.recallMin = 0.9,',
        #         '.confidence = 0.85,'
        #     ]
        # elif isinstance(self._resAssign.original_op, OpReduce):
        #     self._resKeyType = f'Idx_{self._resAssign.index.get_id()}'
        #     resValType = _CPP_INTS[self._resAssign.register_table.value_width]
        #     self._baseQuery = f'QueryARE<{self._regNum}, {self._resKeyType}, {resValType}>'
        #     self._baseQueryInit = 'QueryARE'
        #     self._collectWin = [
        #         f'Result res;',
        #         'for (const auto &key : resKeys_) {',
        #         f'  res[key] = {self._resAssign.register_table.get_id()}->get(key);',
        #         '}',
        #         'resKeys_.clear();'
        #     ]
        #     self._evalConfType = 'AREConf'
        #     self._evalConfInit = [
        #         '.areMax = 0.1,',
        #         '.precisionMin = 0.9,',
        #         '.recallMin = 0.9,',
        #         '.confidence = 0.85,'
        #     ]
        # elif isinstance(self._resAssign.original_op, OpGroupBy):
        #     self._resKeyType = f'Idx_{self._resAssign.index.get_id()}'
        #     resValType = _CPP_INTS[self._resAssign.register_table.value_width]
        #     self._baseQuery = f'QueryARE<{self._regNum}, {self._resKeyType}, {resValType}>'
        #     self._baseQueryInit = 'QueryARE'
        #     self._collectWin = [
        #         f'Result res;',
        #         'for (const auto &key : resKeys_) {',
        #         f'  res[key] = {self._resAssign.register_table.get_id()}->get(key);',
        #         '}',
        #         'resKeys_.clear();'
        #     ]
        #     self._evalConfType = 'AREConf'
        #     self._evalConfInit = [
        #         '.areMax = 0.1,',
        #         '.precisionMin = 0.9,',
        #         '.recallMin = 0.9,',
        #         '.confidence = 0.85,'
        #     ]
        # else:
        #     raise ValueError

        self._traceConfInit = [
            '.trace = std::make_shared<Trace>(readTrace("/data/OmniWindow-trace/trace.bin")),',
            '.nEpoch = 10,',
            '.interval = 0.5,'
        ]
        self._searchConfInit = [
            '.nThreads = 32,',
            '.aluMax = 8,',
            '.pageMax = 32,',
            '.maxStagePerOp = 1,',
            '.alpha = 0.4,',
            '.beta = 0.6,'
        ]

    def output(self, targetPath: str):
        curPath = os.path.dirname(__file__)
        includePath = os.path.join(curPath, 'include')
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(curPath))
        os.makedirs(targetPath, exist_ok=True)
        progName = f'autosketch-{self._appName.replace("_", "-")}'
        with open(os.path.join(targetPath, f'{progName}.cpp'), 'w') as fp:
            print(env.get_template('search.cpp.jinja').render(s=self), file=fp)
        with open(os.path.join(targetPath, f'conf.json'), 'w') as fp:
            print(env.get_template('conf.json.jinja').render(s=self, req=self._packetStream.requirement_dict), file=fp)
        with open(os.path.join(targetPath, f'Makefile'), 'w') as fp:
            print(env.get_template('Makefile.jinja').render(includePath=includePath, progName=progName), file=fp)
