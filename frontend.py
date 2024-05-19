import parser_edsl as pe
from dataclasses import dataclass
from copy import deepcopy
import traceback
from context import *
from builder import *

builder = Builder()

ENTRY = pe.NonTerminal('ENTRY')
PROGRAM = pe.NonTerminal("PROGRAM")
DECL = pe.NonTerminal("DECL")
DECL_LIST = pe.NonTerminal("DECL_LIST")

FUN_DECL = pe.NonTerminal("FUN_DECL")
TYPE_F = pe.NonTerminal("TYPE_F")
PARAMS = pe.NonTerminal("PARAMS")
PARAM_LIST = pe.NonTerminal("PARAM_LIST")
OTHER_PARAMS = pe.NonTerminal("OTHER_PARAMS")
PARAM = pe.NonTerminal("PARAM")

VAR_DECL = pe.NonTerminal("VAR_DECL")
TYPE = pe.NonTerminal("TYPE")
VAR_DECL_LIST = pe.NonTerminal("VAR_DECL_LIST")
OTHER_DECLS = pe.NonTerminal("OTHER_DECLS")
VAR_DECL_INIT = pe.NonTerminal("VAR_DECL_INIT")
ASSIGN_DECL = pe.NonTerminal("ASSIGN_DECL")
ASSIGN = pe.NonTerminal("ASSIGN")

BLOCK = pe.NonTerminal("BLOCK")
ACTIONS = pe.NonTerminal("ACTIONS")
ACTION = pe.NonTerminal("ACTION")
ID_ST = pe.NonTerminal("ID_ST")
GOTO_ST = pe.NonTerminal("GOTO_ST")
IF_ST = pe.NonTerminal("IF_ST")
ELSE_ST = pe.NonTerminal("ELSE_ST")
WHILE_ST = pe.NonTerminal("WHILE_ST")
DO_WHILE_ST = pe.NonTerminal("DO_WHILE_ST")
FOR_ST = pe.NonTerminal("FOR_ST")
ITER_RANGE = pe.NonTerminal("ITER_RANGE")
BY_ST = pe.NonTerminal("BY_ST")
RETURN_ST = pe.NonTerminal("RETURN_ST")
CALL_PARAMS = pe.NonTerminal("CALL_PARAMS")
OTHER_CALL_PARAMS = pe.NonTerminal("OTHER_CALL_PARAMS")
LABEL_ACTION = pe.NonTerminal("LABEL_ACTION")

SIMPLE_EXPRESSION = pe.NonTerminal("SIMPLE_EXPRESSION")
AND_EXPRESSION = pe.NonTerminal("AND_EXPRESSION")
UNARY_REL_EXPRESSION = pe.NonTerminal("UNARY_REL_EXPRESSION")
REL_EXPRESSION = pe.NonTerminal("REL_EXPRESSION")
REL_OP = pe.NonTerminal("REL_OP")
EQ = pe.NonTerminal("EQ")
SUM_EXPRESSION = pe.NonTerminal("SUM_EXPRESSION")
SUM_OP = pe.NonTerminal("SUM_OP")
MUL_EXPRESSION = pe.NonTerminal("MUL_EXPRESSION")
MUL_OP = pe.NonTerminal("MUL_OP")
UNARY_EXPRESSION = pe.NonTerminal("UNARY_EXPRESSION")
UNARY_OP = pe.NonTerminal("UNARY_OP")
UNARY_LOGIC_OP = pe.NonTerminal("UNARY_LOGIC_OP")
FACTOR = pe.NonTerminal("FACTOR")
MUTABLE = pe.NonTerminal("MUTABLE")
IMMUTABLE = pe.NonTerminal("IMMUTABLE")
FUNC_CALL_ST = pe.NonTerminal("FUNC_CALL_ST")
CONSTANT = pe.NonTerminal("CONSTANT")
AND_OP = pe.NonTerminal("AND_OP")
OR_OP = pe.NonTerminal("OR_OP")
ID = pe.Terminal("ID", r'[A-Za-z][A-Za-z0-9]*', str)
NUM_CONST = pe.Terminal("NUM_CONST", r'[0-9]+', int, priority=7)

tmp_version = 0


def is_atomic(expresssion):
    return isinstance(expresssion, IdUse) or isinstance(expresssion, BoolConst) or isinstance(expresssion,
                                                                                              NumConst) or isinstance(
        expresssion, FuncCall)


def place_assigns(assigns):
    for assign in assigns:
        # print(assign)
        new_IR = assign.get_IR()
        builder.add_expression(new_IR)


def generate_block(block):
    for action in block:
        action.generate()
        if isinstance(action, BreakAction) or isinstance(action, ContinueAction) or isinstance(action, GotoAction):
            return True


def simplify_expression(expression):
    global tmp_version
    if is_atomic(expression):
        if isinstance(expression, FuncCall):
            new_args = []
            new_assigns = []
            for arg in expression.args:
                new_arg_assings, new_arg_tmp = simplify_expression(arg)
                new_assigns += new_arg_assings
                new_argument = IdUse(new_arg_tmp, None)
                new_argument.type = arg.type
                new_args.append(new_argument)
            new_tmp = "tmp$" + str(tmp_version)
            tmp_version += 1
            call = FuncCall(expression.name, new_args, None)
            call.type = expression.type
            new_assign = AssignAction(new_tmp, call, None)
            new_assign.type = expression.type
            new_assigns.append(new_assign)
            return new_assigns, new_tmp
        else:
            new_tmp = "tmp$" + str(tmp_version)
            tmp_version += 1
            new_assign = AssignAction(new_tmp, expression, None)
            new_assign.type = expression.type
            return [new_assign], new_tmp
    else:
        if isinstance(expression, UnaryOp):
            new_assigns, new_tmp_exp = simplify_expression(expression.exp)
            new_tmp = "tmp$" + str(tmp_version)
            tmp_version += 1
            id_use = IdUse(new_tmp_exp, None)
            id_use.type = expression.exp.type
            unary_op = UnaryOp(expression.op, id_use, None)
            unary_op.type = expression.type
            new_assign = AssignAction(new_tmp, unary_op, None)
            new_assign.type = expression.type
            new_assigns.append(new_assign)
            return new_assigns, new_tmp
        elif isinstance(expression, BinOp):
            new_tmp = "tmp$" + str(tmp_version)
            tmp_version += 1
            new_assigns_left, new_tmp_left = simplify_expression(expression.left)
            new_assings_right, new_tmp_right = simplify_expression(expression.right)
            new_assigns = new_assigns_left + new_assings_right
            id_use_left = IdUse(new_tmp_left, None)
            id_use_left.type = expression.left.type
            id_use_right = IdUse(new_tmp_right, None)
            id_use_right.type = expression.right.type
            bin_op = BinOp(id_use_left, expression.op, id_use_right, None)
            bin_op.type = expression.type
            new_exp = AssignAction(new_tmp,
                                   bin_op,
                                   None)
            new_exp.type = expression.type
            new_assigns.append(new_exp)
            return new_assigns, new_tmp
        else:
            print("Что-то не так")


class SemanticError(pe.Error):
    def __init__(self, pos, message):
        self.pos = pos
        self.__message = message

    @property
    def message(self):
        return self.__message


class Type(ABC):
    def __eq__(self, other):
        pass


@dataclass
class IntType(Type):
    def __eq__(self, other):
        return type(self) == type(other) or type(other) == type(AnyType)

    def __str__(self):
        return "int"


@dataclass
class AnyType(Type):
    def __eq__(self, other):
        return True


@dataclass
class BoolType(Type):
    def __eq__(self, other):
        return type(self) == type(other) or type(other) == type(AnyType)

    def __str__(self):
        return "bool"


@dataclass
class VoidType(Type):
    def __eq__(self, other):
        return type(self) == type(other) or type(other) == type(AnyType)

    def __str__(self):
        return "void"


@dataclass
class Arg:
    type: Type
    name: str


class Action(ABC):
    def check(self, defined_funcs, named_args, decl_vars, labels, is_loop, func_type):
        pass


class Expression(ABC):
    type: Type

    def check(self, defined_funcs, named_args, decl_vars):
        pass


@dataclass
class BinOp(Expression):
    left: Expression
    op: str
    right: Expression
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        # print(attrs)
        left, op, right = attrs
        return BinOp(left, op, right, res_coord)

    def check(self, defined_funcs, named_args, decl_vars):
        self.left.check(defined_funcs, named_args, decl_vars)
        self.right.check(defined_funcs, named_args, decl_vars)
        if self.op in ["and", "or"]:
            if self.left.type != BoolType or self.right.type != BoolType:
                raise SemanticError(self.pos, "Несоотвествие типа и операции")
            self.type = BoolType()

        if self.op in ["+", "-", "*", "/", "mod", "div"]:
            if self.left.type != IntType or self.right.type != IntType:
                raise SemanticError(self.pos, "Несоотвествие типа и операции")
            self.type = IntType()

        if self.op in ["==", "!=", ">", ">=", "<", "<="]:
            if self.left.type != IntType or self.right.type != IntType:
                raise SemanticError(self.pos, "Несоотвествие типа и операции")
            self.type = BoolType()


@dataclass
class UnaryOp(Expression):
    op: str
    exp: Expression
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        # print(attrs)
        op, exp = attrs
        return UnaryOp(op, exp, res_coord)

    def check(self, defined_funcs, named_args, decl_vars):
        self.exp.check(defined_funcs, named_args, decl_vars)
        if self.op == "not":
            if self.exp.type != BoolType:
                raise SemanticError(self.pos, "Несоотвествие типа и операции")
            self.type = BoolType()

        if self.op == "-":
            if self.exp.type != IntType:
                raise SemanticError(self.pos, "Несоотвествие типа и операции")
            self.type = IntType()


@dataclass
class NumConst(Expression):
    value: int

    def check(self, defined_funcs, named_args, decl_vars):
        self.type = IntType()


@dataclass
class BoolConst(Expression):
    value: bool

    def check(self, defined_funcs, named_args, decl_vars):
        self.type = BoolType()


@dataclass
class IdUse(Expression):
    name: str
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        name = attrs[0]
        return IdUse(name, res_coord)

    def check(self, defined_funcs, named_args, decl_vars):
        if self.name not in named_args and self.name not in decl_vars:
            raise SemanticError(self.pos, "Используется необъявленная переменная")
        self.type = named_args[self.name] if self.name in named_args else decl_vars[self.name]


@dataclass
class FuncCall(Expression):
    name: str
    args: [Expression]
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        name, args = attrs
        return FuncCall(name, args, res_coord)

    def check(self, defined_funcs, named_args, decl_vars):
        if self.name == "print":
            raise SemanticError(self.pos, "print нельзя использовать в выражениях")
        if self.name not in defined_funcs:
            raise SemanticError(self.pos, "Функции с таким именем не существует")
        if self.name == "input":
            if len(self.args) != 0:
                raise SemanticError(self.pos, "Нельзя использовать аргументы в input")
            self.type = IntType()
            return
        f = defined_funcs[self.name]
        if f.return_type == VoidType():
            raise SemanticError(self.pos, "Нельзя использовать void функцию в выражениях")
        for i, arg in enumerate(self.args):
            arg.check(defined_funcs, named_args, decl_vars)
            if arg.type != f.args[i].type:
                raise SemanticError(self.pos, "Тип выражения не совпадает с типом функции")
        self.type = f.return_type


class EmptyExpression(Expression):
    pass


@dataclass
class VarDeclInit(Action):
    name: str
    assign: Expression
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        # print(attrs, res_coord)
        name, assign = attrs
        return VarDeclInit(name, assign, res_coord)

    def check_decl(self, defined_funcs, named_args, decl_vars, var_type):
        if self.name in named_args or self.name in decl_vars:
            raise SemanticError(self.pos, "Имя уже объявлено")
        if not isinstance(self.assign, EmptyExpression):
            self.assign.check(defined_funcs, named_args, decl_vars)
            if self.assign.type != var_type:
                raise SemanticError(self.pos, "Тип присваивания не совпадает с типом переменной")
        decl_vars[self.name] = var_type


@dataclass
class VarDeclAction(Action):
    type: Type
    varDeclInits: [VarDeclInit]
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        type, inits = attrs
        return VarDeclAction(type, inits, res_coord)

    def check(self, defined_funcs, named_args, decl_vars, labels, is_loop, func_type):
        for init in self.varDeclInits:
            init.check_decl(defined_funcs, named_args, decl_vars, self.type)

    def generate(self):
        type = str(self.type)
        for init in self.varDeclInits:
            builder.context.names.add(init.name)
            if isinstance(init.assign, EmptyExpression):
                new_IR = AtomicAssign(type, init.name, IntConstantOperand(0))
                builder.add_expression(new_IR)
            else:
                new_assigns, new_tmp = simplify_expression(init.assign)
                place_assigns(new_assigns)
                ass_IR = AtomicAssign(type, init.name, IdOperand(new_tmp))
                builder.add_expression(ass_IR)


@dataclass
class FuncCallAction(Action):
    name: str
    args: [Expression]
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        name, args = attrs
        return FuncCallAction(name, args, res_coord)

    def check(self, defined_funcs, named_args, decl_vars, labels, is_loop, func_type):
        if self.name not in defined_funcs:
            raise SemanticError(self.pos, "Функции с таким именем не существует")
        if self.name == "input":
            raise SemanticError(self.pos, "Нельзя вызывать input как void")
        f = defined_funcs[self.name]
        if f is not None:
            if f.return_type != VoidType:
                raise SemanticError(self.pos, "как действие можно вызвать только функцию с void")
            for i, arg in enumerate(self.args):
                arg.check(defined_funcs, named_args, decl_vars)
                if arg.type != f.args[i].type:
                    raise SemanticError(self.pos, "Тип выражения не совпадает с типом функции")
        else:
            if self.name == "print":
                if len(self.args) != 1:
                    raise SemanticError(self.pos, "у print должен быть тольок 1 аргумент")
                self.args[0].check(defined_funcs, named_args, decl_vars)

    def generate(self):
        args = []
        for arg in self.args:
            new_assingns_arg, new_tmp_arg = simplify_expression(arg)
            args.append(IdOperand(new_tmp_arg))
            place_assigns(new_assingns_arg)
        call_IR = FuncCallInstruction(self.name, args)
        builder.add_expression(call_IR)


@dataclass
class AssignAction(Action):
    name: str
    assign: Expression
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        name, assign = attrs
        return AssignAction(name, assign, res_coord)

    def check(self, defined_funcs, named_args, decl_vars, labels, is_loop, func_type):
        if self.name not in named_args and self.name not in decl_vars:
            raise SemanticError(self.pos, "Переменная не объявлена")
        self.assign.check(defined_funcs, named_args, decl_vars)
        var_type = named_args[self.name] if self.name in named_args else decl_vars[self.name]

        if self.assign.type != var_type:
            raise SemanticError(self.pos, "Тип переменной не совпадает с типом выражения")

    def get_IR(self):
        type = str(self.assign.type)
        value = self.name
        if is_atomic(self.assign):
            if isinstance(self.assign, IdUse):
                return AtomicAssign(type, value, IdOperand(self.assign.name))
            elif isinstance(self.assign, FuncCall):
                args = []
                for arg in self.assign.args:
                    args.append(IdOperand(arg.name))
                return AtomicAssign(type, value, FuncCallOperand(self.assign.name, args))
            elif isinstance(self.assign, BoolConst):
                return AtomicAssign(type, value, BoolConstantOperand(self.assign.value))
            elif isinstance(self.assign, NumConst):
                return AtomicAssign(type, value, IntConstantOperand(self.assign.value))
            else:
                print("что-то не так")
        elif isinstance(self.assign, BinOp):
            return BinaryAssign(type, value, self.assign.op, IdOperand(self.assign.left.name),
                                IdOperand(self.assign.right.name))
        elif isinstance(self.assign, UnaryOp):
            return UnaryAssign(type, value, self.assign.op, IdOperand(self.assign.exp.name))
        else:
            print("Что-то не так")

    def generate(self):
        new_assigns, new_tmp = simplify_expression(self.assign)
        place_assigns(new_assigns)
        ass_IR = AtomicAssign(str(self.assign.type), self.name, IdOperand(new_tmp))
        builder.add_expression(ass_IR)


class EmptyElse(Action):
    pass


@dataclass
class IfAction(Action):
    if_st: Expression
    if_block: [Action]
    else_block: [Action]
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        # print(attrs)
        if_st, if_block, else_block = attrs
        if isinstance(else_block, EmptyElse):
            else_block = []
        return IfAction(if_st, if_block, else_block, res_coord)

    def check_return(self):
        for action in self.if_block:
            if isinstance(action, ReturnAction):
                return True
            if isinstance(action, (IfAction, ForAction, WhileAction, DoWhileAction)):
                if action.check_return():
                    return True

        for action in self.else_block:
            if isinstance(action, ReturnAction):
                return True
            if isinstance(action, (IfAction, ForAction, WhileAction, DoWhileAction)):
                if action.check_return():
                    return True

        return False

    def check(self, defined_funcs, named_args, decl_vars, labels, is_loop, func_type):
        self.if_st.check(defined_funcs, named_args, decl_vars)
        if self.if_st.type != BoolType:
            raise SemanticError(self.pos, "Тип проверки не bool")
        decl_vars_then = deepcopy(decl_vars)
        labels_then = deepcopy(labels)
        for action in self.if_block:
            action.check(defined_funcs, named_args, decl_vars_then, labels_then, is_loop, func_type)
        decl_vars_else = deepcopy(decl_vars)
        labels_else = deepcopy(labels)
        for action in self.else_block:
            action.check(defined_funcs, named_args, decl_vars_else, labels_else, is_loop, func_type)

    def generate(self):
        st_assings, st_tmp = simplify_expression(self.if_st)
        place_assigns(st_assings)
        new_cmp_IR = IsTrueInstruction(IdOperand(st_tmp))
        builder.add_expression(new_cmp_IR)
        cond_block = builder.current_block()
        builder.create_block()
        is_breakable = generate_block(self.if_block)
        then_block = builder.current_block()
        if len(self.else_block) != 0:
            builder.set_insert(cond_block)
            builder.create_block()
            is_breakable_else = generate_block(self.else_block)
            else_block = builder.current_block()
            afrer_block = builder.create_block_without()
            if not is_breakable:
                builder.add_connector(then_block, afrer_block)
            if not is_breakable_else:
                builder.add_connector(else_block, afrer_block)
        else:
            if is_breakable:
                after_block = builder.create_block_without()
            else:
                after_block = builder.create_block()
            builder.add_connector(cond_block, after_block)


@dataclass
class LabelAction(Action):
    label: str
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        label = attrs[0]
        return LabelAction(label, res_coord)

    def check(self, defined_funcs, named_args, decl_vars, labels, is_loop, func_type):
        if self.label in labels:
            raise SemanticError(self.pos, "Метка уже существует в области видимости")
        labels[self.label] = True

    def generate(self):
        builder.create_block()
        builder.create_labeled_block(self.label)


@dataclass
class GotoAction(Action):
    label: str
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        label = attrs[0]
        return GotoAction(label, res_coord)

    def check(self, defined_funcs, named_args, decl_vars, labels, is_loop, func_type):
        if self.label not in labels:
            raise SemanticError(self.pos, "Не найдена метка")

    def generate(self):
        labeled_block = builder.get_block_by_label(self.label)
        if labeled_block is None:
            print("что то не так")
        else:
            current_block = builder.current_block()
            builder.add_connector(current_block, labeled_block)


@dataclass
class WhileAction(Action):
    st: Expression
    block: [Action]
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        st, block = attrs
        return WhileAction(st, block, res_coord)

    def check_return(self):
        for action in self.block:
            if isinstance(action, ReturnAction):
                return True
            if isinstance(action, (IfAction, ForAction, WhileAction, DoWhileAction)):
                if action.check_return():
                    return True
        return False

    def check(self, defined_funcs, named_args, decl_vars, labels, is_loop, func_type):
        self.st.check(defined_funcs, named_args, decl_vars)
        if self.st.type != BoolType:
            raise SemanticError(self.pos, "Тип проверки не bool")

        decl_vars_loop = deepcopy(decl_vars)
        labels_loop = deepcopy(labels)
        for action in self.block:
            action.check(defined_funcs, named_args, decl_vars_loop, labels_loop, True, func_type)

    def generate(self):
        current = builder.current_block()

        after_block = builder.create_block_without()
        builder.context.after_blocks.append(after_block)

        builder.set_insert(current)

        cond_assigns, new_tmp_cond = simplify_expression(self.st)
        place_assigns(cond_assigns)
        new_IR_cmp = IsTrueInstruction(IdOperand(new_tmp_cond))
        builder.add_expression(new_IR_cmp)

        builder.create_block()
        builder.add_connector(current, after_block)
        header = builder.create_block()

        latch = builder.create_block_without()
        cond_assigns, new_tmp_cond = simplify_expression(self.st)
        place_assigns(cond_assigns)
        new_IR_cmp = IsTrueInstruction(IdOperand(new_tmp_cond))
        builder.add_expression(new_IR_cmp)
        builder.context.latches.append(latch)

        builder.set_insert(header)
        builder.create_block()
        generate_block(self.block)
        builder.add_connector(builder.current_block(), latch)
        builder.add_connector(latch, header)
        builder.add_connector(latch, after_block)
        builder.set_insert(after_block)
        builder.context.after_blocks.pop()
        builder.context.latches.pop()


@dataclass
class DoWhileAction(Action):
    block: [Action]
    st: Expression
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        # print(attrs, res_coord)
        block, st = attrs
        return DoWhileAction(block, st, res_coord)

    def check_return(self):
        for action in self.block:
            if isinstance(action, ReturnAction):
                return True
            if isinstance(action, (IfAction, ForAction, WhileAction, DoWhileAction)):
                if action.check_return():
                    return True
        return False

    def check(self, defined_funcs, named_args, decl_vars, labels, is_loop, func_type):
        self.st.check(defined_funcs, named_args, decl_vars)
        if self.st.type != BoolType:
            raise SemanticError(self.pos, "Тип проверки не bool")

        decl_vars_loop = deepcopy(decl_vars)
        labels_loop = deepcopy(labels)
        for action in self.block:
            action.check(defined_funcs, named_args, decl_vars_loop, labels_loop, True, func_type)

    def generate(self):
        builder.create_block()
        header = builder.create_block()

        latch = builder.create_block_without()
        cond_assigns, new_tmp_cond = simplify_expression(self.st)
        place_assigns(cond_assigns)
        new_IR_cmp = IsTrueInstruction(IdOperand(new_tmp_cond))
        builder.add_expression(new_IR_cmp)
        builder.context.latches.append(latch)

        after_block = builder.create_block_without()
        builder.context.after_blocks.append(after_block)

        builder.set_insert(header)
        builder.create_block()
        generate_block(self.block)
        builder.add_connector(builder.current_block(), latch)
        builder.add_connector(latch, header)
        builder.add_connector(latch, after_block)
        builder.set_insert(after_block)
        builder.context.after_blocks.pop()
        builder.context.latches.pop()


@dataclass
class ForAction(Action):
    var_name: str
    start: Expression
    end: Expression
    step: Expression
    block: [Action]
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        var_name, start, end, step, block = attrs
        if isinstance(step, EmptyExpression):
            step = NumConst(1)
        return ForAction(var_name, start, end, step, block, res_coord)

    def check_return(self):
        for action in self.block:
            if isinstance(action, ReturnAction):
                return True
            if isinstance(action, (IfAction, ForAction, WhileAction, DoWhileAction)):
                if action.check_return():
                    return True
        return False

    def check(self, defined_funcs, named_args, decl_vars, labels, is_loop, func_type):
        if self.var_name in named_args or self.var_name in decl_vars:
            raise SemanticError(self.pos, "имя счетчика не уникально")
        self.start.check(defined_funcs, named_args, decl_vars)
        self.end.check(defined_funcs, named_args, decl_vars)
        self.step.check(defined_funcs, named_args, decl_vars)

        if self.start.type != IntType() or self.end.type != IntType() or self.step.type != IntType():
            raise SemanticError(self.pos, "некорректно заданы параметры цикла")

        decl_vars_loop = deepcopy(decl_vars)
        decl_vars_loop[self.var_name] = IntType()
        labels_loop = deepcopy(labels)
        for action in self.block:
            action.check(defined_funcs, named_args, decl_vars_loop, labels_loop, True, func_type)

    def generate(self):
        global tmp_version
        current = builder.current_block()

        after_block = builder.create_block_without()
        builder.context.after_blocks.append(after_block)

        builder.set_insert(current)

        init_assigns, init_tmp = simplify_expression(self.start)
        place_assigns(init_assigns)
        init_IR = AtomicAssign("int", self.var_name, IdOperand(init_tmp))
        builder.add_expression(init_IR)
        builder.context.names.add(self.var_name)

        end_assigns, end_tmp = simplify_expression(self.end)
        place_assigns(end_assigns)
        new_tmp = "tmp$" + str(tmp_version)
        tmp_version += 1
        cond_IR = BinaryAssign("bool", new_tmp, "<", IdOperand(self.var_name), IdOperand(end_tmp))
        builder.add_expression(cond_IR)
        end_IR = IsTrueInstruction(IdOperand(new_tmp))
        builder.add_expression(end_IR)

        builder.create_block()
        builder.add_connector(current, after_block)
        header = builder.create_block()

        latch = builder.create_block_without()

        step_assigns, step_tmp = simplify_expression(self.step)
        place_assigns(step_assigns)
        step_IR = BinaryAssign("int", self.var_name, "+", IdOperand(self.var_name), IdOperand(step_tmp))
        builder.add_expression(step_IR)
        builder.context.latches.append(latch)

        end_assigns, end_tmp = simplify_expression(self.end)
        place_assigns(end_assigns)
        new_tmp = "tmp$" + str(tmp_version)
        tmp_version += 1
        cond_IR = BinaryAssign("bool", new_tmp, "<", IdOperand(self.var_name), IdOperand(end_tmp))
        builder.add_expression(cond_IR)
        end_IR = IsTrueInstruction(IdOperand(new_tmp))
        builder.add_expression(end_IR)

        builder.set_insert(header)
        builder.create_block()
        generate_block(self.block)
        builder.add_connector(builder.current_block(), latch)
        builder.add_connector(latch, header)
        builder.add_connector(latch, after_block)
        builder.set_insert(after_block)
        builder.context.latches.pop()
        builder.context.after_blocks.pop()


@dataclass
class ReturnAction(Action):
    exp: Expression
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        exp = attrs[0]
        return ReturnAction(exp, res_coord)

    def check(self, defined_funcs, named_args, decl_vars, labels, is_loop, func_type):
        if isinstance(func_type, VoidType):
            raise SemanticError(self.pos, "в void функции нельзя return")
        self.exp.check(defined_funcs, named_args, decl_vars)
        if self.exp.type != func_type:
            raise SemanticError(self.pos, "тип return не совпадает с возвращаемым типом")

    def generate(self):
        new_assigns, new_tmp = simplify_expression(self.exp)
        place_assigns(new_assigns)
        return_IR = ReturnInstruction(IdOperand(new_tmp))
        builder.add_expression(return_IR)


@dataclass
class BreakAction(Action):
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        return BreakAction(res_coord)

    def check(self, defined_funcs, named_args, decl_vars, labels, is_loop, func_type):
        if not is_loop:
            raise SemanticError(self.pos, "break вне цикла")

    def generate(self):
        after_block = builder.context.after_blocks[-1]
        builder.add_connector(builder.current_block(), after_block)


@dataclass
class ContinueAction(Action):
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        return ContinueAction(res_coord)

    def check(self, defined_funcs, named_args, decl_vars, labels, is_loop, func_type):
        if not is_loop:
            raise SemanticError(self.pos, "continue вне цикла")

    def generate(self):
        latch = builder.context.latches[-1]
        builder.add_connector(builder.current_block(), latch)


@dataclass
class FuncDef:
    return_type: Type
    name: str
    args: [Arg]
    block: [Action]
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        return_type, name, args, block = attrs
        return FuncDef(return_type, name, args, block, res_coord)

    def __check_return(self):
        for action in self.block:
            if isinstance(action, ReturnAction):
                return True
            if isinstance(action, (IfAction, ForAction, WhileAction, DoWhileAction)):
                if action.check_return():
                    return True
        return False

    def check(self, defined_funcs):
        if self.name == "main":
            if not isinstance(self.return_type, IntType):
                raise SemanticError(self.pos, "У функции main возвращаемый тип не int")
            if len(self.args) > 0:
                raise SemanticError(self.pos, "У функции main не должно быть аргументов")
        if len(self.args) != len(set(map(lambda x: x.name, self.args))):
            raise SemanticError(self.pos, f"у функции {self.name} найдены одноименные параметры")
        named_args = dict([(arg.name, arg.type) for arg in self.args])
        decl_vars = {}
        labels = {}
        is_loop = False

        for action in self.block:
            action.check(defined_funcs, named_args, decl_vars, labels, is_loop, self.return_type)

        if not isinstance(self.return_type, VoidType) and not self.__check_return():
            raise SemanticError(self.pos, f"функции {self.name} не обнаружено return")

    def generate(self):
        builder.create_block_without()
        arguments = [FuncArgOperand(str(arg.type), arg.name) for arg in self.args]
        def_IR = FuncDefInstruction(str(self.return_type), self.name, arguments)
        builder.add_expression(def_IR)
        builder.create_block()
        generate_block(self.block)


@dataclass
class Entry:
    funcDefs: [FuncDef]
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        funcDefs = attrs[0]
        return Entry(funcDefs, res_coord)

    def __check_main(self):
        for func in self.funcDefs:
            if func.name == "main":
                return True
        return False

    def check(self):
        defined_funcs = {"print": None, 'input': None}
        for func in self.funcDefs:
            if func.name in defined_funcs:
                raise SemanticError(func.pos, 'Найдены одноименные функции')
            defined_funcs[func.name] = func

        if not self.__check_main():
            raise SemanticError(self.pos, "Не найдена функция main")

        for func in self.funcDefs:
            func.check(defined_funcs)

    def __str__(self):
        s = ""
        for func in self.funcDefs:
            s += str(func) + "\n"
        return s

    def generate(self):
        global tmp_version
        for func in self.funcDefs:
            tmp_version = 0
            builder.add_context(func.name)
            func.generate()


ENTRY |= PROGRAM, Entry.create
PROGRAM |= DECL, PROGRAM, lambda x, y: [x] + y
PROGRAM |= lambda: []
DECL |= FUN_DECL

FUN_DECL |= TYPE_F, ID, '(', PARAMS, ')', BLOCK, FuncDef.create
TYPE_F |= 'void', VoidType
TYPE_F |= TYPE
TYPE |= 'int', IntType
TYPE |= 'bool', BoolType
PARAMS |= lambda: []
PARAMS |= PARAM_LIST
PARAM_LIST |= PARAM, OTHER_PARAMS, lambda x, y: [x] + y
OTHER_PARAMS |= ',', PARAM, OTHER_PARAMS, lambda x, y: [x] + y
OTHER_PARAMS |= lambda: []
PARAM |= TYPE, ID, Arg

BLOCK |= '{', ACTIONS, '}'
ACTIONS |= ACTION, ACTIONS, lambda x, y: [x] + y
ACTIONS |= lambda: []
ACTION |= 'break', ';', BreakAction.create
ACTION |= 'continue', ';', ContinueAction.create
ACTION |= RETURN_ST
RETURN_ST |= 'return', SIMPLE_EXPRESSION, ';', ReturnAction.create
ACTION |= GOTO_ST
GOTO_ST |= 'goto', ID, ';', GotoAction.create
ACTION |= WHILE_ST
WHILE_ST |= 'while', '(', SIMPLE_EXPRESSION, ')', BLOCK, WhileAction.create
ACTION |= DO_WHILE_ST
DO_WHILE_ST |= 'do', BLOCK, 'while', '(', SIMPLE_EXPRESSION, ')', DoWhileAction.create
ACTION |= FOR_ST
FOR_ST |= 'for', '(', ID, '=', SIMPLE_EXPRESSION, 'to', SIMPLE_EXPRESSION, BY_ST, ')', BLOCK, ForAction.create
BY_ST |= 'by', SIMPLE_EXPRESSION
BY_ST |= EmptyExpression
ACTION |= IF_ST
IF_ST |= 'if', '(', SIMPLE_EXPRESSION, ')', BLOCK, ELSE_ST, IfAction.create
ELSE_ST |= 'else', BLOCK
ELSE_ST |= EmptyElse
ACTION |= VAR_DECL, ';'
ACTION |= ID, ASSIGN, ';', AssignAction.create
ACTION |= ID, '(', CALL_PARAMS, ')', ';', FuncCallAction.create
CALL_PARAMS |= SIMPLE_EXPRESSION, OTHER_CALL_PARAMS, lambda x, y: [x] + y
OTHER_CALL_PARAMS |= ',', SIMPLE_EXPRESSION, OTHER_CALL_PARAMS, lambda x, y: [x] + y
CALL_PARAMS |= lambda: []
OTHER_CALL_PARAMS |= lambda: []
ACTION |= LABEL_ACTION
LABEL_ACTION |= ID, ":", LabelAction.create

VAR_DECL |= TYPE, VAR_DECL_LIST, VarDeclAction.create
VAR_DECL_LIST |= VAR_DECL_INIT, OTHER_DECLS, lambda x, y: [x] + y
OTHER_DECLS |= ',', VAR_DECL_INIT, OTHER_DECLS, lambda x, y: [x] + y
OTHER_DECLS |= lambda: []
VAR_DECL_INIT |= ID, ASSIGN_DECL, VarDeclInit.create
ASSIGN_DECL |= ASSIGN
ASSIGN |= '=', SIMPLE_EXPRESSION
ASSIGN_DECL |= EmptyExpression

SIMPLE_EXPRESSION |= SIMPLE_EXPRESSION, OR_OP, AND_EXPRESSION, BinOp.create
OR_OP |= 'or', lambda: 'or'
AND_OP |= 'and', lambda: 'and'
SIMPLE_EXPRESSION |= AND_EXPRESSION
AND_EXPRESSION |= AND_EXPRESSION, AND_OP, UNARY_REL_EXPRESSION, BinOp.create
AND_EXPRESSION |= UNARY_REL_EXPRESSION
UNARY_REL_EXPRESSION |= UNARY_LOGIC_OP, UNARY_REL_EXPRESSION, UnaryOp.create
UNARY_LOGIC_OP |= 'not', lambda: 'not'
UNARY_REL_EXPRESSION |= REL_EXPRESSION
REL_EXPRESSION |= SUM_EXPRESSION
REL_EXPRESSION |= SUM_EXPRESSION, REL_OP, SUM_EXPRESSION, BinOp.create
REL_OP |= '<', lambda: '<'
REL_OP |= '<=', lambda: '<='
REL_OP |= '==', lambda: '=='
REL_OP |= "!=", lambda: '!='
REL_OP |= ">", lambda: '>'
REL_OP |= ">=", lambda: '>='
SUM_EXPRESSION |= MUL_EXPRESSION
SUM_EXPRESSION |= SUM_EXPRESSION, SUM_OP, MUL_EXPRESSION, BinOp.create
SUM_OP |= '+', lambda: '+'
SUM_OP |= '-', lambda: '-'
MUL_OP |= '*', lambda: '*'
MUL_OP |= '/', lambda: '/'
MUL_OP |= 'mod', lambda: 'mod'
MUL_OP |= 'div', lambda: 'div'
MUL_EXPRESSION |= MUL_EXPRESSION, MUL_OP, UNARY_EXPRESSION, BinOp.create
MUL_EXPRESSION |= UNARY_EXPRESSION
UNARY_EXPRESSION |= UNARY_OP, UNARY_EXPRESSION, UnaryOp.create
UNARY_OP |= '-', lambda: '-'
UNARY_EXPRESSION |= FACTOR
FACTOR |= IMMUTABLE
FACTOR |= MUTABLE
IMMUTABLE |= '(', SIMPLE_EXPRESSION, ')'
IMMUTABLE |= CONSTANT
CONSTANT |= NUM_CONST, NumConst
CONSTANT |= 'true', lambda: BoolConst(True)
CONSTANT |= 'false', lambda: BoolConst(False)
MUTABLE |= ID, IdUse.create
MUTABLE |= ID, '(', CALL_PARAMS, ')', FuncCall.create


def parse(file):
    p = pe.Parser(ENTRY)
    assert p.is_lalr_one()
    # print("Фух")
    p.add_skipped_domain('\\s')
    p.add_skipped_domain('//[^\n]*\n')
    try:
        with open(file) as f:
            tree = p.parse(f.read())
            tree.check()
            return tree
    except pe.Error as e:
        print(f"Ошибка {e.pos}: {e.message}")
    except Exception as e:
        print(type(e))
        print(e)
        traceback.print_exc()
