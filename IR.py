from operands import *
import functools
import struct


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


def is_cmp_op(op):
    return op == "==" or op == "!=" or op == ">" or op == "<" or op == ">=" or op == "<="


def float_to_ieee_754_hex(num):
    ieee_754_bytes = struct.pack('>f', num)
    ieee_754_hex = '0x' + ''.join(f'{byte:02x}' for byte in ieee_754_bytes)
    return ieee_754_hex


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
    def get_low_ir(self, scalar_variables):
        return []


class NullInstruction(IR):
    def __str__(self):
        return "null instruction"


class FuncDefInstruction(IR):
    def __init__(self, type, name, arguments):
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
            adress = array_adresses[self.name][0].replace("[", "").replace("]", "")
            for i in range(n_elems):
                if self.type == "float":
                    code.append(MoveSS("[" + adress + " + " + str(sdvig) + "]", str(0)))
                else:
                    code.append(Move("[" + adress + " + " + str(sdvig) + "]", str(0)))
                sdvig += 4
        else:
            elems = flatten(self.assign)
            adress = array_adresses[self.name][0].replace("[", "").replace("]", "")
            for i in range(n_elems):
                if self.type == "float":
                    code.append(
                        MoveSS("[" + adress + " + " + str(sdvig) + "]", "dword " + float_to_ieee_754_hex(elems[i])))
                else:
                    code.append(Move("[" + adress + " + " + str(sdvig) + "]", "dword " + str(elems[i])))
                sdvig += 4
        return code


class AtomicAssign(IR):
    def __init__(self, type, value, argument, dimentions):
        self.type = type
        self.value = value
        self.argument = argument
        self.dimentions = dimentions
        self.is_phi = False

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
                self.argument = IdOperand(name)
            if self.dimentions is not None:
                new_dims = []
                for d in self.dimentions:
                    if d.value == name:
                        new_dims.append(IdOperand(new_name))
                    else:
                        new_dims.append(d)
                self.dimentions = new_dims

    def get_low_ir_arr(self, scalar_variables, array_adresses):
        code = []
        if self.dimentions is None:
            reg = scalar_variables[self.value]
            if reg == "spilled":
                reg = "Место в памяти для " + self.value
            if isinstance(self.argument, (IntConstantOperand, BoolConstantOperand, FloatConstantOperand, IdOperand)):
                argument_reg = self.argument.get_low_ir(scalar_variables)
                if self.type == "float":
                    code.append(MoveSS(reg, argument_reg))
                else:
                    code.append(Move(reg, argument_reg))
            if isinstance(self.argument, FuncCallOperand):
                code.append(Push("ecx"))
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
                code.append(Pop("edx"))
                code.append(Pop("ecx"))
            if isinstance(self.argument, ArrayUseOperand):
                reg = scalar_variables[self.value]
                arr_code, src, pop_intr = generate_array_index_code(self.argument.name, self.argument.indexing,
                                                                    scalar_variables, array_adresses, [reg])
                code += arr_code
                if self.type == "float":
                    code.append(MoveSS(reg, src))
                else:
                    code.append(Move(reg, src))
                code += pop_intr
            return code
        else:
            reg = self.argument.get_low_ir(scalar_variables)
            arr_code, src, pop_intr = generate_array_index_code(self.value, self.dimentions,
                                                                scalar_variables, array_adresses, [reg])
            code += arr_code
            if self.type == "float":
                code.append(MoveSS(src, reg))
            else:
                code.append(Move(src, reg))
            code += pop_intr
            return code


class UnaryAssign(IR):
    def __init__(self, type, value, op, argument, dimentions):
        self.type = type
        self.value = value
        self.op = op
        self.arg = argument
        self.dimentions = dimentions

    def __str__(self):
        d = ""
        if self.dimentions is not None:
            d = "["
            d += ", ".join(str(dim) for dim in self.dimentions)
            d += "]"
        return self.type + " " + self.value + d + " <- " + self.op + " " + str(self.arg)

    def rename_operands(self, name, version):
        if isinstance(self.arg, IdOperand):
            if self.arg.value == name:
                new_op = IdOperand(name + "_" + str(version))
                self.arg = new_op

    def get_operands(self):
        return [self.arg]

    def is_use_op(self, value):
        if self.dimentions is not None:
            for d in self.dimentions:
                if d.value == value:
                    return True
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
        if isinstance(self.arg, IdOperand):
            self.arg = IdOperand(self.arg.value.split("_")[0])

    def replace_operand(self, name, new_name):
        if self.dimentions is not None:
            new_dims = []
            for d in self.dimentions:
                if d == name:
                    new_dims.append(IdOperand(new_name))
                else:
                    new_dims.append(d)
            self.dimentions = new_dims
        if self.arg.value == name:
            self.arg = IdOperand(new_name)

    def get_low_ir(self, scalar_variables):
        code = []
        if self.dimentions is None:
            reg = scalar_variables[self.value]
            if reg == "spilled":
                reg = "Место в памяти для " + self.value
            argument_reg = self.arg.get_low_ir(scalar_variables)
            if self.type == "float":
                code.append(MoveSS("xmm0", argument_reg))
                code.append(MoveSS("xmm1", "0x80000000"))
                code.append(Xorps("xmm0", "xmm1"))
                code.append(MoveSS(reg, "xmm0"))
            else:
                if self.op == "not":
                    code.append(Move("eax", argument_reg))
                    code.append(Not("eax"))
                    code.append(Move(reg, "eax"))
                if self.op == "-":
                    code.append(Move("eax", argument_reg))
                    code.append(Neg("eax"))
                    code.append(Move(reg, "eax"))
            return code


class BinaryAssign(IR):
    def __init__(self, type, value, op, left, right, dimentions):
        self.type = type
        self.value = value
        self.op = op
        self.left = left
        self.right = right
        self.dimentions = dimentions

    def __str__(self):
        d = ""
        if self.dimentions is not None:
            d = "["
            d += ", ".join(str(dim) for dim in self.dimentions)
            d += "]"
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
        if self.dimentions is not None:
            for d in self.dimentions:
                if d.value == value:
                    return True
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
        return eval(exp)

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

        if self.dimentions is not None:
            for i, d in enumerate(self.dimentions):
                if d.value in lattice.sl:
                    val = lattice.sl[d.value]
                    if not isinstance(val, ConstantLatticeElement):
                        if type(val) is int:
                            self.dimentions[i] = IntConstantOperand(val)
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
                return AtomicAssign(self.type, self.value, self.right, self.dimentions)
            if isinstance(self.right, IntConstantOperand) and self.right.value == 0:
                return AtomicAssign(self.type, self.value, self.left, self.dimentions)

        if self.op == "-":
            if isinstance(self.right, IntConstantOperand) and self.right.value == 0:
                return AtomicAssign(self.type, self.value, self.left, self.dimentions)

        if self.op == "div" or self.op == "mod":
            if isinstance(self.right, IntConstantOperand) and self.right.value == 0:
                raise ArithmeticError("В вашей программе обнаружено деление на 0")

        if self.op == "and":
            if isinstance(self.left, BoolConstantOperand):
                if not self.left.value:
                    return AtomicAssign(self.type, self.value, BoolConstantOperand(False), self.dimentions)
                else:
                    return AtomicAssign(self.type, self.value, self.right, self.dimentions)
            if isinstance(self.right, BoolConstantOperand):
                if not self.right.value:
                    return AtomicAssign(self.type, self.value, BoolConstantOperand(False), self.dimentions)
                else:
                    return AtomicAssign(self.type, self.value, self.left, self.dimentions)

        if self.op == "or":
            if isinstance(self.left, BoolConstantOperand):
                if not self.left.value:
                    return AtomicAssign(self.type, self.value, self.right, self.dimentions)
                else:
                    return AtomicAssign(self.type, self.value, BoolConstantOperand(True), self.dimentions)
            if isinstance(self.right, BoolConstantOperand):
                if not self.right.value:
                    return AtomicAssign(self.type, self.value, self.left, self.dimentions)
                else:
                    return AtomicAssign(self.type, self.value, self.left, self.dimentions)
        return self

    def is_cmp(self):
        return self.op == ">" or self.op == "<" or self.op == "==" or self.op == "!=" or self.op == ">=" or self.op == "<="

    def replace_operand(self, name, new_name):
        if self.left.value == name:
            self.left = IdOperand(new_name)
        if self.right.value == name:
            self.right = IdOperand(new_name)
        if self.dimentions is not None:
            new_dims = []
            for d in self.dimentions:
                print(d, name, new_name)
                if d.value == name:
                    new_dims.append(IdOperand(new_name))
                else:
                    new_dims.append(d)
            self.dimentions = new_dims

    def get_low_ir(self, scalar_variables):
        if isinstance(self.left, (IntConstantOperand, FloatConstantOperand)) and self.is_cmp():
            self.left, self.right = self.right, self.left
            self.op = revert_cmp_op(self.op)
        code = []
        if self.dimentions is None:
            reg = scalar_variables[self.value]
            if reg == "spilled":
                reg = "Место в памяти для " + self.value
            left_reg = self.left.get_low_ir(scalar_variables)
            right_reg = self.right.get_low_ir(scalar_variables)
            dw = ""
            if self.is_cmp() and left_reg not in reg and isinstance(self.right, (IntConstantOperand, FloatConstantOperand)):
                dw = " dword "

            if self.type == "float":
                if self.op == "+":
                    code.append(MoveSS("xmm0", left_reg))
                    code.append(MoveSS("xmm1", right_reg))
                    code.append(Addss("xmm0", "xmm1"))
                    code.append(MoveSS(reg, "xmm0"))
                if self.op == "-":
                    code.append(MoveSS("xmm0", left_reg))
                    code.append(MoveSS("xmm1", right_reg))
                    code.append(Subss("xmm0", "xmm1"))
                    code.append(MoveSS(reg, "xmm0"))
                if self.op == "*":
                    code.append(MoveSS("xmm0", left_reg))
                    code.append(MoveSS("xmm1", right_reg))
                    code.append(Mulss("xmm0", "xmm1"))
                    code.append(MoveSS(reg, "xmm0"))
                if self.op == "/":
                    code.append(MoveSS("xmm0", left_reg))
                    code.append(MoveSS("xmm1", right_reg))
                    code.append(Divss("xmm0", "xmm1"))
                    code.append(MoveSS(reg, "xmm0"))
            else:
                if self.op == "and":
                    code.append(Move("eax", left_reg))
                    code.append(And("eax", right_reg))
                    code.append(Move(reg, "eax"))
                if self.op == "or":
                    code.append(Move("eax", left_reg))
                    code.append(Or("eax", right_reg))
                    code.append(Move(reg, "eax"))
                if self.op == "+":
                    code.append(Move("eax", left_reg))
                    code.append(Add("eax", right_reg))
                    code.append(Move(reg, "eax"))
                if self.op == "-":
                    code.append(Move("eax", left_reg))
                    code.append(Sub("eax", right_reg))
                    code.append(Move(reg, "eax"))
                if self.op == "*":
                    code.append(Move("eax", left_reg))
                    code.append(Imul("eax", right_reg))
                    code.append(Move(reg, "eax"))
                if self.op == "div":
                    code.add("Заглушка на div")
                if self.op == "mod":
                    code.add("Заглушка на mod")
                if self.op == ">":
                    code.append(Cmp(left_reg, dw + right_reg))
                    code.append(Setg("al"))
                    code.append(MoveZX("eax", "al"))
                    code.append(Move(reg, "eax"))
                if self.op == ">=":
                    code.append(Cmp(left_reg, dw + right_reg))
                    code.append(Setge("al"))
                    code.append(MoveZX("eax", "al"))
                    code.append(Move(reg, "eax"))
                if self.op == "<=":
                    code.append(Cmp(left_reg, dw + right_reg))
                    code.append(Setle("al"))
                    code.append(MoveZX("eax", "al"))
                    code.append(Move(reg, "eax"))
                if self.op == "==":
                    code.append(Cmp(left_reg, dw + right_reg))
                    code.append(Sete("al"))
                    code.append(MoveZX("eax", "al"))
                    code.append(Move(reg, "eax"))
                if self.op == "<":
                    code.append(Cmp(left_reg, dw + right_reg))
                    code.append(Setl("al"))
                    code.append(MoveZX("eax", "al"))
                    code.append(Move(reg, "eax"))
                if self.op == "!=":
                    code.append(Cmp(left_reg, dw + right_reg))
                    code.append(Setne("al"))
                    code.append(MoveZX("eax", "al"))
                    code.append(Move(reg, "eax"))
            return code


class PhiAssign(IR):
    def __init__(self, type, value, arguments):
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
        self.value = IdOperand(new_name)

    def get_low_ir_return(self, scalar_variables, is_entry, type):
        code = []
        if is_entry:
            code.append(Move("eax", "0x01"))
            code.append(Xor("ebx", "ebx"))
            code.append("int 0x80")
        else:
            argument_reg = self.value.get_low_ir(scalar_variables)
            if type == "float":
                code.append(Fld("dword " + argument_reg))
            else:
                code.append(Move("eax", argument_reg))
            code.append(Pop("esi"))
            code.append(Pop("edi"))
            code.append(Pop("ebx"))
            code.append(Move("esp", "ebp"))
            code.append(Pop("ebp"))
            code.append(Return())
        return code


class IsTrueInstruction(IR):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return "br_if_true " + str(self.value)

    def rename_operands(self, name, version):
        if isinstance(self.value, IdOperand) and self.value.value == name:
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
        self.value = IdOperand(new_name)

    def get_low_ir_branch(self, scalar_variables, output_vertexes, phi_assigns):
        code = []
        argument_reg = self.value.get_low_ir(scalar_variables)
        code.append(Cmp(argument_reg, "1"))
        code += phi_assigns
        code.append(JumpEqual(output_vertexes[0].label))
        code.append(Jump(output_vertexes[1].label))
        return code
