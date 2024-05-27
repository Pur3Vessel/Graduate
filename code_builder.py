from register_allocator import *
from IR import *


class CodeBuilder:
    def __init__(self, func_defs, builder, i):
        self.func_defs = func_defs
        self.builder = builder
        self.i = i
        self.context_builders = {}
        for func in self.func_defs:
            func_name = func.name
            is_entry = True if func_name == "main" else False
            self.context_builders[func_name] = ContextBuilder(self.builder.contexts[func_name], func_name, is_entry,
                                                              self.i)

    def allocate_registers(self):
        for context_builder in self.context_builders.values():
            context_builder.allocate_registers()

    def generate_code(self):
        for context_builder in self.context_builders.values():
            context_builder.generate_context()
        code = "section .data\n"
        code += "section .text\n"
        for context_builder in self.context_builders.values():
            code += str(context_builder)
        with open(f"asm/program{self.i}.asm", 'w') as file:
            file.write(code)


class ContextBuilder:
    def __init__(self, context, func_name, is_entry, i):
        self.context = context
        self.is_entry = is_entry
        self.func_name = func_name
        self.i = i
        self.scalar_variables = {}
        self.code = []

    def allocate_registers(self):
        self.context.build_lives()
        k_reg = len(color_to_regs)
        k_xmm_reg = len(color_to_xmm_regs)
        int_ifg = IFG(k_reg)
        float_ifg = IFG(k_xmm_reg)

        int_ifg.build(self.context, True, [], [])
        spill_var = int_ifg.try_color()
        spill_vars = []
        while spill_var is not None:
            spill_vars.append(spill_var)
            int_ifg.build(self.context, True, spill_vars, [])
            spill_var = int_ifg.try_color()

        #added_vars = spill_vars
        #spill_vars = []
        added_vars = []

        float_ifg.build(self.context, False, [], added_vars)
        spill_var = float_ifg.try_color()
        while spill_var is not None:
            spill_vars.append(spill_var)
            float_ifg.build(self.context, False, spill_vars, added_vars)
            spill_var = float_ifg.try_color()

        for var, color in int_ifg.vars_to_color.items():
            if var.split("_")[0] == "tmp":
                var = var.replace("_", "$")
            self.scalar_variables[var] = color_to_regs[color]

        for var, color in float_ifg.vars_to_color.items():
            if var.split("_")[0] == "tmp":
                var = var.replace("_", "$")
            self.scalar_variables[var] = color_to_xmm_regs[color]

        for var in spill_vars:
            if var.split("_")[0] == "tmp":
                var = var.replace("_", "$")
            self.scalar_variables[var] = "spilled"

    def generate_context(self):
        self.code = []
        self.context.quit_ssa()
        self.context.graph.set_labels()
        first = self.context.graph.vertexes[0]
        stack = [first]
        for v in self.context.graph.vertexes:
            v.checked = False
        while len(stack) != 0:
            current = stack.pop()
            current.checked = True
            self.generate_block(current)
            for next_v in current.output_vertexes:
                if not next_v.checked:
                    stack.append(next_v)

    def generate_block(self, v):
        self.code.append(Label(v.label))
        for instruction in v.block:
            if isinstance(instruction, IsTrueInstruction):
                self.code += instruction.get_low_ir_branch(self.scalar_variables, v.output_vertexes)
            elif isinstance(instruction, ReturnInstruction):
                self.code += instruction.get_low_ir_return(self.scalar_variables, self.is_entry)
            else:
                self.code += instruction.get_low_ir(self.scalar_variables)
        if len(v.output_vertexes) == 1:
            self.code.append(Jump(v.output_vertexes[0].label))

    def __str__(self):
        s = "_start:" if self.is_entry else self.func_name + ":"
        s += "\n"
        for c in self.code:
            s += "\t" + str(c) + "\n"
        return s
