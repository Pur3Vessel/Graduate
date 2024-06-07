import parser_edsl as pe
from dataclasses import dataclass
from context import *
from builder import *
from typing import List, Union

NestedList = Union[float, List['NestedList']]


def check_dimentions(nested_list, dimentions):
    if type(nested_list) is float or type(nested_list) is int and len(dimentions) == 0:
        return True
    if len(nested_list) != int(dimentions[0]):
        return False
    for item in nested_list:
        if not check_dimentions(item, dimentions[1:]):
            return False
    return True


builder = Builder()
tmp_version = 0


def is_int(value):
    if isinstance(value, float):
        return value.is_integer()
    print("Что-то не так с float: " + str(value))
    return False


def is_atomic(expression):
    return isinstance(expression, IdUse) or isinstance(expression, BoolConst) or isinstance(expression,
                                                                                            NumConst) or isinstance(
        expression, FuncCall) or isinstance(expression, ArrayUse)


def place_assigns(assigns):
    for assign in assigns:
        new_IR = assign.get_IR()
        builder.add_expression(new_IR)


def generate_block(block):
    for action in block:
        action.generate()
        if isinstance(action, BreakAction) or isinstance(action, ContinueAction) or isinstance(action, GotoAction) or isinstance(action, ReturnAction):
            return True


def simplify_expression(expression):
    global tmp_version
    if is_atomic(expression):
        if isinstance(expression, FuncCall):
            new_args = []
            new_assigns = []
            for arg in expression.args:
                if not (isinstance(arg, IdUse) and arg.is_arr):
                    new_arg_assings, new_arg_tmp = simplify_expression(arg)
                    new_assigns += new_arg_assings
                    new_argument = IdUse(new_arg_tmp, pe.Fragment(pe.Position(0), pe.Position(0)), False)
                    new_argument.type = arg.type
                    new_args.append(new_argument)
                else:
                    new_args.append(arg)
            new_tmp = "tmp$" + str(tmp_version)
            tmp_version += 1
            call = FuncCall(expression.name, new_args, pe.Fragment(pe.Position(0), pe.Position(0)))
            call.type = expression.type
            new_assign = AssignAction(new_tmp, call, pe.Fragment(pe.Position(0), pe.Position(0)))
            new_assign.type = expression.type
            new_assigns.append(new_assign)
            return new_assigns, new_tmp
        elif isinstance(expression, ArrayUse):
            new_indexes = []
            new_assigns = []
            for idx in expression.indexing:
                new_idx_assigns, new_idx_tmp = simplify_expression(idx)
                new_assigns += new_idx_assigns
                new_idx = IdUse(new_idx_tmp, pe.Fragment(pe.Position(0), pe.Position(0)), False)
                new_idx.type = "int"
                new_indexes.append(new_idx)
            new_tmp = "tmp$" + str(tmp_version)
            tmp_version += 1
            use = ArrayUse(expression.name, new_indexes, pe.Fragment(pe.Position(0), pe.Position(0)), expression.dimention_variables)
            use.type = expression.type
            new_assign = AssignAction(new_tmp, use, pe.Fragment(pe.Position(0), pe.Position(0)))
            new_assign.type = expression.type
            new_assigns.append(new_assign)
            return new_assigns, new_tmp
        else:
            new_tmp = "tmp$" + str(tmp_version)
            tmp_version += 1
            new_assign = AssignAction(new_tmp, expression, pe.Fragment(pe.Position(0), pe.Position(0)))
            new_assign.type = expression.type
            return [new_assign], new_tmp
    else:
        if isinstance(expression, UnaryOp):
            new_assigns, new_tmp_exp = simplify_expression(expression.exp)
            new_tmp = "tmp$" + str(tmp_version)
            tmp_version += 1
            id_use = IdUse(new_tmp_exp, pe.Fragment(pe.Position(0), pe.Position(0)), False)
            id_use.type = expression.exp.type
            unary_op = UnaryOp(expression.op, id_use, pe.Fragment(pe.Position(0), pe.Position(0)))
            unary_op.type = expression.type
            new_assign = AssignAction(new_tmp, unary_op, pe.Fragment(pe.Position(0), pe.Position(0)))
            new_assign.type = expression.type
            new_assigns.append(new_assign)
            return new_assigns, new_tmp
        elif isinstance(expression, BinOp):
            new_tmp = "tmp$" + str(tmp_version)
            tmp_version += 1
            new_assigns_left, new_tmp_left = simplify_expression(expression.left)
            new_assings_right, new_tmp_right = simplify_expression(expression.right)
            new_assigns = new_assigns_left + new_assings_right
            id_use_left = IdUse(new_tmp_left, pe.Fragment(pe.Position(0), pe.Position(0)), False)
            id_use_left.type = expression.left.type
            id_use_right = IdUse(new_tmp_right, pe.Fragment(pe.Position(0), pe.Position(0)), False)
            id_use_right.type = expression.right.type
            bin_op = BinOp(id_use_left, expression.op, id_use_right, pe.Fragment(pe.Position(0), pe.Position(0)))
            bin_op.type = expression.type
            new_exp = AssignAction(new_tmp,
                                   bin_op,
                                   pe.Fragment(pe.Position(0), pe.Position(0)))
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
class NumericType(Type):
    def __eq__(self, other):
        return type(self) == type(other)

    def __str__(self):
        return "numeric"


@dataclass
class BoolType(Type):
    def __eq__(self, other):
        return isinstance(other, BoolType)

    def __str__(self):
        return "bool"


@dataclass
class IntType(NumericType):
    def __eq__(self, other):
        return isinstance(other, IntType)

    def __str__(self):
        return "int"


@dataclass
class FloatType(NumericType):
    def __eq__(self, other):
        return isinstance(other, FloatType)

    def __str__(self):
        return "float"


@dataclass
class Arg:
    type: Type
    name: str
    dimentions: list[str]


class Action(ABC):
    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, labels, is_loop, func_type):
        pass


class Expression(ABC):
    type: Type

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays):
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

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays):
        self.left.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays)
        self.right.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays)
        if self.op in ["and", "or"]:
            if not isinstance(self.left.type, BoolType) or not isinstance(self.right.type, BoolType):
                raise SemanticError(self.pos, "Несоотвествие типа и операции")
            self.type = BoolType()

        if self.op in ["mod", "div"]:
            if not isinstance(self.left.type, IntType) or not isinstance(self.right.type, IntType):
                raise SemanticError(self.pos, "Несоотвествие типа и операции")
            self.type = IntType()

        if self.op in ["+", "-", "*", "/", "mod", "div"]:
            if not isinstance(self.left.type, NumericType) or not isinstance(self.right.type, NumericType):
                raise SemanticError(self.pos, "Несоотвествие типа и операции")
            if isinstance(self.left.type, IntType) and isinstance(self.right.type, IntType) and self.op != "/":
                self.type = IntType()
            else:
                self.type = FloatType()

        if self.op in ["==", "!=", ">", ">=", "<", "<="]:
            if not isinstance(self.left.type, NumericType) or not isinstance(self.right.type, NumericType):
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

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays):
        self.exp.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays)
        if self.op == "not":
            if not isinstance(self.exp.type, BoolType):
                raise SemanticError(self.pos, "Несоотвествие типа и операции")
            self.type = BoolType()

        if self.op == "-":
            if not isinstance(self.exp.type, NumericType):
                raise SemanticError(self.pos, "Несоотвествие типа и операции")
            if isinstance(self.exp.type, IntType):
                self.type = IntType()
            else:
                self.type = FloatType()


@dataclass
class NumConst(Expression):
    value: float

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays):
        if is_int(self.value):
            self.type = IntType()
        else:
            self.type = FloatType()


@dataclass
class BoolConst(Expression):
    value: bool

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays):
        self.type = BoolType()


@dataclass
class IdUse(Expression):
    name: str
    pos: pe.Fragment
    is_arr: bool

    @pe.ExAction
    def create(attrs, coords, res_coord):
        name = attrs[0]
        return IdUse(name, res_coord, False)

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays):
        if self.name not in scalar_args and self.name not in decl_vars:
            raise SemanticError(self.pos, "Используется необъявленная переменная")
        self.type = scalar_args[self.name] if self.name in scalar_args else decl_vars[self.name]


@dataclass
class ArrayUse(Expression):
    name: str
    indexing: [Expression]
    pos: pe.Fragment
    dimention_variables: list[str]

    @pe.ExAction
    def create(attrs, coords, res_coord):
        name, indexing = attrs
        return ArrayUse(name, indexing, res_coord, [])

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays):
        if self.name not in array_args and self.name not in decl_arrays:
            raise SemanticError(self.pos, "Используется необъявленная переменная")
        n_dimentions = array_args[self.name][1] if self.name in array_args else decl_arrays[self.name][1]
        if len(self.indexing) != n_dimentions:
            raise SemanticError(self.pos, "Несовпадение размерностей")
        for exp in self.indexing:
            exp.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays)
            if not isinstance(exp.type, IntType):
                print(exp.type)
                print(self.indexing[1].right.type)
                raise SemanticError(self.pos, "Индекс массива не целое число")
        self.type = array_args[self.name][0] if self.name in array_args else decl_arrays[self.name][0]
        dim_vars = array_args[self.name][2] if self.name in array_args else decl_arrays[self.name][2]
        self.dimention_variables = dim_vars


@dataclass
class FuncCall(Expression):
    name: str
    args: [Expression]
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        name, args = attrs
        return FuncCall(name, args, res_coord)

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays):
        if self.name not in defined_funcs:
            raise SemanticError(self.pos, "Функции с таким именем не существует")
        f = defined_funcs[self.name]
        for i, arg in enumerate(self.args):
            if len(f.args[i].dimentions) != 0:
                if not isinstance(arg, IdUse):
                    raise SemanticError(self.pos, "Нужно передать имя массива")
                array_name = arg.name
                if array_name not in array_args and array_name not in decl_arrays:
                    raise SemanticError(self.pos, "Нужно передать объявленный массив")
                array_type = array_args[array_name][0] if array_name in array_args else decl_arrays[array_name][0]
                n_dimentions = array_args[array_name][1] if array_name in array_args else decl_arrays[array_name][1]
                if array_type != f.args[i].type:
                    raise SemanticError(self.pos, "Тип выражения не совпадает с типом аргумента функции")
                if n_dimentions != len(f.args[i].dimentions):
                    raise SemanticError(self, "Несовпадение количества размерностей")
                arg.is_arr = True
            else:
                arg.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays)
                if arg.type != f.args[i].type:
                    raise SemanticError(self.pos, "Тип выражения не совпадает с типом аргумента функции")
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

    def check_decl(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, var_type):
        if self.name in scalar_args or self.name in decl_vars or self.name in array_args or self.name in decl_arrays:
            raise SemanticError(self.pos, "Имя уже объявлено")
        if not isinstance(self.assign, EmptyExpression):
            self.assign.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays)
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

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, labels, is_loop, func_type):
        for init in self.varDeclInits:
            init.check_decl(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, self.type)

    def generate(self):
        type = str(self.type)
        for init in self.varDeclInits:
            builder.context.names.add((init.name, str(self.type)))
            if isinstance(init.assign, EmptyExpression):
                new_IR = AtomicAssign(type, init.name, IntConstantOperand(0), None, None)
                builder.add_expression(new_IR)
            else:
                new_assigns, new_tmp = simplify_expression(init.assign)
                place_assigns(new_assigns)
                ass_IR = AtomicAssign(type, init.name, IdOperand(new_tmp), None, None)
                builder.add_expression(ass_IR)


@dataclass
class ArrayDeclAction(Action):
    type: Type
    name: str
    dimentions: [float]
    init: NestedList
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        type, name, dimentions, init = attrs
        if len(init) == 0:
            init = None
        return ArrayDeclAction(type, name, dimentions, init, res_coord)

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, labels, is_loop, func_type):
        if self.name in scalar_args or self.name in decl_vars or self.name in array_args or self.name in decl_arrays:
            raise SemanticError(self.pos, "Имя уже объявлено")
        for dim in self.dimentions:
            if not is_int(dim):
                raise SemanticError(self.pos, "Измерение задано не целым числом")
        if self.init is not None:
            if not check_dimentions(self.init, self.dimentions):
                raise SemanticError(self.pos, "Некорректная инициализация массива")
        decl_arrays[self.name] = (self.type, len(self.dimentions), None)

    def generate(self):
        type = str(self.type)
        ir = ArrayInitInstruction(type, self.name, self.dimentions, self.init)
        builder.add_expression(ir)


@dataclass
class AssignAction(Action):
    name: str
    assign: Expression
    pos: pe.Fragment

    @pe.ExAction
    def create(attrs, coords, res_coord):
        name, assign = attrs
        return AssignAction(name, assign, res_coord)

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, labels, is_loop, func_type):
        if self.name not in scalar_args and self.name not in decl_vars:
            raise SemanticError(self.pos, "Переменная не объявлена")
        self.assign.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays)
        #print(self)
        if isinstance(self.assign, ArrayUse):
            print(self.assign.dimention_variables)
        var_type = scalar_args[self.name] if self.name in scalar_args else decl_vars[self.name]

        if self.assign.type != var_type and not (isinstance(var_type, FloatType) and isinstance(self.assign.type, IntType)):
            raise SemanticError(self.pos, "Тип переменной не совпадает с типом выражения")

    def get_IR(self):
        type = str(self.assign.type)
        value = self.name
        if is_atomic(self.assign):
            if isinstance(self.assign, IdUse):
                return AtomicAssign(type, value, IdOperand(self.assign.name), None, None)
            elif isinstance(self.assign, FuncCall):
                args = []
                for arg in self.assign.args:
                    args.append(IdOperand(arg.name))
                return AtomicAssign(type, value, FuncCallOperand(self.assign.name, args), None, None)
            elif isinstance(self.assign, ArrayUse):
                idx = []
                for i in self.assign.indexing:
                    idx.append(IdOperand(i.name))
                return AtomicAssign(type, value, ArrayUseOperand(self.assign.name, idx, self.assign.dimention_variables), None, None)
            elif isinstance(self.assign, BoolConst):
                return AtomicAssign(type, value, BoolConstantOperand(self.assign.value), None, None)
            elif isinstance(self.assign, NumConst):
                if is_int(self.assign.value):
                    return AtomicAssign(type, value, IntConstantOperand(self.assign.value), None, None)
                else:
                    return AtomicAssign(type, value, FloatConstantOperand(self.assign.value), None, None)
            else:
                print("что-то не так")
        elif isinstance(self.assign, BinOp):
            return BinaryAssign(type, value, self.assign.op, IdOperand(self.assign.left.name),
                                IdOperand(self.assign.right.name), None, str(self.assign.left.type), str(self.assign.right.type))
        elif isinstance(self.assign, UnaryOp):
            return UnaryAssign(type, value, self.assign.op, IdOperand(self.assign.exp.name), None)
        else:
            print("Что-то не так")

    def generate(self):
        new_assigns, new_tmp = simplify_expression(self.assign)
        place_assigns(new_assigns)
        ass_IR = AtomicAssign(str(self.assign.type), self.name, IdOperand(new_tmp), None, None)
        builder.add_expression(ass_IR)


@dataclass
class ArrayAssignAction(Action):
    name: str
    indexing: list[Expression]
    assign: Expression
    pos: pe.Fragment
    dimention_vars: list[str]

    @pe.ExAction
    def create(attrs, coords, res_coord):
        name, indexing, assign = attrs
        return ArrayAssignAction(name, indexing, assign, res_coord, [])

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, labels, is_loop, func_type):
        if self.name not in array_args and self.name not in decl_arrays:
            raise SemanticError(self.pos, "Переменная не объявлена")
        self.assign.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays)
        array_type = array_args[self.name][0] if self.name in array_args else decl_arrays[self.name][0]
        if self.assign.type != array_type and not (isinstance(array_type, FloatType) and isinstance(self.assign.type, IntType)):
            raise SemanticError(self.pos, "Тип переменной не совпадает с типом выражения")
        n_dimentions = array_args[self.name][1] if self.name in array_args else decl_arrays[self.name][1]
        if n_dimentions != len(self.indexing):
            raise SemanticError(self.pos, "Несовпадение размерностей")
        for dim in self.indexing:
            dim.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays)
            if not isinstance(dim.type, IntType):
                raise SemanticError(self.pos, "Индексация не целым числом")
        dim_vars = array_args[self.name][2] if self.name in array_args else decl_arrays[self.name][2]
        self.dimentions_vars = dim_vars

    def generate(self):
        new_assigns, new_tmp = simplify_expression(self.assign)
        place_assigns(new_assigns)
        new_indexes = []
        for idx in self.indexing:
            new_idx_assigns, new_idx_tmp = simplify_expression(idx)
            place_assigns(new_idx_assigns)
            new_indexes.append(IdOperand(new_idx_tmp))
        new_IR = AtomicAssign(str(self.assign.type), self.name, IdOperand(new_tmp), new_indexes, self.dimentions_vars)
        builder.add_expression(new_IR)


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

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, labels, is_loop, func_type):
        self.if_st.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays)
        if not isinstance(self.if_st.type, BoolType):
            raise SemanticError(self.pos, "Тип проверки не bool")
        decl_vars_then = deepcopy(decl_vars)
        decl_arrays_then = deepcopy(decl_arrays)
        labels_then = deepcopy(labels)
        for action in self.if_block:
            action.check(defined_funcs, scalar_args, array_args, decl_vars_then, decl_arrays_then, labels_then, is_loop,
                         func_type)
        decl_vars_else = deepcopy(decl_vars)
        decl_arrays_else = deepcopy(decl_arrays)
        labels_else = deepcopy(labels)
        for action in self.else_block:
            action.check(defined_funcs, scalar_args, array_args, decl_vars_else, decl_arrays_else, labels_else, is_loop,
                         func_type)

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

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, labels, is_loop, func_type):
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

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, labels, is_loop, func_type):
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

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, labels, is_loop, func_type):
        self.st.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays)
        if self.st.type != BoolType:
            raise SemanticError(self.pos, "Тип проверки не bool")

        decl_vars_loop = deepcopy(decl_vars)
        decl_arrays_loop = deepcopy(decl_arrays)
        labels_loop = deepcopy(labels)
        for action in self.block:
            action.check(defined_funcs, scalar_args, array_args, decl_vars_loop, decl_arrays_loop, labels_loop, True,
                         func_type)

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
        if len(builder.current_block().output_vertexes) == 0:
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

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, labels, is_loop, func_type):
        self.st.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays)
        if self.st.type != BoolType:
            raise SemanticError(self.pos, "Тип проверки не bool")

        decl_vars_loop = deepcopy(decl_vars)
        decl_arrays_loop = deepcopy(decl_arrays)
        labels_loop = deepcopy(labels)
        for action in self.block:
            action.check(defined_funcs, scalar_args, array_args, decl_vars_loop, decl_arrays_loop, labels_loop, True,
                         func_type)

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
        if len(builder.current_block().output_vertexes) == 0:
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
            step = NumConst(1.0)
        return ForAction(var_name, start, end, step, block, res_coord)

    def check_return(self):
        for action in self.block:
            if isinstance(action, ReturnAction):
                return True
            if isinstance(action, (IfAction, ForAction, WhileAction, DoWhileAction)):
                if action.check_return():
                    return True
        return False

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, labels, is_loop, func_type):
        if self.var_name in scalar_args or self.var_name in decl_vars:
            raise SemanticError(self.pos, "имя счетчика не уникально")
        self.start.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays)
        self.end.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays)
        self.step.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays)

        if self.start.type != IntType() or self.end.type != IntType() or self.step.type != IntType():
            raise SemanticError(self.pos, "некорректно заданы параметры цикла")

        decl_vars_loop = deepcopy(decl_vars)
        decl_vars_loop[self.var_name] = IntType()
        decl_arrays_loop = deepcopy(decl_arrays)
        labels_loop = deepcopy(labels)
        for action in self.block:
            action.check(defined_funcs, scalar_args, array_args, decl_vars_loop, decl_arrays_loop, labels_loop, True,
                         func_type)

    def generate(self):
        global tmp_version
        builder.create_block()
        current = builder.current_block()

        after_block = builder.create_block_without()
        builder.context.after_blocks.append(after_block)

        builder.set_insert(current)

        init_assigns, init_tmp = simplify_expression(self.start)
        place_assigns(init_assigns)
        init_IR = AtomicAssign("int", self.var_name, IdOperand(init_tmp), None, None)
        builder.add_expression(init_IR)
        builder.context.names.add((self.var_name, "int"))

        end_assigns, end_tmp = simplify_expression(self.end)
        place_assigns(end_assigns)
        new_tmp = "tmp$" + str(tmp_version)
        tmp_version += 1
        cond_IR = BinaryAssign("bool", new_tmp, "<", IdOperand(self.var_name), IdOperand(end_tmp), None, "int", "int")
        builder.add_expression(cond_IR)
        end_IR = IsTrueInstruction(IdOperand(new_tmp))
        builder.add_expression(end_IR)

        header = builder.create_block()
        builder.add_connector(current, after_block)

        latch = builder.create_block_without()

        step_assigns, step_tmp = simplify_expression(self.step)
        place_assigns(step_assigns)
        step_IR = BinaryAssign("int", self.var_name, "+", IdOperand(self.var_name), IdOperand(step_tmp), None, "int", "int")
        builder.add_expression(step_IR)
        builder.context.latches.append(latch)

        end_assigns, end_tmp = simplify_expression(self.end)
        place_assigns(end_assigns)
        new_tmp = "tmp$" + str(tmp_version)
        tmp_version += 1
        cond_IR = BinaryAssign("bool", new_tmp, "<", IdOperand(self.var_name), IdOperand(end_tmp), None, "int", "int")
        builder.add_expression(cond_IR)
        end_IR = IsTrueInstruction(IdOperand(new_tmp))
        builder.add_expression(end_IR)

        builder.set_insert(header)
        builder.create_block()
        generate_block(self.block)
        if len(builder.current_block().output_vertexes) == 0:
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

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, labels, is_loop, func_type):
        self.exp.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays)
        if not isinstance(self.exp.type, type(func_type)):
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

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, labels, is_loop, func_type):
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

    def check(self, defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, labels, is_loop, func_type):
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

        scalar_args = dict([(arg.name, arg.type) for arg in self.args if len(arg.dimentions) == 0])
        array_args = dict(
            [(arg.name, (arg.type, len(arg.dimentions), arg.dimentions)) for arg in self.args if len(arg.dimentions) != 0])
        for a in self.args:
            for i in a.dimentions:
                if i in scalar_args or i in array_args:
                    raise SemanticError(self.pos, f"у функции {self.name} найдены одноименные параметры")
                scalar_args[i] = IntType()
        decl_vars = {}
        decl_arrays = {}
        labels = {}
        is_loop = False

        for action in self.block:
            action.check(defined_funcs, scalar_args, array_args, decl_vars, decl_arrays, labels, is_loop,
                         self.return_type)

        if not self.__check_return():
            raise SemanticError(self.pos, f"функции {self.name} не обнаружено return")

    def generate(self):
        builder.create_block_without()
        arguments = [FuncArgOperand(str(arg.type), arg.name, arg.dimentions) for arg in self.args]
        for arg in arguments:
            if len(arg.dimentions) == 0:
                arg.dimentions = None
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
        defined_funcs = {}
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
            builder.contexts[func.name].tmp_version = tmp_version - 1
