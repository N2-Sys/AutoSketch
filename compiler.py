import argparse
import re
import os
import tempfile

from udf.tree_partition import count_indent
from front.task import Task
from ir.ir import IRFactory
import search

from backend.p4.p4 import P4Factory
import json

def split_udf_and_operators(lines):
    task = Task(merge=True)
    last = None
    modular = []
    for line in lines:
        # 跳过空行
        match_ignore = re.match(r'^\s*\n', line, re.M | re.I)
        if match_ignore:
            continue

        indent = count_indent(line)
        # print(indent)
        if indent == 0:
            if last == "udf": # 获得了一个完整的 udf
                task.new_udf_definition(modular)
            if last == "query": # 获得了一个完整的 query
                task.new_packet_stream(modular)
            modular = []
            if line.find("PacketStream(") != -1: # 是一个 query 的开始
                last = "query"
            elif line.find("def ") != -1: # 是一个 udf 定义的开始
                last = "udf"
        modular.append(line)
    if len(modular) > 0:
        if last == "udf":
            task.new_udf_definition(modular)
        if last == "query":
            task.new_packet_stream(modular)
    # task.factory.dump()
    task.factory.dump_graph("tmp")
    return task

def get_ir(task: Task):
    task.post_processing()
    task.factory.dump_graph("tmp_post_processing")
    # IR
    ir = IRFactory(task)
    ir.dump_table("tmp_ir")
    for (i, compunit) in enumerate(ir.compuints):
        # compunit.factory.dump_graph("tmp_ir", "a", "")
        if i == 0:
            compunit.resona.dump("tmp_resona")
        else:
            compunit.resona.dump("tmp_resona", "a")
    return ir


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", type=str, help="input filename", dest="filename")
    parser.add_argument("--p4output", "-p4o", type=str, help="p4 output filename", dest="p4_filename")
    parser.add_argument("--p4conf", "-p4c", type=str, help="p4 output conf file", dest="p4_conf_filename")
    parser.add_argument("--search", "-s", type=str, help="output path of program for config search")
    parser.add_argument("--p4search", "-p4s", action="store_true", help="do config search while compiling to p4")
    parser.add_argument("--p4verify", "-p4v", action="store_true", help="do config verification while compiling to p4")
    arg = parser.parse_args()

    if arg.filename:
        print("start compiler {}".format(arg.filename))
        with open(arg.filename, "r") as f:
            lines = f.readlines()
            task = split_udf_and_operators(lines)
            ir = get_ir(task)
            # print(lines)
            if arg.search:
                search.SearchGen(ir, task).output(arg.search)
            if arg.p4_filename:
                if arg.p4search:
                    searchDir = arg.p4_filename + '.search'
                    print(f'Running serach in directory \'{searchDir}\'')
                    search.SearchGen(ir, task).output(searchDir)
                    if os.system(f'cd \'{searchDir}\'; make') != 0:
                        raise RuntimeError('Make failed')
                    if os.system(f'cd \'{searchDir}\'; make search') != 0:
                        raise RuntimeError('Search failed')
                    with open(os.path.join(searchDir, 'app-conf.json'), 'r') as fp:
                        print(f'Verifying app config \'{os.path.join(searchDir, "app-conf.json")}\'')
                        appConf = json.load(fp)
                    if arg.p4verify:
                        if os.system(f'cd \'{searchDir}\'; make verify') != 0:
                            raise RuntimeError('Verification failed')
                    P4Factory(ir, task.udfs, appConf).dump_to_file(arg.p4_filename)
                    print('Done')

                else:
                    assert arg.p4_conf_filename
                    with open(arg.p4_conf_filename) as conf_f:
                        P4Factory(ir, task.udfs, json.load(conf_f)).dump_to_file(arg.p4_filename)
            # print(lines)
