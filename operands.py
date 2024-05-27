from abc import ABC
from lattice import *


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
    def __init__(self, name, indexing):
        self.name = name
        self.indexing = indexing

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

    def rename_operands(self, name, version):
        new_args = []
        for arg in self.args:
            if arg.value == name:
                new_args.append(IdOperand(name + "_" + str(version)))
            else:
                new_args.append(arg)
        self.args= new_args


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
