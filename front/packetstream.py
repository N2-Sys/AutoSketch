from front.operators import OperatorFactory, Operator

# global_dict = {}
# factory = OperatorFactory(merge=True)
# start = factory.start()

class PacketStream:
    def __init__(self, task, name: str, requirement_dict:dict):
        self.requirement_dict = requirement_dict
        self.name = name
        self.lastop = task.start
        self.task = task
        self.link_lastop(task.factory.empty(task.start))
        self.factory = task.factory
    
    def link_lastop(self, new_op: Operator):
        self.lastop = new_op
        self.task.global_dict[self.name] = new_op
        
    def filter(self, left_value, op, right_value):
        self.link_lastop(self.factory.filter(self.lastop, left_value, op, right_value))
        return self
    
    def map(self, map_keys: list, new_import: dict):
        self.link_lastop(self.factory.map(self.lastop, map_keys, new_import))
        return self
    
    def distinct(self, distinct_keys: list):
        self.link_lastop(self.factory.distinct(self.lastop, distinct_keys))
        return self
    
    def reduce(self, reduce_keys: list, result: str):
        self.link_lastop(self.factory.reduce(self.lastop, reduce_keys, result))
        return self
    
    def zip(self, stream_name:str, left_key:str, right_key:str):
        new_op = self.factory.zip(self.lastop, left_key, right_key)
        self.link_lastop(new_op)
        
        merged_stream_lastop = self.task.global_dict.get(stream_name)
        merged_stream_lastop.add_next(new_op)
        new_op.add_prev(merged_stream_lastop)
        
        return self
    
    def groupby(self, func_name:str, index: list, args: list, registers:list, out:list):
        self.link_lastop(self.factory.groupby(self.lastop, func_name, index, args, registers, out))
        return self