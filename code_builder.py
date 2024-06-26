from register_allocator import *
from IR import *

MIN_FUNC = """
min:
    push ebp
    mov ebp, esp
    push ebx
    mov eax, [ebp+8] 
    mov ebx, [ebp+12]

    cmp eax, ebx
    jle .min_done
    mov eax, ebx
    
.min_done:
    pop ebx
    pop ebp
    ret
"""

MAX_FUNC = """
max:
    push ebp
    mov ebp, esp
    push ebx
    mov eax, [ebp+8]
    mov ebx, [ebp+12]

    cmp eax, ebx
    jge .max_done
    mov eax, ebx

.max_done:
    pop ebx
    pop ebp
    ret
"""


class CodeBuilder:
    def __init__(self, func_defs, builder, i):
        self.func_defs = func_defs
        self.builder = builder
        self.i = i
        self.context_builders = {}
        for func in self.func_defs:
            func_name = func.name
            is_entry = True if func_name == "main" else False
            self.context_builders[func_name] = ContextBuilder(self.builder.contexts[func_name], func_name,
                                                              str(func.return_type), is_entry,
                                                              self.i)

    def allocate_registers(self):
        for context_builder in self.context_builders.values():
            context_builder.allocate_registers()
            context_builder.get_spilled_adresses()

    def generate_code(self):
        code = ""
        for context_builder in self.context_builders.values():
            context_builder.generate_context()
        # scalar_variables, array_adresses = None, None
        # for context_builder in self.context_builders.values():
        #    if context_builder.is_entry:
        #        scalar_variables, array_adresses = context_builder.get_entry_info()
        #        break
        # bss_vars = []
        # for var, label in scalar_variables.items():
        #    if label not in regs and label not in xmm_regs:
        #        bss_vars.append(var)
        # if len(bss_vars) != 0:
        #    code += "section .bss\n"
        #    for var in bss_vars:
        #        code += "\t" + var + " resd 1\n"
        # decl_arrays = []
        # for arr in array_adresses.keys():
        #    decl_arrays.append(arr)
        # if len(decl_arrays) != 0:
        #    code += "section .data\n"
        #    for arr in decl_arrays:
        #        code += "\t" + arr + " dd " + ", ".join(
        #            list(map(lambda x: str(x), flatten(array_adresses[arr][3])))) + "\n"

        code += "section .text\n"
        code += "global "
        for i, context_builder in enumerate(self.context_builders.values()):
            if not context_builder.is_entry:
                if i == 0:
                    code += context_builder.func_name
                else:
                    code += ", " + context_builder.func_name
        code += "\n"
        code += "extern print_register_value, print_register_value_float\n"
        for context_builder in self.context_builders.values():
            if not context_builder.is_entry:
                code += str(context_builder)
        code += "\n"
        code += MIN_FUNC
        code += "\n"
        code += MAX_FUNC
        if self.i == -1:
            with open(f"out.asm", 'w') as file:
                file.write(code)
        else:
            with open(f"asm/program{self.i}.asm", 'w') as file:
                file.write(code)


class ContextBuilder:
    def __init__(self, context, func_name, func_type, is_entry, i):
        self.context = context
        self.is_entry = is_entry
        self.func_name = func_name
        self.func_type = func_type
        self.i = i
        self.scalar_variables = {}
        self.array_adresses = {}
        self.code = []
        self.local_sdvig = 0

    def allocate_registers(self):
        self.context.build_lives()
        # if self.i == 3:
        #    for label, lives in self.context.labels_to_live.items():
        #        print(label, lives)
        k_reg = len(color_to_regs)
        k_xmm_reg = len(color_to_xmm_regs)
        int_ifg = IFG(k_reg)
        float_ifg = IFG(k_xmm_reg)

        self.context.slices_variables = list(set(self.context.slices_variables))

        int_ifg.build(self.context, True, list(map(lambda x: x.replace("$", "_"), self.context.slices_variables)), [])
        spill_var = int_ifg.try_color()
        # if self.i == 1 and self.func_name == "tile":
        #    int_ifg.to_graph("IFG/ifg.txt")

        spill_vars = []
        while spill_var is not None:
            spill_vars.append(spill_var)
            int_ifg.build(self.context, True, spill_vars + list(map(lambda x: x.replace("$", "_"), self.context.slices_variables)), [])
            spill_var = int_ifg.try_color()

        added_vars = self.context.slices_variables

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

    def is_scalar_arg(self, var):
        if self.is_entry:
            return False, None
        func_def_action = self.context.graph.vertexes[0].block[0]
        sdvig = 8
        for arg in func_def_action.arguments:
            if arg.dimentions is None:
                if arg.name == var:
                    return True, "+ " + str(sdvig)
                sdvig += 4
            else:
                sdvig += 4
                for dim in arg.dimentions:
                    if dim == var:
                        return True, "+ " + str(sdvig)
                    sdvig += 4
        return False, None

    def get_array_args(self):
        if self.is_entry:
            return []
        array_args = []
        sdvig = 8
        func_def_action = self.context.graph.vertexes[0].block[0]
        for arg in func_def_action.arguments:
            if arg.dimentions is None:
                sdvig += 4
            else:
                array_args.append((arg.name, "[ebp + " + str(sdvig) + "]", arg.dimentions))
                sdvig += 4
                for _ in arg.dimentions:
                    sdvig += 4
        return array_args

    def get_spilled_adresses(self):
        self.array_adresses = {}
        self.local_sdvig = 0
        for var, reg in self.scalar_variables.items():
            if reg == "spilled":
                if self.is_entry:
                    self.scalar_variables[var] = "[" + var + "]"
                else:
                    is_arg, sdvig = self.is_scalar_arg(var)
                    if is_arg:
                        self.scalar_variables[var] = "[ebp " + sdvig + "]"
                    else:
                        self.local_sdvig += 4
                        self.scalar_variables[var] = "[ebp - " + str(self.local_sdvig) + "]"

        declared_arrays = self.context.get_declared_arrays()
        for array in declared_arrays:
            if self.is_entry:
                self.array_adresses[array[0]] = ("[" + array[0] + "]", False, array[1], array[2])
            else:
                n_bytes = 4 * functools.reduce(lambda x, y: x * y, array[1])
                self.local_sdvig += n_bytes
                self.array_adresses[array[0]] = ("[ebp - " + str(self.local_sdvig) + "]", False, array[1])

        array_params = self.get_array_args()
        for param in array_params:
            self.array_adresses[param[0]] = (param[1], True, param[2])

    def get_entry_info(self):
        if self.is_entry:
            return self.scalar_variables, self.array_adresses
        else:
            return None

    def generate_entry_block(self):
        code = []
        used_xmm = []
        for var, reg in self.scalar_variables.items():
            if reg in xmm_regs and reg not in used_xmm:
                used_xmm.append(reg)
        if len(used_xmm) != 0:
            used_xmm.append("xmm0")
            used_xmm.append("xmm1")
        if not self.is_entry:
            code.append(Push("ebp"))
            code.append(Move("ebp", "esp"))
            if self.local_sdvig != 0:
                code.append(Sub("esp", str(self.local_sdvig)))
            code.append(Push("ebx"))
            code.append(Push("edi"))
            code.append(Push("esi"))
            for xmm in used_xmm:
                code.append(Sub("esp", "16"))
                code.append(MoveDQU("[esp]", xmm))
            for var, reg in self.scalar_variables.items():
                is_arg, sdvig = self.is_scalar_arg(var)
                if is_arg:
                    # print(var, reg, sdvig)
                    if reg in regs:
                        code.append(Move(reg, "[ebp " + sdvig + "]"))
                    if reg in xmm_regs:
                        code.append(MoveSS(reg, "[ebp " + sdvig + "]"))
        return code, used_xmm

    def compute_used_regs(self):
        for v in self.context.graph.vertexes:
            for instruction in v.block:
                if self.context.graph.instructions_to_labels[instruction] not in self.context.labels_to_live:
                    instruction.used_regs = []
                    continue
                lives = self.context.labels_to_live[self.context.graph.instructions_to_labels[instruction]]
                used_regs = []
                for var in lives:
                    sp_var = var.split("_")
                    if len(sp_var) > 1 and sp_var[0] == "tmp":
                        var = var.replace("_", "$")
                    if self.scalar_variables[var] in regs or self.scalar_variables[var] in xmm_regs:
                        used_regs.append(self.scalar_variables[var])
                instruction.used_regs = used_regs

    def generate_context(self):
        self.code = []
        self.context.quit_ssa()
        # for instruction, label in self.context.graph.instructions_to_labels.items():
        #        print("====================")
        # for label, lives in self.context.labels_to_live.items():
        #    print(label, lives)
        self.compute_used_regs()
        entry_code, used_xmm = self.generate_entry_block()
        self.code += entry_code
        first = self.context.graph.vertexes[0].output_vertexes[0]
        stack = [first]
        for v in self.context.graph.vertexes:
            v.checked = False
        while len(stack) != 0:
            current = stack.pop()
            current.checked = True
            self.generate_block(current, used_xmm)
            for next_v in current.output_vertexes:
                if not next_v.checked:
                    stack.append(next_v)
        self.fix_reduntancy()

    def generate_block(self, v, used_xmm):
        self.code.append(Label(v.label))
        phi_assigns = []
        compared = None
        for i, instruction in enumerate(v.block):
            if isinstance(instruction, IsTrueInstruction):
                self.code += instruction.get_low_ir_branch(self.scalar_variables, v.output_vertexes, phi_assigns,
                                                           compared)
                phi_assigns = []
            elif isinstance(instruction, ReturnInstruction):
                self.code += instruction.get_low_ir_return(self.scalar_variables, self.is_entry, self.func_type,
                                                           used_xmm)
            elif isinstance(instruction, AtomicAssign):
                if instruction.is_phi:
                    phi_assigns += instruction.get_low_ir_arr(self.scalar_variables, self.array_adresses, self.context.slices_variables)
                else:
                    self.code += instruction.get_low_ir_arr(self.scalar_variables, self.array_adresses, self.context.slices_variables)
            elif isinstance(instruction, SliceAssign):
                self.code += instruction.get_low_ir_arr(self.scalar_variables, self.array_adresses, self.context.slices_variables)
            elif isinstance(instruction, ArrayInitInstruction):
                if not self.is_entry:
                    self.code += instruction.get_low_ir_arr_decl(self.array_adresses)
            elif isinstance(instruction, BinaryAssign) and instruction.is_cmp():
                if i == len(v.block) - 1:
                    self.code += instruction.get_low_ir(self.scalar_variables)
                elif isinstance(v.block[i + 1], IsTrueInstruction):
                    code, compared = instruction.get_low_ir_cmp(self.scalar_variables)
                    self.code += code
                else:
                    self.code += instruction.get_low_ir_ass(self.scalar_variables, self.context.slices_variables)
            elif isinstance(instruction, (UnaryAssign, BinaryAssign)):
                self.code += instruction.get_low_ir_ass(self.scalar_variables, self.context.slices_variables)
            else:
                self.code += instruction.get_low_ir(self.scalar_variables)
        self.code += phi_assigns
        if len(v.output_vertexes) == 1:
            self.code.append(Jump(v.output_vertexes[0].label))

    def fix_reduntancy(self):
        new_code = []
        for i, c in enumerate(self.code):
            not_append = not (isinstance(c, (Move, MoveSS)) and c.arg1 == c.arg2)
            if isinstance(c, Jump) and i != len(self.code) - 1:
                if isinstance(self.code[i + 1], Label) and c.label == self.code[i + 1].label:
                    not_append = False
            if not_append:
                new_code.append(c)
        self.code = new_code

    def __str__(self):
        s = "_start:" if self.is_entry else self.func_name + ":"
        s += "\n"
        for c in self.code:
            s += "\t" + str(c) + "\n"
        return s
