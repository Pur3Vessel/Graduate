from operands import *


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
    pass


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


class AtomicAssign(IR):
    def __init__(self, type, value, argument, dimentions):
        self.type = type
        self.value = value
        self.argument = argument
        self.dimentions = dimentions

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

    def get_operands(self):
        if isinstance(self.argument, FuncCallOperand):
            return self.argument.get_operands()
        if isinstance(self.argument, ArrayUseOperand):
            return self.argument.get_operands()
        return [self.argument]

    def is_use_op(self, value):
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
        return False

    def is_def(self, op):
        return op.value == self.value

    def remove_versions(self):
        self.value = self.value.split("_")[0]
        if isinstance(self.argument, FuncCallOperand) or isinstance(self.argument, ArrayUseOperand):
            self.argument.remove_versions()
        if isinstance(self.argument, IdOperand):
            self.argument = IdOperand(self.argument.value.split("_")[0])


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


class PhiAssign(IR):
    def __init__(self, value, arguments):
        self.value = value
        self.arguments = arguments
        self.dimentions = None

    def __str__(self):
        s = self.value + " <- PHI("
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


class ReturnInstruction(IR):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return "ret " + str(self.value)

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
