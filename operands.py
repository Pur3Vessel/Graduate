from lattice import *
from low_IR import *


def generate_array_index_code(name, dimentions, scalar_variables, array_adresses, used_regs):
    code = []
    pop_intr = []
    info = array_adresses[name]
    addr = info[0]
    dimentions_sizes = info[2]
    r = ""

    dimentions_regs = []
    for dim in dimentions:
        dimentions_regs.append(dim.get_low_ir(scalar_variables))

    if info[1]:
        for reg in regs:
            if reg not in used_regs and reg not in dimentions_regs:
                used_regs.append(reg)
                r = reg
                code.append(Push(reg))
                code.append(Move(reg, addr))
                addr = reg
                break
    addr = addr.replace("[", "").replace("]", "")
    n_dims = len(dimentions)
    assert n_dims < 5
    index_regs = []
    if n_dims == 1:
        n_regs = 1
    else:
        n_regs = n_dims - 1

    last_dim_reg = dimentions_regs[-1]
    if n_dims == 1:
        last_dim_reg = ""

    for i in range(n_regs):
        if dimentions_regs[i] in regs and dimentions_regs[i] not in used_regs:
            index_regs.append(dimentions_regs[i])
        else:
            index_regs.append("spilled")

    for i in range(n_regs):
        if index_regs[i] == "spilled":
            for reg in regs:
                if reg not in used_regs and reg not in index_regs and reg != last_dim_reg:
                    index_regs[i] = reg

    for reg in index_regs:
        code.append(Push(reg))

    if n_dims == 1:
        dim_reg = dimentions_regs[0]
        code.append(Move(index_regs[0], dim_reg))
    else:
        for i, reg in enumerate(index_regs):
            dim_reg = dimentions_regs[i]
            code.append(Move(reg, dim_reg))
            for size in dimentions_sizes[i + 1:]:
                if type(size) != int:
                    size_reg = scalar_variables[size]
                else:
                    size_reg = size
                code.append(Imul(reg, str(size_reg)))
        for reg in enumerate(index_regs[1:]):
            code.append(Add(index_regs[0], reg))
        dim_reg = dimentions[-1].get_low_ir(scalar_variables)
        code.append(Add(index_regs[0], dim_reg))
    for reg in index_regs[::-1]:
        pop_intr.append(Pop(reg))
    if info[1]:
        pop_intr.append(Pop(r))
    code.append(Shl(index_regs[0], "2"))
    src = "[" + addr + " + " + index_regs[0] + ']'
    return code, src, pop_intr


class Operand(ABC):
    def get_low_ir(self, scalar_variables):
        pass


class IdOperand(Operand):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def get_low_ir(self, scalar_variables):
        reg = scalar_variables[self.value]
        if reg == "spilled":
            reg = "Место в памяти для " + self.value
        return reg


class FloatConstantOperand(Operand):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def get_low_ir(self, scalar_variables):
        return str(self.value)


class IntConstantOperand(Operand):
    def __init__(self, value):
        self.value = int(value)

    def __str__(self):
        return str(self.value)

    def get_low_ir(self, scalar_variables):
        return str(self.value)


class BoolConstantOperand(Operand):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def get_low_ir(self, scalar_variables):
        if self.value:
            return "1"
        else:
            return "0"


class ArrayUseOperand(Operand):
    def __init__(self, name, indexing, dimention_variables):
        self.name = name
        self.indexing = indexing
        self.dimention_variables = dimention_variables

    def __str__(self):
        s = self.name + "["
        for i, idx in enumerate(self.indexing):
            s += str(idx)
            if i != len(self.indexing) - 1:
                s += ", "
        s += "]"
        return s

    def get_operands(self):
        return self.indexing

    def is_use_op(self, value):
        is_use = False
        for arg in self.indexing:
            is_use = is_use or value == arg.value
        if self.dimention_variables is not None:
            for d in self.dimention_variables:
                if d == value:
                    return True
        return is_use

    def place_constants(self, lattice):
        changed = False
        for i, arg in enumerate(self.indexing):
            if isinstance(arg, IdOperand):
                if arg.value in lattice.sl:
                    val = lattice.sl[arg.value]
                    if not isinstance(val, ConstantLatticeElement):
                        if type(val) is int:
                            self.indexing[i] = IntConstantOperand(val)
                        elif type(val) is float:
                            self.indexing[i] = FloatConstantOperand(val)
                        else:
                            assert type(val) is bool
                            self.indexing[i] = BoolConstantOperand(val)
                        changed = True
        return changed

    def remove_versions(self):
        for i, arg in enumerate(self.indexing):
            if isinstance(arg, IdOperand):
                self.indexing[i] = IdOperand(arg.value.split("_")[0])

    def replace_operand(self, name, new_name):
        new_args = []
        for arg in self.indexing:
            if arg.value == name:
                new_args.append(IdOperand(new_name))
            else:
                new_args.append(arg)
        self.indexing = new_args

    def replace_tmp(self, version):
        for i, arg in enumerate(self.indexing):
            if isinstance(arg, IdOperand) and len(arg.value.split("$")) > 1:
                version = version + 1
                new_tmp = "tmp$" + str(version)
                self.indexing[i] = IdOperand(new_tmp)

        return version

    def rename_operands(self, name, version):
        new_args = []
        for arg in self.indexing:
            if arg.value == name:
                new_args.append(IdOperand(name + "_" + str(version)))
            else:
                new_args.append(arg)
        self.indexing = new_args


class FuncCallOperand(Operand):
    def __init__(self, func_name, arguments):
        self.name = func_name
        self.args = arguments

    def __str__(self):
        s = "CALL " + self.name + "("
        for i, arg in enumerate(self.args):
            s += str(arg)
            if i != len(self.args) - 1:
                s += ", "
        s += ")"
        return s

    def get_operands(self):
        return self.args

    def is_use_op(self, value):
        is_use = False
        for arg in self.args:
            is_use = is_use or value == arg.value
        return is_use

    def place_constants(self, lattice):
        changed = False
        for i, arg in enumerate(self.args):
            if isinstance(arg, IdOperand):
                if arg.value in lattice.sl:
                    val = lattice.sl[arg.value]
                    if not isinstance(val, ConstantLatticeElement):
                        if type(val) is int:
                            self.args[i] = IntConstantOperand(val)
                        elif type(val) is float:
                            self.args[i] = FloatConstantOperand(val)
                        else:
                            assert type(val) is bool
                            self.args[i] = BoolConstantOperand(val)
                        changed = True
        return changed

    def remove_versions(self):
        for i, arg in enumerate(self.args):
            if isinstance(arg, IdOperand):
                self.args[i] = IdOperand(arg.value.split("_")[0])

    def replace_operand(self, name, new_name):
        new_args = []
        for arg in self.args:
            if arg.value == name:
                new_args.append(IdOperand(new_name))
            else:
                new_args.append(arg)
        self.args = new_args

    def replace_tmp(self, version):
        for i, arg in enumerate(self.args):
            if isinstance(arg, IdOperand) and len(arg.value.split("$")) > 1:
                version = version + 1
                new_tmp = "tmp$" + str(version)
                self.args[i] = IdOperand(new_tmp)

        return version

    def rename_operands(self, name, version):
        new_args = []
        for arg in self.args:
            if arg.value == name:
                new_args.append(IdOperand(name + "_" + str(version)))
            else:
                new_args.append(arg)
        self.args = new_args

    def get_call_instructions(self, scalar_variables, array_adresses):
        params_sdvig = 0
        load_params = []
        remove_params = []

        for arg in self.args[::-1]:
            if arg.value in scalar_variables:
                reg = arg.get_low_ir(scalar_variables)
                if reg not in xmm_regs:
                    load_params.append(Push(reg))
                else:
                    load_params.append(Sub("esp", "4"))
                    load_params.append(MoveSS("dword [esp]", reg))
                params_sdvig += 4
            elif arg.value in array_adresses:
                info = array_adresses[arg.value]
                for dim in info[2][::-1]:
                    if type(dim) == int:
                        load_params.append(Push(str(dim)))
                    else:
                        reg = dim.get_low_ir(scalar_variables)
                        load_params.append(Push(reg))
                    params_sdvig += 4
                if info[1]:
                    load_params.append(Push(info[0]))
                else:
                    load_params.append(Lea("eax", info[0]))
                    load_params.append(Push("eax"))
                params_sdvig += 4
            else:
                reg = arg.get_low_ir(scalar_variables)
                load_params.append(Push(reg))
                params_sdvig += 4

        if params_sdvig != 0:
            remove_params.append(Add("esp", str(params_sdvig)))

        return load_params, remove_params


class FuncArgOperand(Operand):
    def __init__(self, type, name, dimentions):
        self.type = type
        self.name = name
        self.dimentions = dimentions

    def __str__(self):
        d = ""
        if self.dimentions is not None:
            d = "[" + ", ".join(self.dimentions) + "]"
        return self.type + " " + self.name + d
