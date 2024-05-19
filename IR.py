from abc import ABC
from lattice import *


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


class Operand(ABC):
    pass


class IdOperand(Operand):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value


class IntConstantOperand(Operand):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class BoolConstantOperand(Operand):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


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
                        else:
                            assert type(val) is bool
                            self.args[i] = BoolConstantOperand(val)
                        changed = True
        return changed

    def remove_versions(self):
        for i, arg in enumerate(self.args):
            if isinstance(arg, IdOperand):
                self.args[i] = IdOperand(arg.value.split("_")[0])


class FuncArgOperand(Operand):
    def __init__(self, type, name):
        self.type = type
        self.name = name

    def __str__(self):
        return self.type + " " + self.name


class IR(ABC):
    pass


class NullInstruction(IR):
    def __str__(self):
        return "null instruction"


class FuncCallInstruction(IR):
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

    def __str__(self):
        s = "CALL VOID " + self.name + "("
        for i, arg in enumerate(self.arguments):
            s += str(arg)
            if i != len(self.arguments) - 1:
                s += ", "
        s += ")"
        return s

    def rename_operands(self, name, version):
        pass

    def is_use_op(self, value):
        is_use = False
        for arg in self.arguments:
            is_use = is_use or value == arg.value
        return is_use

    def place_constants(self, lattice):
        changed = False
        for i, arg in enumerate(self.arguments):
            if isinstance(arg, IdOperand):
                if arg.value in lattice.sl:
                    val = lattice.sl[arg.value]
                    if not isinstance(val, ConstantLatticeElement):
                        if type(val) is int:
                            self.arguments[i] = IntConstantOperand(val)
                        else:
                            assert type(val) is bool
                            self.arguments[i] = BoolConstantOperand(val)
                        changed = True
        return changed

    def get_operands(self):
        return self.arguments

    def remove_versions(self):
        for i, arg in enumerate(self.arguments):
            if isinstance(arg, IdOperand):
                self.arguments[i] = IdOperand(arg.value.split("_")[0])


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


class AtomicAssign(IR):
    def __init__(self, type, value, argument):
        self.type = type
        self.value = value
        self.argument = argument

    def __str__(self):
        return self.type + " " + self.value + " <- " + str(self.argument)

    def rename_operands(self, name, version):
        if isinstance(self.argument, IdOperand):
            if self.argument.value == name:
                new_op = IdOperand(name + "_" + str(version))
                self.argument = new_op

    def get_operands(self):
        if isinstance(self.argument, FuncCallOperand):
            return self.argument.get_operands()
        return [self.argument]

    def is_use_op(self, value):
        if isinstance(self.argument, IntConstantOperand) or isinstance(self.argument, BoolConstantOperand):
            return False
        if isinstance(self.argument, FuncCallOperand):
            return self.argument.is_use_op(value)
        return self.argument.value == value

    def lat_eval(self, lattice):
        if isinstance(self.argument, FuncCallOperand):
            return ConstantLatticeElement.LOW
        if isinstance(self.argument, IntConstantOperand) or isinstance(self.argument, BoolConstantOperand):
            return self.argument.value
        if self.argument.value not in lattice.sl:
            return ConstantLatticeElement.LOW
        return lattice.sl[self.argument.value]

    def place_constants(self, lattice):
        if isinstance(self.argument, FuncCallOperand):
            return self.argument.place_constants(lattice)

        if isinstance(self.argument, IdOperand):
            if self.argument.value in lattice.sl:
                val = lattice.sl[self.argument.value]
                if not isinstance(val, ConstantLatticeElement):
                    if type(val) is int:
                        self.argument = IntConstantOperand(val)
                    else:
                        assert type(val) is bool
                        self.argument = BoolConstantOperand(val)
                    return True
        return False

    def is_def(self, op):
        return op.value == self.value

    def remove_versions(self):
        self.value = self.value.split("_")[0]
        if isinstance(self.argument, FuncCallOperand):
            self.argument.remove_versions()
        if isinstance(self.argument, IdOperand):
            self.argument = IdOperand(self.argument.value.split("_")[0])


class UnaryAssign(IR):
    def __init__(self, type, value, op, argument):
        self.type = type
        self.value = value
        self.op = op
        self.arg = argument

    def __str__(self):
        return self.type + " " + self.value + " <- " + self.op + " " + str(self.arg)

    def rename_operands(self, name, version):
        pass

    def get_operands(self):
        return [self.arg]

    def is_use_op(self, value):
        if isinstance(self.arg, (IntConstantOperand, BoolConstantOperand)):
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
        if self.type == "int":
            assert self.op == "-"
            if isinstance(self.arg, IntConstantOperand):
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
    def __init__(self, type, value, op, left, right):
        self.type = type
        self.value = value
        self.op = op
        self.left = left
        self.right = right

    def __str__(self):
        return self.type + " " + self.value + " <- " + str(self.left) + " " + self.op + " " + str(self.right)

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
        if isinstance(self.left, IntConstantOperand) or isinstance(self.left, BoolConstantOperand):
            op1 = self.left.value
        else:
            op1 = lattice.sl[self.left.value]

        if isinstance(self.right, IntConstantOperand) or isinstance(self.right, BoolConstantOperand):
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
                    else:
                        assert type(val) is bool
                        self.left = BoolConstantOperand(val)
        if isinstance(self.right, IdOperand):
            if self.right.value in lattice.sl:
                val = lattice.sl[self.right.value]
                if not isinstance(val, ConstantLatticeElement):
                    if type(val) is int:
                        self.right = IntConstantOperand(val)
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
                return AtomicAssign(self.type, self.value, self.right)
            if isinstance(self.right, IntConstantOperand) and self.right.value == 0:
                return AtomicAssign(self.type, self.value, self.left)

        if self.op == "-":
            if isinstance(self.right, IntConstantOperand) and self.right.value == 0:
                return AtomicAssign(self.type, self.value, self.left)

        if self.op == "div" or self.op == "mod":
            if isinstance(self.right, IntConstantOperand) and self.right.value == 0:
                raise ArithmeticError("В вашей программе обнаружено деление на 0")

        if self.op == "and":
            if isinstance(self.left, BoolConstantOperand):
                if not self.left.value:
                    return AtomicAssign(self.type, self.value, BoolConstantOperand(False))
                else:
                    return AtomicAssign(self.type, self.value, self.right)
            if isinstance(self.right, BoolConstantOperand):
                if not self.right.value:
                    return AtomicAssign(self.type, self.value, BoolConstantOperand(False))
                else:
                    return AtomicAssign(self.type, self.value, self.left)

        if self.op == "or":
            if isinstance(self.left, BoolConstantOperand):
                if not self.left.value:
                    return AtomicAssign(self.type, self.value, self.right)
                else:
                    return AtomicAssign(self.type, self.value, BoolConstantOperand(True))
            if isinstance(self.right, BoolConstantOperand):
                if not self.right.value:
                    return AtomicAssign(self.type, self.value, self.left)
                else:
                    return AtomicAssign(self.type, self.value, self.left)
        return self


class PhiAssign(IR):
    def __init__(self, value, arguments):
        self.value = value
        self.arguments = arguments

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
        changed = False
        for i, arg in enumerate(self.arguments):
            if isinstance(arg, IdOperand):
                if arg in lattice.sl:
                    val = lattice.sl[arg.value]
                    if not isinstance(val, ConstantLatticeElement):
                        if type(val) is int:
                            self.arguments[i] = IntConstantOperand(val)
                        else:
                            assert type(val) is bool
                            self.arguments[i] = BoolConstantOperand(val)
                        changed = True
        return changed

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
