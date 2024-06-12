from operands import *
import functools


def get_reg(use_regs):
    for reg in regs:
        if reg != "eax" and reg != "edx" and reg not in use_regs:
            return reg


def revert_cmp_op(op):
    if op == ">":
        return "<"
    if op == "<":
        return ">"
    if op == "<=":
        return ">="
    if op == ">=":
        return "<="
    return op


def get_set_cmp(op):
    if op == "==":
        return Sete("al")
    if op == "!=":
        return Setne("al")
    if op == ">":
        return Setg("al")
    if op == "<":
        return Setl("al")
    if op == ">=":
        return Setge("al")
    if op == "<=":
        return Setle("al")


def nested_list_to_str(nested_list):
    if isinstance(nested_list, list):
        return "{" + ",".join(nested_list_to_str(item) for item in nested_list) + "}"
    return str(nested_list)


def convert_to_int(nested_list):
    if isinstance(nested_list, list):
        return [convert_to_int(item) for item in nested_list]
    elif isinstance(nested_list, float):
        return int(nested_list)
    return nested_list


def flatten(nested_list):
    flat_list = []

    def _flatten(sublist):
        if isinstance(sublist, list):
            for item in sublist:
                _flatten(item)
        else:
            flat_list.append(sublist)

    _flatten(nested_list)
    return flat_list


def is_assign(stmt):
    return isinstance(stmt, AtomicAssign) or isinstance(stmt, BinaryAssign) or isinstance(stmt,
                                                                                          UnaryAssign) or isinstance(
        stmt, PhiAssign)


class UnaryExpressions(Enum):
    NOT = "not"
    MINUS = "-"


class BinaryOperations(Enum):
    MINUS = "-"
    PLUS = "+"
    DIV = "div"
    MOD = "mod"
    AND = "and"
    OR = "or"
    EQ = '=='
    NEQ = "!="
    MORE = ">"
    LESS = "<"
    MORE_EQ = ">="
    LESS_EQ = "<="


class IR(ABC):
    def __init__(self):
        self.used_regs = None

    def get_low_ir(self, scalar_variables):
        return []


class NullInstruction(IR):
    def __str__(self):
        return "null instruction"


class FuncDefInstruction(IR):
    def __init__(self, type, name, arguments):
        super().__init__()
        self.type = type
        self.name = name
        self.arguments = arguments

    def __str__(self):
        s = self.type + " " + self.name + "("
        for i, arg in enumerate(self.arguments):
            s += str(arg)
            if i != len(self.arguments) - 1:
                s += ", "
        s += ")"
        return s

    def rename_operands(self):
        pass

    def place_constants(self, lattice):
        return False

    def remove_versions(self):
        pass

    def is_use_op(self, op):
        for arg in self.arguments:
            if arg.dimentions is None:
                if arg.name == op:
                    return True
            else:
                for d in arg.dimentions:
                    if d == op:
                        return True
        return False


class ArrayInitInstruction(IR):
    def __init__(self, type, name, dimentions, assign):
        super().__init__()
        self.type = type
        self.name = name
        self.dimentions = dimentions
        self.assign = assign
        self.dimentions = list(map(lambda x: int(x), self.dimentions))
        if self.type == "int" and self.assign is not None:
            self.assign = convert_to_int(self.assign)

    def __str__(self):
        s = self.type + " " + self.name + "["
        for i, dim in enumerate(self.dimentions):
            s += str(dim)
            if i != len(self.dimentions) - 1:
                s += ", "
        s += "]"
        if self.assign is not None:
            s += " = " + nested_list_to_str(self.assign)
        return s

    def rename_operands(self, name, version):
        pass

    def place_constants(self, lattice):
        return False

    def remove_versions(self):
        pass

    def get_operands(self):
        return []

    def is_use_op(self, op):
        return False

    def get_low_ir_arr_decl(self, array_adresses):
        code = []
        n_elems = functools.reduce(lambda x, y: x * y, self.dimentions)
        sdvig = 0
        if self.assign is None:
            elems = [0] * n_elems
        else:
            elems = flatten(self.assign)
        adress = array_adresses[self.name][0].replace("[", "").replace("]", "")
        for i in range(n_elems):
            if self.type == "float":
                code.append(
                    Move("[" + adress + " + " + str(sdvig) + "]", "dword " + float_to_ieee754(elems[i])))
            else:
                code.append(Move("[" + adress + " + " + str(sdvig) + "]", "dword " + str(elems[i])))
            sdvig += 4
        return code


class AtomicAssign(IR):
    def __init__(self, type, value, argument, dimentions, dimentions_variables):
        super().__init__()
        self.type = type
        self.value = value
        self.argument = argument
        self.dimentions = dimentions
        self.is_phi = False
        self.dimentions_variables = dimentions_variables

    def __str__(self):
        d = ""
        if self.dimentions is not None:
            d = "["
            d += ", ".join(str(dim) for dim in self.dimentions)
            d += "]"
        return self.type + " " + self.value + d + " <- " + str(self.argument)

    def rename_operands(self, name, version):
        if isinstance(self.argument, IdOperand):
            if self.argument.value == name:
                new_op = IdOperand(name + "_" + str(version))
                self.argument = new_op
        if isinstance(self.argument, (FuncCallOperand, ArrayUseOperand)):
            self.argument.rename_operands(name, version)
        if self.dimentions is not None:
            for i, d in enumerate(self.dimentions):
                if isinstance(d, IdOperand) and d.value == name:
                    self.dimentions[i] = IdOperand(d.value + "_" + str(version))

    def get_operands(self):
        operands = []
        if self.dimentions is not None:
            for dim in self.dimentions:
                operands.append(dim)
        if isinstance(self.argument, FuncCallOperand):
            operands += self.argument.get_operands()
            return operands
        if isinstance(self.argument, ArrayUseOperand):
            operands += self.argument.get_operands()
            return operands
        operands.append(self.argument)
        return operands

    def is_use_op(self, value):
        if self.dimentions is not None:
            for d in self.dimentions:
                if d.value == value:
                    return True
            if self.dimentions_variables is not None:
                for d in self.dimentions_variables[1:]:
                    if d == value:
                        return True
        if isinstance(self.argument, IntConstantOperand) or isinstance(self.argument,
                                                                       BoolConstantOperand) or isinstance(self.argument,
                                                                                                          FloatConstantOperand):
            return False
        if isinstance(self.argument, FuncCallOperand) or isinstance(self.argument, ArrayUseOperand):
            return self.argument.is_use_op(value)
        return self.argument.value == value

    def lat_eval(self, lattice):
        if isinstance(self.argument, FuncCallOperand) or isinstance(self.argument, ArrayUseOperand):
            return ConstantLatticeElement.LOW
        if isinstance(self.argument, IntConstantOperand) or isinstance(self.argument,
                                                                       BoolConstantOperand) or isinstance(self.argument,
                                                                                                          FloatConstantOperand):
            return self.argument.value
        if self.argument.value not in lattice.sl:
            return ConstantLatticeElement.LOW
        return lattice.sl[self.argument.value]

    def place_constants(self, lattice):
        if isinstance(self.argument, FuncCallOperand) or isinstance(self.argument, ArrayUseOperand):
            return self.argument.place_constants(lattice)

        if isinstance(self.argument, IdOperand):
            if self.argument.value in lattice.sl:
                val = lattice.sl[self.argument.value]
                if not isinstance(val, ConstantLatticeElement):
                    if type(val) is int:
                        self.argument = IntConstantOperand(val)
                    elif type(val) is float:
                        self.argument = FloatConstantOperand(val)
                    else:
                        assert type(val) is bool
                        self.argument = BoolConstantOperand(val)
                    return True

        if self.dimentions is not None:
            for i, d in enumerate(self.dimentions):
                if d.value in lattice.sl:
                    val = lattice.sl[d.value]
                    if not isinstance(val, ConstantLatticeElement):
                        if type(val) is int:
                            self.dimentions[i] = IntConstantOperand(val)

        return False

    def is_def(self, op):
        return op.value == self.value

    def remove_versions(self):
        self.value = self.value.split("_")[0]
        if isinstance(self.argument, FuncCallOperand) or isinstance(self.argument, ArrayUseOperand):
            self.argument.remove_versions()
        if isinstance(self.argument, IdOperand):
            self.argument = IdOperand(self.argument.value.split("_")[0])
        if self.dimentions is not None:
            for i, d in enumerate(self.dimentions):
                if isinstance(d, IdOperand):
                    self.dimentions[i] = IdOperand(d.value.split("_")[0])

    def replace_operand(self, name, new_name):
        if isinstance(self.argument, (FuncCallOperand, ArrayUseOperand)):
            self.argument.replace_operand(name, new_name)
        else:
            if self.argument.value == name:
                self.argument = IdOperand(new_name)
            if self.dimentions is not None:
                new_dims = []
                for d in self.dimentions:
                    if d.value == name:
                        new_dims.append(IdOperand(new_name))
                    else:
                        new_dims.append(d)
                self.dimentions = new_dims

    def replace_tmp(self, version):
        if len(self.value.split("$")) > 1:
            version = version + 1
            new_tmp = "tmp$" + str(version)
            old = self.value
            self.value = new_tmp
            return version, old, new_tmp
        return version, None, None

    def get_low_ir_arr(self, scalar_variables, array_adresses):
        code = []
        if self.dimentions is None:
            reg = scalar_variables[self.value]
            if isinstance(self.argument, (IntConstantOperand, BoolConstantOperand, FloatConstantOperand, IdOperand)):
                if self.type == "float":
                    if isinstance(self.argument, (IntConstantOperand, FloatConstantOperand)):
                        argument_reg = float_to_ieee754(self.argument.value)
                    else:
                        argument_reg = self.argument.get_low_ir(scalar_variables)
                    if argument_reg not in xmm_regs:
                        code.append(Sub("esp", "4"))
                        code.append(Move("dword [esp]", argument_reg))
                        if reg in xmm_regs:
                            code.append(MoveSS(reg, "[esp]"))
                        else:
                            code.append(MoveSS("xmm0", "[esp]"))
                            code.append(MoveSS(reg, "xmm0"))
                        code.append(Add("esp", "4"))
                    else:
                        code.append(MoveSS(reg, argument_reg))
                else:
                    argument_reg = self.argument.get_low_ir(scalar_variables)
                    if reg not in regs and argument_reg not in regs:
                        code.append(Move("eax", argument_reg))
                        code.append(Move(reg, "eax"))
                    else:
                        code.append(Move(reg, argument_reg))
            if isinstance(self.argument, FuncCallOperand):
                if "ecx" in self.used_regs and reg != "ecx":
                    code.append(Push("ecx"))
                if "edx" in self.used_regs and reg != "edx":
                    code.append(Push("edx"))
                load_params, remove_params = self.argument.get_call_instructions(scalar_variables, array_adresses)
                code += load_params
                code.append(Call(self.argument.name))
                if self.type == "float":
                    if reg in xmm_regs:
                        code.append(Sub("esp", "4"))
                        code.append(Fstp("dword [esp]"))
                        code.append(MoveSS(reg, "dword [esp]"))
                        code.append(Add("esp", "4"))
                    else:
                        code.append(Fstp("dword " + reg))
                else:
                    code.append(Move(reg, "eax"))
                code += remove_params
                if "edx" in self.used_regs and reg != "edx":
                    code.append(Pop("edx"))
                if "ecx" in self.used_regs and reg != "ecx":
                    code.append(Pop("ecx"))
            if isinstance(self.argument, ArrayUseOperand):
                arr_code, src, pop_intr = generate_array_index_code(self.argument.name, self.argument.indexing,
                                                                    scalar_variables, array_adresses, [reg], self.used_regs)
                code += arr_code
                if self.type == "float":
                    if reg not in xmm_regs:
                        code.append(MoveSS("xmm0", src))
                        code.append(MoveSS(reg, "xmm0"))
                    else:
                        code.append(MoveSS(reg, src))
                else:
                    if reg not in regs:
                        code.append(Move("eax", src))
                        code.append(Move(reg, "eax"))
                    else:
                        code.append(Move(reg, src))
                code += pop_intr
            return code
        else:
            reg = self.argument.get_low_ir(scalar_variables)
            arr_code, src, pop_intr = generate_array_index_code(self.value, self.dimentions,
                                                                scalar_variables, array_adresses, [reg], self.used_regs)
            code += arr_code
            if self.type == "float":
                if reg not in xmm_regs:
                    code.append(MoveSS("xmm0", reg))
                    code.append(MoveSS(src, "xmm0"))
                else:
                    code.append(MoveSS(src, reg))
            else:
                if reg not in regs:
                    code.append(Move("eax", reg))
                    code.append(Move(src, "eax"))
                else:
                    code.append(Move(src, reg))
            code += pop_intr
            return code


class UnaryAssign(IR):
    def __init__(self, type, value, op, argument):
        super().__init__()
        self.type = type
        self.value = value
        self.op = op
        self.arg = argument

    def __str__(self):
        d = ""
        return self.type + " " + self.value + d + " <- " + self.op + " " + str(self.arg)

    def rename_operands(self, name, version):
        if isinstance(self.arg, IdOperand):
            if self.arg.value == name:
                new_op = IdOperand(name + "_" + str(version))
                self.arg = new_op

    def get_operands(self):
        return [self.arg]

    def is_use_op(self, value):
        if isinstance(self.arg, (IntConstantOperand, BoolConstantOperand, FloatConstantOperand)):
            return False
        return self.arg.value == value

    def lat_eval(self, lattice):
        if self.type == "bool":
            assert self.op == "not"
            if isinstance(self.arg, BoolConstantOperand):
                return not self.arg.value
            v = lattice.sl[self.arg.value]
            if isinstance(v, ConstantLatticeElement):
                return v
            return not v
        if self.type == "int" or self.type == "float":
            assert self.op == "-"
            if isinstance(self.arg, (IntConstantOperand, FloatConstantOperand)):
                return -self.arg.value
            v = lattice.sl[self.arg.value]
            if isinstance(v, ConstantLatticeElement):
                return v
            return -lattice.sl[self.arg.value]

    def place_constants(self, lattice):
        if isinstance(self.arg, IdOperand):
            if self.arg.value in lattice.sl:
                val = lattice.sl[self.arg.value]
                if not isinstance(val, ConstantLatticeElement):
                    if type(val) is int:
                        self.arg = IntConstantOperand(val)
                    elif type(val) is float:
                        self.arg = FloatConstantOperand(val)
                    else:
                        assert type(val) is bool
                        self.arg = BoolConstantOperand(val)
                    return True
        return False

    def is_def(self, op):
        return op.value == self.value

    def remove_versions(self):
        self.value = self.value.split("_")[0]
        if isinstance(self.arg, IdOperand):
            self.arg = IdOperand(self.arg.value.split("_")[0])

    def replace_operand(self, name, new_name):
        if self.arg.value == name:
            self.arg = IdOperand(new_name)

    def replace_tmp(self, version):
        if len(self.value.split("$")) > 1:
            version = version + 1
            new_tmp = "tmp$" + str(version)
            old = self.value
            self.value = new_tmp
            return version, old, new_tmp
        return version, None, None

    def get_low_ir(self, scalar_variables):
        code = []
        reg = scalar_variables[self.value]
        argument_reg = self.arg.get_low_ir(scalar_variables)
        if self.type == "float":
            code.append(MoveSS("xmm0", argument_reg))
            code.append(Sub("esp", "4"))
            code.append(Move("[esp]", "dword 0x80000000"))
            code.append(MoveSS("xmm1", "dword [esp]"))
            code.append(Add("esp", "4"))
            code.append(Xorps("xmm0", "xmm1"))
            code.append(MoveSS(reg, "xmm0"))
        else:
            if reg == argument_reg:
                dword = "" if reg in regs else "dword "
                if self.op == "not":
                    code.append(Not(dword + reg))
                else:
                    code.append(Neg(dword + reg))
            else:
                target = "eax"
                code.append(Move(target, argument_reg))
                if self.op == "not":
                    code.append(Not(target))
                else:
                    code.append(Neg(target))
                code.append(Move(reg, target))
        return code


class BinaryAssign(IR):
    def __init__(self, type, value, op, left, right, left_type, right_type):
        super().__init__()
        self.type = type
        self.value = value
        self.op = op
        self.left = left
        self.right = right
        self.left_type = left_type
        self.right_type = right_type

    def __str__(self):
        d = ""
        return self.type + " " + self.value + d + " <- " + str(self.left) + " " + self.op + " " + str(self.right)

    def rename_operands(self, name, version):
        if isinstance(self.left, IdOperand):
            if self.left.value == name:
                new_op = IdOperand(name + "_" + str(version))
                self.left = new_op

        if isinstance(self.right, IdOperand):
            if self.right.value == name:
                new_op = IdOperand(name + "_" + str(version))
                self.right = new_op

    def get_operands(self):
        return [self.left, self.right]

    def is_use_op(self, value):
        return self.left.value == value or self.right.value == value

    def lat_eval(self, lattice):
        if isinstance(self.left, IntConstantOperand) or isinstance(self.left, BoolConstantOperand) or isinstance(
                self.left, FloatConstantOperand):
            op1 = self.left.value
        else:
            op1 = lattice.sl[self.left.value]

        if isinstance(self.right, IntConstantOperand) or isinstance(self.right, BoolConstantOperand) or isinstance(
                self.right, FloatConstantOperand):
            op2 = self.right.value
        else:
            op2 = lattice.sl[self.right.value]

        if self.op == "*" and (op1 == 0 or op2 == 0):
            return 0

        if self.op == "+":
            # print(op1, op2)
            if op1 == 0:
                return op2
            if op2 == 0:
                return op1

        if isinstance(op1, ConstantLatticeElement):
            if op1 == ConstantLatticeElement.LOW:
                return ConstantLatticeElement.LOW

        if isinstance(op2, ConstantLatticeElement):
            if op2 == ConstantLatticeElement.LOW:
                return ConstantLatticeElement.LOW

        if isinstance(op1, ConstantLatticeElement):
            if op1 == ConstantLatticeElement.HIGH:
                return ConstantLatticeElement.HIGH

        if isinstance(op2, ConstantLatticeElement):
            if op2 == ConstantLatticeElement.HIGH:
                return ConstantLatticeElement.HIGH

        exp = str(op1) + " " + self.op + " " + str(op2)
        # print(exp)
        return eval(exp.replace('div', '//').replace('mod', '%'))

    def place_constants(self, lattice):
        changed = False
        if isinstance(self.left, IdOperand):
            if self.left.value in lattice.sl:
                val = lattice.sl[self.left.value]
                if not isinstance(val, ConstantLatticeElement):
                    if type(val) is int:
                        self.left = IntConstantOperand(val)
                    elif type(val) is float:
                        self.left = FloatConstantOperand(val)
                    else:
                        assert type(val) is bool
                        self.left = BoolConstantOperand(val)
        if isinstance(self.right, IdOperand):
            if self.right.value in lattice.sl:
                val = lattice.sl[self.right.value]
                if not isinstance(val, ConstantLatticeElement):
                    if type(val) is int:
                        self.right = IntConstantOperand(val)
                    elif type(val) is float:
                        self.right = FloatConstantOperand(val)
                    else:
                        assert type(val) is bool
                        self.right = BoolConstantOperand(val)

        return changed

    def is_def(self, op):
        return op.value == self.value

    def remove_versions(self):
        self.value = self.value.split("_")[0]
        if isinstance(self.left, IdOperand):
            self.left = IdOperand(self.left.value.split("_")[0])
        if isinstance(self.right, IdOperand):
            self.right = IdOperand(self.right.value.split("_")[0])

    def simplify(self):
        if self.op == "+":
            if isinstance(self.left, IntConstantOperand) and self.left.value == 0:
                return AtomicAssign(self.type, self.value, self.right, None, None)
            if isinstance(self.right, IntConstantOperand) and self.right.value == 0:
                return AtomicAssign(self.type, self.value, self.left, None, None)

        if self.op == "-":
            if isinstance(self.right, IntConstantOperand) and self.right.value == 0:
                return AtomicAssign(self.type, self.value, self.left, None, None)

        if self.op == "*":
            if isinstance(self.left, IntConstantOperand) and self.left.value == 1:
                return AtomicAssign(self.type, self.value, self.right, None, None)
            if isinstance(self.right, IntConstantOperand) and self.right.value == 1:
                return AtomicAssign(self.type, self.value, self.left, None, None)

        if self.op == "div" or self.op == "mod":
            if isinstance(self.right, IntConstantOperand) and self.right.value == 0:
                raise ArithmeticError("В вашей программе обнаружено деление на 0")

        if self.op == "and":
            if isinstance(self.left, BoolConstantOperand):
                if not self.left.value:
                    return AtomicAssign(self.type, self.value, BoolConstantOperand(False), None, None)
                else:
                    return AtomicAssign(self.type, self.value, self.right, None, None)
            if isinstance(self.right, BoolConstantOperand):
                if not self.right.value:
                    return AtomicAssign(self.type, self.value, BoolConstantOperand(False), None, None)
                else:
                    return AtomicAssign(self.type, self.value, self.left, None, None)

        if self.op == "or":
            if isinstance(self.left, BoolConstantOperand):
                if not self.left.value:
                    return AtomicAssign(self.type, self.value, self.right, None, None)
                else:
                    return AtomicAssign(self.type, self.value, BoolConstantOperand(True), None, None)
            if isinstance(self.right, BoolConstantOperand):
                if not self.right.value:
                    return AtomicAssign(self.type, self.value, self.left, None, None)
                else:
                    return AtomicAssign(self.type, self.value, self.left, None, None)
        return self

    def is_cmp(self):
        return self.op == ">" or self.op == "<" or self.op == "==" or self.op == "!=" or self.op == ">=" or self.op == "<="

    def replace_operand(self, name, new_name):
        if self.left.value == name:
            self.left = IdOperand(new_name)
        if self.right.value == name:
            self.right = IdOperand(new_name)

    def replace_tmp(self, version):
        if len(self.value.split("$")) > 1:
            version = version + 1
            new_tmp = "tmp$" + str(version)
            old = self.value
            self.value = new_tmp
            return version, old, new_tmp
        return version, None, None

    def get_low_ir_cmp(self, scalar_variables):
        code = []
        if isinstance(self.left, (IntConstantOperand, FloatConstantOperand)):
            self.left, self.right = self.right, self.left
            self.left_type, self.right_type = self.right_type, self.left_type
            self.op = revert_cmp_op(self.op)
        left_reg = self.left.get_low_ir(scalar_variables)
        right_reg = self.right.get_low_ir(scalar_variables)
        dw = ""
        if left_reg not in regs and isinstance(self.right, (IntConstantOperand, FloatConstantOperand)):
            dw = " dword "
        if self.left_type == "int" and self.right_type == "int":
            code.append(Cmp(left_reg, dw + right_reg))
        else:
            left_cmp = "xmm0"
            right_cmp = "xmm1"
            if self.left_type == "int":
                if left_reg in regs or (left_reg[0] == "[" and left_reg[-1] == "]"):
                    code.append(Cvtsi2ss("xmm0", left_reg))
                else:
                    code.append(Sub("esp", "4"))
                    code.append(Move("dword [esp]", left_reg))
                    code.append(MoveSS("xmm0", "[esp]"))
                    code.append(Add("esp", "4"))
            else:
                left_cmp = left_reg
            if self.right_type == "int":
                if right_reg in regs or (right_reg[0] == "[" and right_reg[-1] == "]"):
                    code.append(Cvtsi2ss("xmm1", right_reg))
                else:
                    code.append(Sub("esp", "4"))
                    code.append(Move("dword [esp]", right_reg))
                    code.append(MoveSS("xmm1", "[esp]"))
                    code.append(Add("esp", "4"))
            else:
                right_cmp = right_reg
            code.append(Comiss(left_cmp, right_cmp))
        return code, self.op

    def get_low_ir(self, scalar_variables):
        if isinstance(self.left, (IntConstantOperand, FloatConstantOperand)) and self.is_cmp():
            self.left, self.right = self.right, self.left
            self.left_type, self.right_type = self.right_type, self.left_type
            self.op = revert_cmp_op(self.op)
        code = []
        reg = scalar_variables[self.value]
        if self.type == "float":
            if self.op in ["+", "*"] and isinstance(self.left, (FloatConstantOperand, IntConstantOperand)):
                self.left, self.right = self.right, self.left
                self.left_type, self.right_type = self.right_type, self.left_type
            left_reg = self.left.get_low_ir(scalar_variables)
            right_reg = self.right.get_low_ir(scalar_variables)
            overwrite = False
            if left_reg in xmm_regs and left_reg == reg:
                overwrite = True
            right_arg = "xmm1" if right_reg not in xmm_regs else right_reg

            if self.op == "/" and isinstance(self.left,
                                             (IntConstantOperand, FloatConstantOperand)) and self.left.value == 1:
                if right_reg not in xmm_regs:
                    if right_reg in regs or (
                            (right_reg[0] == "[" and right_reg[-1] == "]") and self.right_type == "int"):
                        code.append(Cvtsi2ss("xmm1", right_reg))
                    else:
                        code.append(Sub("esp", "4"))
                        code.append(Move("dword [esp]", right_reg))
                        code.append(MoveSS("xmm1", "[esp]"))
                        code.append(Add("esp", "4"))
                    if reg in xmm_regs:
                        code.append(RCPSS(reg, "xmm1"))
                    else:
                        code.append(RCPSS("xmm0", "xmm1"))
                        code.append(MoveSS(reg, "xmm0"))
                else:
                    if reg in xmm_regs:
                        code.append(RCPSS(reg, right_reg))
                    else:
                        code.append(RCPSS("xmm0", right_reg))
                        code.append(MoveSS(reg, "xmm0"))
                return code

            if left_reg not in xmm_regs:
                if left_reg in regs or (
                        (left_reg[0] == "[" and left_reg[-1] == "]") and self.left_type == "int"):
                    code.append(Cvtsi2ss("xmm0", left_reg))
                else:
                    code.append(Sub("esp", "4"))
                    code.append(Move("dword [esp]", left_reg))
                    code.append(MoveSS("xmm0", "[esp]"))
                    code.append(Add("esp", "4"))
            else:
                if not overwrite:
                    code.append(MoveSS("xmm0", left_reg))
            if right_reg not in xmm_regs:
                if right_reg in regs or (
                        (right_reg[0] == "[" and right_reg[-1] == "]") and self.right_type == "int"):
                    code.append(Cvtsi2ss("xmm1", right_reg))
                else:
                    code.append(Sub("esp", "4"))
                    code.append(Move("dword [esp]", right_reg))
                    if self.right_type == "int":
                        code.append(Cvtsi2ss("xmm1", "[esp]"))
                    else:
                        code.append(MoveSS("xmm1", "[esp]"))
                    code.append(Add("esp", "4"))
            else:
                if right_arg == "xmm1":
                    code.append(MoveSS("xmm1", right_reg))
            if not overwrite:
                left_reg = "xmm0"
            if self.op == "+":
                code.append(Addss(left_reg, right_arg))
            if self.op == "-":
                code.append(Subss(left_reg, right_arg))
            if self.op == "*":
                code.append(Mulss(left_reg, right_arg))
            if self.op == "/":
                code.append(Divss(left_reg, right_arg))
            if not overwrite:
                code.append(MoveSS(reg, "xmm0"))
        else:
            left_reg = self.left.get_low_ir(scalar_variables)
            is_overwrite = False
            if left_reg in regs and left_reg == reg:
                is_overwrite = True
            right_reg = self.right.get_low_ir(scalar_variables)
            if right_reg == "1" and is_overwrite:
                if self.op == "+":
                    code.append(Inc(left_reg))
                if self.op == "-":
                    code.append(Dec(left_reg))
                return code
            if self.op not in ["div", "mod"] and not self.is_cmp():
                left_arg = "eax"
                if is_overwrite:
                    left_arg = left_reg
                else:
                    code.append(Move("eax", left_reg))
                if self.op == "+":
                    code.append(Add(left_arg, right_reg))
                if self.op == "-":
                    code.append(Sub(left_arg, right_reg))
                if self.op == "*":
                    code.append(Imul(left_arg, right_reg))
                if self.op == "and":
                    code.append(And(left_arg, right_reg))
                if self.op == "or":
                    code.append(Or(left_arg, right_reg))
                if not is_overwrite:
                    code.append(Move(reg, "eax"))
            elif not self.is_cmp():
                if reg != "edx" and "edx" in self.used_regs:
                    code.append(Push("edx"))
                pushable = False
                code.append(Move("eax", left_reg))
                if right_reg == "edx":
                    right_reg = get_reg([reg, left_reg])
                    if right_reg not in self.used_regs:
                        code.append(Push(right_reg))
                        pushable = True
                if isinstance(self.right, IntConstantOperand):
                    old = right_reg
                    right_reg = get_reg([reg, left_reg])
                    code.append(Move(right_reg, old))
                    if right_reg not in self.used_regs:
                        code.append(Push(right_reg))
                        pushable = True
                code.append(Xor("edx", "edx"))
                code.append(Idiv(right_reg))
                if self.op == "div":
                    code.append(Move(reg, "eax"))
                else:
                    code.append(Move(reg, "edx"))
                if pushable:
                    code.append(Pop(right_reg))
                if reg != "edx" and "edx" in self.used_regs:
                    code.append(Pop("edx"))
            if self.is_cmp():
                dw = ""
                if left_reg not in regs and isinstance(self.right, (IntConstantOperand, FloatConstantOperand)):
                    dw = " dword "
                if self.left_type == "int" and self.right_type == "int":
                    code.append(Cmp(left_reg, dw + right_reg))
                else:
                    left_arg = "xmm0"
                    right_arg = 'xmm1'
                    if self.left_type == "int":
                        if left_reg in regs or (left_reg[0] == "[" and left_reg[-1] == "]"):
                            code.append(Cvtsi2ss("xmm0", left_reg))
                        else:
                            code.append(Sub("esp", "4"))
                            code.append(Move("dword [esp]", left_reg))
                            code.append(MoveSS("xmm0", "[esp]"))
                            code.append(Add("esp", "4"))
                    else:
                        if left_reg in xmm_regs:
                            left_arg = left_reg
                        else:
                            code.append(MoveSS("xmm0", left_reg))
                    if self.right_type == "int":
                        if right_reg in regs or (right_reg[0] == "[" and right_reg[-1] == "]"):
                            code.append(Cvtsi2ss("xmm1", right_reg))
                        else:
                            code.append(Sub("esp", "4"))
                            code.append(Move("dword [esp]", right_reg))
                            code.append(MoveSS("xmm1", "[esp]"))
                            code.append(Add("esp", "4"))
                    else:
                        if right_reg in xmm_regs:
                            right_arg = right_reg
                        else:
                            code.append(MoveSS("xmm1", right_reg))
                    code.append(Comiss(left_arg, right_arg))
                code.append(get_set_cmp(self.op))
                code.append(MoveZX("eax", "al"))
                code.append(Move(reg, "eax"))
        return code


class PhiAssign(IR):
    def __init__(self, type, value, arguments):
        super().__init__()
        self.type = type
        self.value = value
        self.arguments = arguments
        self.dimentions = None

    def __str__(self):
        s = self.type + " " + self.value + " <- PHI("
        for i, arg in enumerate(self.arguments):
            s += str(arg)
            if i != len(self.arguments) - 1:
                s += ', '
        s += ")"
        return s

    def get_operands(self):
        return self.arguments

    def place_constants(self, lattice):
        # changed = False
        # for i, arg in enumerate(self.arguments):
        #    if isinstance(arg, IdOperand):
        #        if arg in lattice.sl:
        #            val = lattice.sl[arg.value]
        #            if not isinstance(val, ConstantLatticeElement):
        #                if type(val) is int:
        #                    self.arguments[i] = IntConstantOperand(val)
        #                else:
        #                    assert type(val) is bool
        #                    self.arguments[i] = BoolConstantOperand(val)
        #                changed = True
        # return changed
        return False

    def is_def(self, op):
        return op.value == self.value

    def operand_number(self, op):
        for i, arg in enumerate(self.arguments):
            if arg.value == op:
                return i
        return -1

    def is_use_op(self, op):
        for arg in self.arguments:
            if arg.value == op:
                return True
        return False

    def is_use_op_for_label(self, op, i):
        return self.arguments[i].value == op

    def replace_operand(self, name, new_name):
        # new_args = []
        # for arg in self.arguments:
        #    if arg.value == name:
        #        new_args.append(IdOperand(new_name))
        #    else:
        #        new_args.append(arg)
        # self.arguments = new_args
        pass


class ReturnInstruction(IR):
    def __init__(self, value):
        super().__init__()
        self.value = value

    def __str__(self):
        return "ret " + str(self.value)

    def rename_operands(self, name, version):
        if isinstance(self.value, IdOperand) and self.value.value == name:
            self.value = IdOperand(self.value.value + "_" + str(version))

    def is_use_op(self, value):
        return self.value.value == value

    def lat_eval(self, lattice):
        return lattice.sl[self.value.value]

    def place_constants(self, lattice):
        if isinstance(self.value, IdOperand):
            if self.value.value in lattice.sl:
                val = lattice.sl[self.value.value]
                if not isinstance(val, ConstantLatticeElement):
                    if type(val) is int:
                        self.value = IntConstantOperand(val)
                    elif type(val) is float:
                        self.value = FloatConstantOperand(val)
                    else:
                        assert type(val) is bool
                        self.value = BoolConstantOperand(val)
                    return True
        return False

    def get_operands(self):
        return [self.value]

    def remove_versions(self):
        if isinstance(self.value, IdOperand):
            self.value = IdOperand(self.value.value.split("_")[0])

    def replace_operand(self, name, new_name):
        if self.value.value == name:
            self.value = IdOperand(new_name)

    def replace_tmp(self, version):
        return version, None, None

    def get_low_ir_return(self, scalar_variables, is_entry, type, used_xmm):
        code = []
        if is_entry:
            code.append(Move("eax", "0x01"))
            code.append(Xor("ebx", "ebx"))
            code.append("int 0x80")
        else:
            argument_reg = self.value.get_low_ir(scalar_variables)
            if type == "float":
                if argument_reg in xmm_regs:
                    code.append(Sub("esp", "4"))
                    code.append(MoveSS("dword [esp]", argument_reg))
                    code.append(Fld("dword [esp]"))
                    code.append(Add("esp", "4"))
                else:
                    code.append(Fld("dword " + argument_reg))
            else:
                code.append(Move("eax", argument_reg))
            for xmm in used_xmm[::-1]:
                code.append(MoveDQU(xmm, "[esp]"))
                code.append(Add("esp", "16"))
            code.append(Pop("esi"))
            code.append(Pop("edi"))
            code.append(Pop("ebx"))
            code.append(Move("esp", "ebp"))
            code.append(Pop("ebp"))
            code.append(Return())
        return code


class IsTrueInstruction(IR):
    def __init__(self, value):
        super().__init__()
        self.value = value

    def __str__(self):
        return "br_if_true " + str(self.value)

    def rename_operands(self, name, version):
        if isinstance(self.value, IdOperand) and self.value.value == name:
            print(name)
            self.value = IdOperand(self.value.value + "_" + version)

    def is_use_op(self, value):
        return self.value.value == value

    def lat_eval(self, lattice):
        return lattice.sl[self.value.value]

    def place_constants(self, lattice):
        if isinstance(self.value, IdOperand):
            if self.value.value in lattice.sl:
                val = lattice.sl[self.value.value]
                if not isinstance(val, ConstantLatticeElement):
                    if type(val) is int:
                        self.value = IntConstantOperand(val)
                    elif type(val) is float:
                        self.value = FloatConstantOperand(val)
                    else:
                        assert type(val) is bool
                        self.value = BoolConstantOperand(val)
                    return True
        return False

    def get_operands(self):
        return [self.value]

    def remove_versions(self):
        if isinstance(self.value, IdOperand):
            self.value = IdOperand(self.value.value.split("_")[0])

    def replace_operand(self, name, new_name):
        if self.value.value == name:
            self.value = IdOperand(new_name)

    def replace_tmp(self, version):
        return version, None, None

    def get_jump(self, compared, out):
        if compared == "==":
            return JumpEqual(out)
        if compared == "!=":
            return JumpNotEqual(out)
        if compared == ">":
            return JumpGreater(out)
        if compared == "<":
            return JumpLess(out)
        if compared == ">=":
            return JumpGreaterEqual(out)
        if compared == "<=":
            return JumpLessEqual(out)

    def get_low_ir_branch(self, scalar_variables, output_vertexes, phi_assigns, compared):
        code = []
        if compared is not None:
            code += phi_assigns
            code.append(self.get_jump(compared, output_vertexes[0].label))
            code.append(Jump(output_vertexes[1].label))
        else:
            argument_reg = self.value.get_low_ir(scalar_variables)
            code.append(Cmp(argument_reg, "1"))
            code += phi_assigns
            code.append(JumpEqual(output_vertexes[0].label))
            code.append(Jump(output_vertexes[1].label))
        return code
