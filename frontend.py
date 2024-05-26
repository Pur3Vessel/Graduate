from AST import *
import traceback


def prepend_to_list(element, lst):
    lst.insert(0, element)
    return lst


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
POSSIBLE_ARRAY_DECL = pe.NonTerminal("POSSIBLE_ARRAY_DECL")
ARRAY_DECL = pe.NonTerminal("ARRAY_DECL")
DIMENTIONS_DECL = pe.NonTerminal("DIMENTIONS_DECL")
OTHER_DIMENTIONS_DECL = pe.NonTerminal("OTHER_DIMENTIONS_DECL")
ARRAY_INIT = pe.NonTerminal("ARRAY_INIT")
ARRAY = pe.NonTerminal("ARRAY")
ARRAY_ELEM = pe.NonTerminal("ARRAY_ELEM")
ARRAY_ELEMS = pe.NonTerminal("ARRAY_ELEMS")
ARRAY_PARAM = pe.NonTerminal("ARRAY_PARAM")
DIMENTION_PARAM = pe.NonTerminal("DIMENTION_PARAM")

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
ADDING = pe.NonTerminal("ADDING")
INDEXING = pe.NonTerminal("INDEXING")
OTHER_DIMENTIONS_EXPR = pe.NonTerminal("OTHER_DIMENTIONS_EXPR")
IMMUTABLE = pe.NonTerminal("IMMUTABLE")
FUNC_CALL_ST = pe.NonTerminal("FUNC_CALL_ST")
CONSTANT = pe.NonTerminal("CONSTANT")
AND_OP = pe.NonTerminal("AND_OP")
OR_OP = pe.NonTerminal("OR_OP")
ID = pe.Terminal("ID", r'[A-Za-z][A-Za-z0-9]*', str)
NUM_CONST = pe.Terminal("NUM_CONST", r'[0-9]+(\.[0-9]+)?', float, priority=7)

ENTRY |= PROGRAM, Entry.create
PROGRAM |= DECL, PROGRAM, lambda x, y: [x] + y
PROGRAM |= lambda: []
DECL |= FUN_DECL

FUN_DECL |= TYPE_F, ID, '(', PARAMS, ')', BLOCK, FuncDef.create
TYPE_F |= TYPE
TYPE |= 'int', IntType
TYPE |= 'bool', BoolType
TYPE |= 'float', FloatType
PARAMS |= lambda: []
PARAMS |= PARAM_LIST
PARAM_LIST |= PARAM, OTHER_PARAMS, lambda x, y: [x] + y
OTHER_PARAMS |= ',', PARAM, OTHER_PARAMS, lambda x, y: [x] + y
OTHER_PARAMS |= lambda: []
PARAM |= TYPE, ID, ARRAY_PARAM, Arg
ARRAY_PARAM |= DIMENTION_PARAM, ARRAY_PARAM, lambda x, y: [x] + y
ARRAY_PARAM |= lambda: []
DIMENTION_PARAM |= '[', ID, ']'

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
ACTION |= ID, INDEXING, ASSIGN, ';', ArrayAssignAction.create
CALL_PARAMS |= SIMPLE_EXPRESSION, OTHER_CALL_PARAMS, lambda x, y: [x] + y
OTHER_CALL_PARAMS |= ',', SIMPLE_EXPRESSION, OTHER_CALL_PARAMS, lambda x, y: [x] + y
CALL_PARAMS |= lambda: []
OTHER_CALL_PARAMS |= lambda: []
ACTION |= LABEL_ACTION
LABEL_ACTION |= ID, ":", LabelAction.create

VAR_DECL |= TYPE, ID, '[', DIMENTIONS_DECL, ']', ARRAY_INIT, ArrayDeclAction.create
DIMENTIONS_DECL |= NUM_CONST, OTHER_DIMENTIONS_DECL, lambda x, y: [x] + y
OTHER_DIMENTIONS_DECL |= ',', NUM_CONST, OTHER_DIMENTIONS_DECL, lambda x, y: [x] + y
OTHER_DIMENTIONS_DECL |= lambda: []
ARRAY_INIT |= lambda: []
ARRAY_INIT |= "=", ARRAY
ARRAY |= '{', ARRAY_ELEM, ARRAY_ELEMS, '}', lambda x, y: prepend_to_list(x, y)
ARRAY_ELEM |= NUM_CONST
ARRAY_ELEM |= ARRAY
ARRAY_ELEMS |= ',', ARRAY_ELEM, ARRAY_ELEMS, lambda x, y: prepend_to_list(x, y)
ARRAY_ELEMS |= lambda: []

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
MUTABLE |= ID, INDEXING, ArrayUse.create
INDEXING |= '[', SIMPLE_EXPRESSION, OTHER_DIMENTIONS_EXPR, ']', lambda x, y: [x] + y
OTHER_DIMENTIONS_EXPR |= ',', SIMPLE_EXPRESSION, OTHER_DIMENTIONS_EXPR, lambda x, y: [x] + y
OTHER_DIMENTIONS_EXPR |= lambda: []


def parse(file):
    p = pe.Parser(ENTRY)
    assert p.is_lalr_one()
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
        print("Ошибка")
        print(type(e))
        print(e)
        traceback.print_exc()
