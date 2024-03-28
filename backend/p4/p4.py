from backend.p4._template import p4_template, unit_indent
from backend.p4._struct_definition import StructDefinitionFactory
from backend.p4._switch_egress import SwitchEgressFactory

from ir.ir import IRFactory

class P4Factory:
    def __init__(self, ir : IRFactory, udfs, register_conf):
        self.struct_definition_factory = StructDefinitionFactory()
        self.switch_egress_factory = SwitchEgressFactory(self.struct_definition_factory, ir, udfs, register_conf)

    def dump_to_file(self, filename : str, write_policy="w"):
        output = p4_template
        output = output.replace("<{ struct definition }>", self.struct_definition_factory.dump(''))
        output = output.replace("<{ SwitchEgress }>", self.switch_egress_factory.dump(unit_indent))

        with open(filename, write_policy) as f:
            f.write(output)