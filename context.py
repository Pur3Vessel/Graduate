from graph import *
from lattice import *
import re
import numpy as np

tile_sizes1 = [2, 2]
tile_sizes2 = [2, 2, 2]


class Context:
    def __init__(self):
        self.count = 0
        self.stack = []
        self.names = set()
        self.graph = Graph()
        self.cur_vertex = None
        self.latches = []
        self.after_blocks = []
        self.contexts = {}
        self.labels_to_live = {}
        self.tmp_version = -1

    def set_contexts(self, contexts):
        self.contexts = contexts

    def get_tmp(self):
        self.tmp_version += 1
        return "tmp$" + str(self.tmp_version)

    @staticmethod
    def which_pred(v1, v):
        for i, ver in enumerate(v1.input_vertexes):
            if ver.number == v.number:
                return i
        return None

    def change_numeration(self):
        for name in self.names:
            self.count = 1
            self.stack.clear()
            self.stack.append(0)
            self.change_numeration_by_name(name[0])

    def change_numeration_by_name(self, name):
        self.traverse(self.graph.vertexes[1], name)

    def traverse(self, v, name):
        for stmt in v.block:
            if not isinstance(stmt, PhiAssign):
                stmt.rename_operands(name, self.stack[-1])

            if is_assign(stmt) and stmt.value == name:
                stmt.value = stmt.value + "_" + str(self.count)
                self.stack.append(self.count)
                self.count += 1

        for succ in v.output_vertexes:
            j = self.which_pred(succ, v)

            for stmt in succ.block:
                if isinstance(stmt, PhiAssign) and stmt.value.split("_")[0] == name:
                    stmt.arguments[j] = IdOperand(name + "_" + str(self.stack[-1]))

        for child in v.children:
            self.traverse(child, name)

        for stmt in v.block:
            if is_assign(stmt):
                l = stmt.value
                if l.split("_")[0] == name:
                    self.stack.pop()

    def place_phi(self):
        for name in self.names:
            using_set = self.graph.get_all_assign(name[0])
            places = self.graph.make_dfp(using_set)
            for place in places:
                phi_args = []
                for _ in place.input_vertexes:
                    phi_args.append(name[0])
                phi_args = list(map(lambda x: IdOperand(x), phi_args))
                phi_expr = PhiAssign(name[1], name[0], phi_args)
                place.insert_head(phi_expr)

    def loop_invariant_code_motion(self, is_preheader):
        # for v in self.graph.vertexes:
        #    for inst in v.block:
        #        if is_assign(inst):
        #            print(inst, self.graph.assign2point[inst])
        # for v in self.graph.vertexes:
        # print(v.block[0])
        # print("In:", v.inB)
        # print("Out:", v.outB)
        cycles = sorted(self.graph.cycles, key=lambda x: len(x))
        changed = False
        for cycle in cycles:
            changed = self.lycm_cycle(cycle, is_preheader) or changed
        return changed

    def lycm_cycle(self, cycle, is_preheader):
        cycleN = []
        for v in cycle:
            if v.label is None:
                cycleN.append(v)
            else:
                if v.label not in list(map(lambda x: x.label, cycleN)):
                    cycleN.append(v)
        cycle = cycleN
        invar_order = self.mark_invar(cycle)
        # for inst in invar_order:
        #    print(inst)
        changed = self.move_invars(invar_order, cycle, is_preheader)
        return changed

    def mark_invar(self, cycle):
        inst_invar = {}
        invar_order = []
        order = self.graph.bfs_cycle(cycle)
        # for v in order:
        #     print(v.block[0])
        for v in cycle:
            for instruction in v.block:
                if is_assign(instruction):
                    inst_invar[instruction] = False
        changed = True
        while changed:
            changed = False
            for v in order:
                changed = changed or self.mark_block(cycle, v, invar_order, inst_invar)
        return invar_order

    def is_const_operand(self, operand):
        return isinstance(operand, IntConstantOperand) or isinstance(operand, BoolConstantOperand) or isinstance(
            operand, FloatConstantOperand)

    def check_inv_operand(self, operand, block, cycle, instruction, inst_invar):
        if self.is_const_operand(operand):
            return True

        definitions = block.inB
        for instr in block.block:
            if instr == instruction:
                break
            if is_assign(instruction):
                value = instruction.value
                kill = set()
                for point in definitions:
                    if self.graph.point2assign[point].value == value:
                        kill.add(point)
                definitions -= kill
                definitions.add(self.graph.assign2point[instruction])
        definitions_for_op = set(filter(lambda x: self.graph.point2assign[x].value == operand.value, definitions))
        # print(operand, definitions_for_op)
        if len(definitions_for_op) == 1:
            defin = self.graph.point2assign[next(iter(definitions_for_op))]
            return self.graph.is_instruction_in_cycle(defin, cycle) and inst_invar[defin]
        else:
            is_inv = True
            for defin in definitions_for_op:
                defin = self.graph.point2assign[defin]
                is_inv = is_inv and not self.graph.is_instruction_in_cycle(defin, cycle)
            return is_inv

    def mark_block(self, cycle, block, invar_order, inst_invar):
        changed = False
        for instruction in block.block:
            if is_assign(instruction) and not inst_invar[instruction]:
                is_inv = True
                if isinstance(instruction,
                              (AtomicAssign, UnaryAssign, BinaryAssign)) and instruction.dimentions is not None:
                    is_inv = False
                if isinstance(instruction, BinaryAssign) and instruction.is_cmp():
                    is_inv = False
                operands = instruction.get_operands()
                for operand in operands:
                    if isinstance(operand, ArrayUseOperand):
                        is_inv = False
                    # print(f"{instruction}: {operand}: {self.check_inv_operand(operand, block, cycle, instruction, inst_invar)}")
                    is_inv = is_inv and self.check_inv_operand(operand, block, cycle, instruction, inst_invar)
                inst_invar[instruction] = is_inv
                if is_inv:
                    changed = True
                    invar_order.append(instruction)
        return changed

    def dom_uses(self, instruction, cycle):
        instr_block = self.graph.get_block_by_instruction(instruction)
        used_blocks = self.graph.get_all_uses_cycle_blocks(cycle, instr_block, instruction.value)
        for instr in instr_block.block:
            if instr == instruction:
                break
            if instr.is_use_op(instruction.value):
                return False
        is_uses = True
        for bl in used_blocks:
            is_uses = is_uses and self.graph.is_dom(instr_block, bl)
        return is_uses

    def dom_exits(self, instruction, subgraph, exits):
        instr_block = self.graph.get_block_by_instruction(instruction)

        is_exists = True
        for exit in exits:
            is_exists = is_exists and subgraph.is_dom(instr_block, exit)

        return is_exists

    def dom_predicate(self, instruction, cycle, preheader):
        exits = self.graph.get_exits_for_cycle(cycle)
        # for exit in exits:
        #    print(exit.dfs_number)
        # subgraph = Graph()
        # subgraph.vertexes = [preheader] + cycle + exits

        # subgraph.build_dominators_tree()
        is_pred = self.dom_uses(instruction, cycle) and self.dom_exits(instruction, self.graph, exits)
        self.graph.clean_dominators()
        return is_pred

    def move_invars(self, invar_order, cycle, is_preheader):
        changed = False
        if len(invar_order) != 0:
            if not is_preheader:
                preheader = self.graph.create_preheader(cycle)
            else:
                header = cycle[1]
                preheader = header.input_vertexes[-1]
            self.graph.dfs_without()
            for instruction in invar_order:
                if self.dom_predicate(instruction, cycle, preheader):
                    changed = True
                    self.graph.delete_instruction(instruction)
                    preheader.insert_tail(instruction)
        return changed

    def constant_propagation(self):
        graph = deepcopy(self.graph)
        self.graph.slice()
        lattice = self.fill_lattice()
        self.graph = graph
        # print(lattice)
        changed = self.place_constants(lattice)
        return changed

    def place_constants(self, lattice):
        changed = False
        for v in self.graph.vertexes:
            for i, instr in enumerate(v.block):
                # print(instr)
                if instr.place_constants(lattice):
                    changed = True
                if isinstance(instr, BinaryAssign):
                    v.block[i] = instr.simplify()
                # print(instr)
        return changed

    def fill_lattice(self):
        flowWL = set()
        SSAWL = set()
        lattice = ConstantLattice()
        exec_flag = {}
        for v in self.graph.vertexes:
            for instr in v.block:
                if isinstance(instr, FuncDefInstruction):
                    for arg in instr.arguments:
                        lattice.sl[arg.name] = ConstantLatticeElement.LOW
                        if arg.dimentions is not None:
                            for d in arg.dimentions:
                                lattice.sl[d] = ConstantLatticeElement.LOW
                if isinstance(instr, ArrayInitInstruction):
                    lattice.sl[instr.name] = ConstantLatticeElement.LOW
                if is_assign(instr):
                    if instr.dimentions is None:
                        lattice.init_value(instr.value)
            for out_v in v.output_vertexes:
                exec_flag[(v, out_v)] = False
        for out_v in self.graph.vertexes[0].output_vertexes:
            flowWL.add((self.graph.vertexes[0], out_v))

        while len(flowWL) != 0 or len(SSAWL) != 0:
            if len(flowWL) != 0:
                e = flowWL.pop()
                # print("flow", e[1].block[0])
                # print(e[0].number, e[1].number)
                if not exec_flag[e]:
                    exec_flag[e] = True
                    if len(e[1].block) == 0 and len(e[1].output_vertexes) != 0:
                        flowWL.add((e[1], e[1].output_vertexes[0]))
                        continue
                    if isinstance(e[1].block[0], PhiAssign):
                        self.visit_phi(e[1].block[0], lattice, e[1], flowWL, SSAWL)
                    elif self.edge_count(e[1], exec_flag) == 1:
                        self.visit_inst(e[1], e[1].block[0], lattice, flowWL, SSAWL)

            if len(SSAWL) != 0:
                e = SSAWL.pop()
                # print("ssa", e[1].block[0])
                if isinstance(e[1].block[0], PhiAssign):
                    self.visit_phi(e[1].block[0], lattice, e[1], flowWL, SSAWL)
                elif self.edge_count(e[1], exec_flag) >= 1:
                    self.visit_inst(e[1], e[1].block[0], lattice, flowWL, SSAWL)
        return lattice

    def edge_count(self, v, exec_flag):
        i = 0
        for in_v in v.input_vertexes:
            if exec_flag[(in_v, v)]:
                i += 1
        return i

    def visit_phi(self, phi_instr, lattice, v, flowWL, SSAWL):
        old = lattice.sl[phi_instr.value]
        for arg in phi_instr.arguments:
            lattice.sl[phi_instr.value] = lattice.meet(phi_instr.value, arg.value)
        flowWL.add((v, v.output_vertexes[0]))
        if lattice.sl[phi_instr.value] != old:
            ssa_succs = self.graph.ssa_succ(phi_instr.value)
            for succ in ssa_succs:
                SSAWL.add((v, succ))

    def visit_inst(self, v, instr, lattice, flowWL, SSAWL):
        if isinstance(instr, (FuncDefInstruction, ReturnInstruction, ArrayInitInstruction)) or (
                is_assign(instr) and instr.dimentions is not None):
            if len(v.output_vertexes) != 0:
                flowWL.add((v, v.output_vertexes[0]))
            return
        val = instr.lat_eval(lattice)
        if isinstance(instr, IsTrueInstruction) or val != lattice.sl[instr.value]:
            # print("a00", instr, val)
            if is_assign(instr):
                lattice.sl[instr.value] = lattice.meet(instr.value, val)
                ssa_succs = self.graph.ssa_succ(instr.value)
                for succ in ssa_succs:
                    SSAWL.add((v, succ))
            for out_v in v.output_vertexes:
                flowWL.add((v, out_v))

    def dead_code_elimination(self):
        changed = self.remove_unreachable_ways()
        # print(1, changed)
        changed = self.remove_useless_operations() or changed
        # print(2, changed)
        if changed:
            changed = self.remove_empty_blocks() or changed
        # print(3, changed)
        return changed

    def is_critical_instruction(self, instruction):
        return isinstance(instruction,
                          (IsTrueInstruction, ReturnInstruction, ArrayInitInstruction, FuncDefInstruction)) or (
                isinstance(instruction,
                           (AtomicAssign, BinaryAssign, UnaryAssign)) and instruction.dimentions is not None)

    def get_assign_for_op(self, op):
        for v in self.graph.vertexes:
            for instr in v.block:
                if is_assign(instr) and instr.is_def(op):
                    return instr
        return None

    def remove_useless_operations(self):
        mark = set()
        worklist = set()
        for v in self.graph.vertexes[1:]:
            for instr in v.block:
                if self.is_critical_instruction(instr):
                    mark.add(instr)
                    worklist.add(instr)
        if len(worklist) == 0:
            return False
        while len(worklist) != 0:
            instr = worklist.pop()
            operands = instr.get_operands()
            for op in operands:
                if isinstance(op, IdOperand):
                    def_instr = self.get_assign_for_op(op)
                    # print(op, def_instr)
                    if def_instr is not None:
                        if def_instr not in mark:
                            mark.add(def_instr)
                            worklist.add(def_instr)
        # for instr in mark:
        #    print(instr)
        on_delete = set()
        for v in self.graph.vertexes[1:]:
            for instr in v.block:
                if instr not in mark:
                    on_delete.add(instr)
        for instr in on_delete:
            self.graph.delete_instruction(instr)
        on_delete = set(filter(lambda x: not isinstance(x, PhiAssign), on_delete))
        return (len(on_delete)) != 0

    def remove_unreachable_ways(self):
        self.graph.mark_dfs()
        changed = self.graph.remove_non_reachable()
        self.remove_constant_branches()
        return changed

    def remove_constant_branches(self):
        on_delete = set()
        for v in self.graph.vertexes[1:]:
            for instr in v.block:
                if isinstance(instr, IsTrueInstruction) and isinstance(instr.value, BoolConstantOperand):
                    on_delete.add(instr)
        for br in on_delete:
            self.graph.delete_instruction(br)

    def remove_empty_blocks(self):
        changed = False
        empty_blocks = self.graph.get_empty_blocks()
        if len(empty_blocks) != 0:
            changed = True
        while len(empty_blocks) != 0:
            block = empty_blocks.pop()
            self.graph.remove_block(block)
        self.graph.remove_fluous_edges()
        return changed

    def copy_propagation(self):
        changed = False
        names = {}
        for v in self.graph.vertexes:
            for instruction in v.block:
                if isinstance(instruction, AtomicAssign) and isinstance(instruction.argument,
                                                                        IdOperand) and instruction.dimentions is None:
                    names[instruction.value] = instruction.argument.value

        for name in names.keys():
            # print(name, names[name])
            for v in self.graph.vertexes:
                for instruction in v.block:
                    if instruction.is_use_op(name) and not isinstance(instruction, PhiAssign):
                        instruction.replace_operand(name, names[name])
                        changed = True
        return changed

    def remove_ssa(self):
        self.remove_phi()
        self.remove_versions()
        self.update_names()

    def remove_phi(self):
        for v in self.graph.vertexes:
            on_delete = []
            for i, instr in enumerate(v.block):
                if isinstance(instr, PhiAssign):
                    on_delete.append(i)
            for i in sorted(on_delete, reverse=True):
                del v.block[i]

    def remove_versions(self):
        for v in self.graph.vertexes:
            for instr in v.block:
                instr.remove_versions()

    def update_names(self):
        self.names = set()
        for v in self.graph.vertexes:
            for instr in v.block:
                if is_assign(instr) and instr.dimentions is None and len(instr.value.split("$")) == 1:
                    self.names.add((instr.value, instr.type))

    def get_variables(self):
        variables = []
        for v in self.graph.vertexes:
            for instruction in v.block:
                if isinstance(instruction,
                              (AtomicAssign, BinaryAssign, UnaryAssign)) and instruction.dimentions is None:
                    variables.append(instruction.value)
                if isinstance(instruction, PhiAssign):
                    variables.append(instruction.value)
                if isinstance(instruction, FuncDefInstruction):
                    for arg in instruction.arguments:
                        if arg.dimentions is None:
                            variables.append(arg.name)
                        else:
                            for d in arg.dimentions:
                                variables.append(d)
        return variables

    def get_int_variables(self):
        variables = []
        for v in self.graph.vertexes:
            for instruction in v.block:
                if isinstance(instruction,
                              (AtomicAssign, BinaryAssign,
                               UnaryAssign)) and instruction.dimentions is None and (
                        instruction.type == "int" or instruction.type == "bool"):
                    variables.append(instruction.value)
                if isinstance(instruction, PhiAssign) and (instruction.type == "int" or instruction.type == "bool"):
                    variables.append(instruction.value)
                if isinstance(instruction, FuncDefInstruction):
                    for arg in instruction.arguments:
                        if arg.dimentions is None:
                            if arg.type == "int" or arg.type == "bool":
                                variables.append(arg.name)
                        else:
                            for d in arg.dimentions:
                                variables.append(d)
        return variables

    def get_float_variables(self):
        variables = []
        for v in self.graph.vertexes:
            for instruction in v.block:
                if isinstance(instruction,
                              (AtomicAssign, BinaryAssign,
                               UnaryAssign)) and instruction.dimentions is None and instruction.type == "float":
                    variables.append(instruction.value)
                if isinstance(instruction, PhiAssign) and instruction.type == "float":
                    variables.append(instruction.value)
                if isinstance(instruction, FuncDefInstruction):
                    for arg in instruction.arguments:
                        if arg.dimentions is None and arg.type == "float":
                            variables.append(arg.name)
        return variables

    def get_assign_instruction_and_block(self, var):
        for v in self.graph.vertexes:
            for instrunction in v.block:
                if isinstance(instrunction, (AtomicAssign, UnaryAssign,
                                             BinaryAssign)) and instrunction.dimentions is None and instrunction.value == var:
                    return instrunction, v
                if isinstance(instrunction, PhiAssign) and instrunction.value == var:
                    return instrunction, v
                if isinstance(instrunction, FuncDefInstruction):
                    for arg in instrunction.arguments:
                        if arg.dimentions is None and arg.name == var:
                            return instrunction, v
                        if arg.dimentions is not None:
                            for d in arg.dimentions:
                                if d == var:
                                    return instrunction, v

    def add_live(self, label, var):
        if label not in self.labels_to_live.keys():
            self.labels_to_live[label] = set()
        self.labels_to_live[label].add(var)

    def add_live_labels_list(self, labels, var):
        var = var.replace("$", "_")
        for label in labels:
            self.add_live(label, var)

    def build_lives_dfs_last(self, var, labels, vertex, pred, assign):
        breakable = False
        # print(var)
        for instruction in vertex.block:
            if instruction == assign:
                breakable = True
                break
            label = self.graph.instructions_to_labels[instruction]
            if len(labels) == 0 or not (labels[-1] == label):
                labels.append(label)
            if labels.count(label) > 2:
                breakable = True
                break
            if isinstance(instruction, PhiAssign):
                is_use = instruction.is_use_op_for_label(var, self.which_pred(vertex, pred))
            else:
                is_use = instruction.is_use_op(var)
            if is_use:
                self.add_live_labels_list(labels, var)
                breakable = True
                break
        if not breakable:
            for out_v in vertex.output_vertexes:
                self.build_lives_dfs(var, deepcopy(labels), out_v, vertex, assign)

    def build_lives_dfs(self, var, labels, vertex, pred, assign):
        breakable = False
        last = False
        for instruction in vertex.block:
            if instruction == assign:
                breakable = True
                break
            label = self.graph.instructions_to_labels[instruction]
            if label in labels and label != labels[-1]:
                last = True
                break
            if len(labels) == 0 or not (labels[-1] == label):
                labels.append(label)
            if isinstance(instruction, PhiAssign):
                is_use = instruction.is_use_op_for_label(var, self.which_pred(vertex, pred))
            else:
                is_use = instruction.is_use_op(var)
            if is_use:
                self.add_live_labels_list(labels, var)
        if not breakable:
            if last:
                self.build_lives_dfs_last(var, deepcopy(labels), vertex, pred, assign)
            else:
                for out_v in vertex.output_vertexes:
                    self.build_lives_dfs(var, deepcopy(labels), out_v, vertex, assign)

    def build_lives(self):
        self.graph.labels_dfs()
        variables = self.get_variables()

        for var in variables:
            labels = []
            assign, v = self.get_assign_instruction_and_block(var)
            find_assign = False
            for instruction in v.block:
                if instruction == assign:
                    find_assign = True
                    continue
                if not find_assign:
                    continue
                if not isinstance(instruction, PhiAssign):
                    label = self.graph.instructions_to_labels[instruction]
                    if len(labels) == 0 or not (labels[-1] == label):
                        labels.append(label)
                    if instruction.is_use_op(var):
                        self.add_live_labels_list(labels, var)
            for out_v in v.output_vertexes:
                self.build_lives_dfs(var, deepcopy(labels), out_v, v, assign)

    def not_phi_once(self, label, var, other_var):
        instructions = []
        for v in self.graph.vertexes:
            for instruction in v.block:
                if self.graph.instructions_to_labels[instruction] == label and isinstance(instruction, PhiAssign):
                    instructions.append(instruction)
        var_number = -1
        other_var_number = -1
        for instruction in instructions:
            if var_number == -1:
                var_number = instruction.operand_number(var)
            if other_var_number == -1:
                other_var_number = instruction.operand_number(other_var)

        return var_number == other_var_number or var_number == -1 or other_var_number == -1

    def find_place(self, block):
        j = len(block)
        is_br = False
        for instruction in block[::-1]:
            if isinstance(instruction, IsTrueInstruction):
                j -= 1
                is_br = True
            if isinstance(instruction, BinaryAssign) and instruction.is_cmp() and is_br:
                j -= 1
        return j

    def quit_ssa(self):
        for v in self.graph.vertexes:
            for instruction in v.block:
                if isinstance(instruction, PhiAssign):
                    assign1 = AtomicAssign(instruction.type, instruction.value, instruction.arguments[0], None)
                    assign2 = AtomicAssign(instruction.type, instruction.value, instruction.arguments[1], None)
                    assign1.is_phi = True
                    assign2.is_phi = True
                    v1 = v.input_vertexes[0]
                    v2 = v.input_vertexes[1]
                    if len(v1.block) != 0 and isinstance(v1.block[-1], IsTrueInstruction):
                        v1.block.insert(self.find_place(v1.block), assign1)
                    else:
                        v1.block.append(assign1)
                    if len(v2.block) != 0 and isinstance(v2.block[-1], IsTrueInstruction):
                        v2.block.insert(self.find_place(v2.block), assign2)
                    else:
                        v2.block.append(assign2)
            while len(v.block) > 0 and isinstance(v.block[0], PhiAssign):
                v.block.pop(0)

    def get_declared_arrays(self):
        arrays = []
        for v in self.graph.vertexes:
            for instruction in v.block:
                if isinstance(instruction, ArrayInitInstruction):
                    arrays.append((instruction.name, instruction.dimentions, instruction.assign))
        return arrays

    def is_perfect_nest(self, nest):
        nest = sorted(nest, key=lambda x: len(x), reverse=True)
        pairs = []
        for i, cycle in enumerate(nest):
            pairs += [cycle[0], cycle[1]]
            if i > 0:
                header = cycle[1]
                for v in header.input_vertexes:
                    if v != cycle[0]:
                        pairs.append(v)
                        break
        biggest = nest[0]
        nest_body = []
        for block in biggest:
            if block not in pairs and block not in nest[-1]:
                return False, nest_body
            if block not in pairs:
                nest_body.append(block)
        return True, nest_body

    def get_full_exp(self, exp, block):
        if isinstance(exp, AtomicAssign):
            if isinstance(exp.argument, (IntConstantOperand, FloatConstantOperand)):
                return str(exp.argument)
            if "$" in exp.argument.value:
                for instr in block:
                    if instr.value == exp.argument.value:
                        return self.get_full_exp(instr, block)
            else:
                return str(exp.argument)
        if isinstance(exp, UnaryAssign):
            if isinstance(exp.arg, (IntConstantOperand, FloatConstantOperand)):
                return exp.op + str(exp.arg)
            if "$" in exp.arg.value:
                for instr in block:
                    if instr.value == exp.arg.value:
                        return exp.op + self.get_full_exp(instr, block)
            else:
                return exp.op + str(exp.arg)
        if isinstance(exp, BinaryAssign):
            left, right = "", ""
            if isinstance(exp.left, (IntConstantOperand, FloatConstantOperand)):
                left = str(exp.left)
            elif "$" in exp.left.value:
                for instr in block:
                    if instr.value == exp.left:
                        left = self.get_full_exp(instr, block)
            else:
                left = str(exp.left)
            if isinstance(exp.right, (IntConstantOperand, FloatConstantOperand)):
                right = str(exp.right)
            elif "$" in exp.right.value:
                for instr in block:
                    if instr.value == exp.right.value:
                        right = self.get_full_exp(instr, block)
            else:
                right = str(exp.right)
            return left + exp.op + right

    def get_full_exp_instr(self, exp, block):
        if isinstance(exp, AtomicAssign):
            if isinstance(exp.argument, (IntConstantOperand, FloatConstantOperand)):
                return [exp.argument]
            if "$" in exp.argument.value:
                for instr in block:
                    if instr.value == exp.argument.value:
                        return [exp.argument] + self.get_full_exp(instr, block)
            else:
                return [exp.argument]
        if isinstance(exp, UnaryAssign):
            if isinstance(exp.arg, (IntConstantOperand, FloatConstantOperand)):
                return [exp]
            if "$" in exp.arg.value:
                for instr in block:
                    if instr.value == exp.arg.value:
                        return [exp] + self.get_full_exp(instr, block)
            else:
                return [exp]
        if isinstance(exp, BinaryAssign):
            left, right = [], []
            if isinstance(exp.left, (IntConstantOperand, FloatConstantOperand)):
                left = []
            elif "$" in exp.left.value:
                for instr in block:
                    if instr.value == exp.left:
                        left = self.get_full_exp(instr, block)
            else:
                left = []
            if isinstance(exp.right, (IntConstantOperand, FloatConstantOperand)):
                right = []
            elif "$" in exp.right.value:
                for instr in block:
                    if instr.value == exp.right.value:
                        right = self.get_full_exp(instr, block)
            else:
                right = []
            return [exp] + left + right

    def get_full_array_exp(self, exp, block, indexes):
        if isinstance(exp, AtomicAssign):
            if not isinstance(exp.argument, ArrayUseOperand):
                if exp.value in indexes:
                    return None
                else:
                    return []
            else:
                array_name = exp.argument.name
                array_indexes = []
                if len(exp.argument.indexing) != len(indexes) - 1:
                    return None
                for dim in exp.argument.indexing:
                    if isinstance(dim, IntConstantOperand):
                        return None
                    if "$" in dim.value:
                        for instr in block:
                            if instr.value == dim.value:
                                array_indexes.append(self.get_full_exp(instr, block))
                                break
                    else:
                        array_indexes.append(dim.value)
                array_gen = (array_name, array_indexes)
                return [array_gen]
        if isinstance(exp, UnaryAssign):
            if "$" in exp.arg.value:
                for instr in block:
                    if instr.value == exp.arg.value:
                        return self.get_full_array_exp(instr, block, indexes)
            else:
                if exp.arg.value in indexes:
                    return None
                else:
                    return []
        if isinstance(exp, BinaryAssign):
            left, right = [], []
            if isinstance(exp.left, (IntConstantOperand, FloatConstantOperand)):
                left = []
            elif "$" in exp.left.value:
                for instr in block:
                    if instr.value == exp.left.value:
                        left = self.get_full_array_exp(instr, block, indexes)
                        if left is None:
                            return None
            else:
                if exp.left.value in indexes:
                    return None
                else:
                    left = []
            if isinstance(exp.right, (IntConstantOperand, FloatConstantOperand)):
                right = []
            elif "$" in exp.right.value:
                for instr in block:
                    if instr.value == exp.right.value:
                        right = self.get_full_array_exp(instr, block, indexes)
                        if right is None:
                            return None
            else:
                if exp.right.value in indexes:
                    return None
                else:
                    right = []
            return left + right

    def get_cycle_blocks(self, cycle):
        latch = cycle[0]
        header = cycle[1]
        enter = None
        for v in header.input_vertexes:
            if v != latch:
                enter = v
        after = None
        for v in latch.output_vertexes:
            if v != header:
                after = v
        return enter, after

    def get_cycle_index_info(self, cycle):
        latch = cycle[0]
        header = cycle[1]
        if len(header.input_vertexes) != 2:
            return None
        enter = None
        for v in header.input_vertexes:
            if v != latch:
                enter = v
        index_increment = latch.block[0]
        if isinstance(index_increment,
                      BinaryAssign) and index_increment.value == index_increment.left.value and isinstance(
            index_increment.right, IntConstantOperand) and index_increment.right.value == 1:
            index_name = index_increment.value
        else:
            return None
        start = None
        for instruction in enter.block[::-1]:
            if isinstance(instruction, AtomicAssign) and instruction.value == index_name:
                start = self.get_full_exp(instruction, enter.block)
        if start is None:
            return None
        # print(index_name, start)
        cmp = latch.block[-2]
        if not (isinstance(cmp, BinaryAssign) and cmp.op == "<" and cmp.left.value == index_name):
            return None
        end = None
        if isinstance(cmp.right, IdOperand) and "$" in cmp.right.value:
            for instr in latch.block:
                if instr.value == cmp.right.value:
                    end = self.get_full_exp(instr, latch.block)
                    break
        else:
            end = str(cmp.right)
        if end is None:
            return None
        return index_name, start, end

    def get_nest_body_info(self, nest_body, indexes):
        n_arrays = 0
        array_gen, array_in = None, None
        for instruction in nest_body.block:
            if isinstance(instruction, AtomicAssign):
                if instruction.dimentions is None:
                    if "$" not in instruction.value:
                        return None
                else:
                    if len(instruction.dimentions) != len(indexes) - 1:
                        return None
                    n_arrays += 1
                    if n_arrays > 1:
                        return None
                    array_name = instruction.value
                    array_indexes = []
                    for dim in instruction.dimentions:
                        if isinstance(dim, IntConstantOperand):
                            return None
                        if "$" in dim.value:
                            for instr in nest_body.block:
                                if instr.value == dim.value:
                                    array_indexes.append(self.get_full_exp(instr, nest_body.block))
                                    break
                        else:
                            array_indexes.append(dim.value)
                    array_gen = (array_name, array_indexes)
                    array_in = []
                    if not isinstance(instruction.argument, IdOperand) or "$" not in instruction.argument.value:
                        return None
                    for instr in nest_body.block:
                        if instr.value == instruction.argument.value:
                            array_in = self.get_full_array_exp(instr, nest_body.block, indexes)
                            break
                    if array_in is None or len(array_in) == 0:
                        return None

        if n_arrays == 0:
            return None

        return array_gen, array_in

    def get_index_constants(self, array_use):
        pattern = r'^([a-zA-Z][a-zA-Z0-9]*)([+-]\d+)?$'
        indexes = []
        for index in array_use:
            match = re.match(pattern, index)
            if match:
                id_value = match.group(1)
                constant = match.group(2)
                if constant is not None:
                    constant = int(constant)
                indexes.append((id_value, constant))
            else:
                return None
        return indexes

    def analyze_array_use(self, array_use, indexes):
        indexing = array_use[1]
        indexing = self.get_index_constants(indexing)
        if indexing is None:
            return None
        array_name = array_use[0]
        inds = []
        for i, idx in enumerate(indexing):
            idx_name = idx[0]
            if idx_name != indexes[i]:
                return None
            value = idx[1]
            if value is None:
                value = 0
            inds.append(value)
        return array_name, inds

    def analyze_dep(self, u, v, gran):
        n_dims = len(u)
        for i in range(n_dims):
            low = gran[i][0] if isinstance(gran[i][0], int) else 0
            if isinstance(gran[i][1], int):
                high = gran[i][1]
            else:
                continue
            const = v[i] - u[i]
            if (high - low) <= abs(const):
                return None, None
        distance = [a - b for a, b in zip(u, v)]
        if not any(comp < 0 for comp in distance):
            return None, None
        carriers = []
        potential_carriers = []
        carriers.append(0)
        for i in range(n_dims):
            const = v[i] - u[i]
            if const == 0:
                potential_carriers.append(i + 1)
                continue
            elif const < 0:
                carriers += potential_carriers
                carriers.append(i + 1)
            break
        return distance, carriers

    def tiling_nest(self, nest):
        is_perfect, nest_body = self.is_perfect_nest(nest)
        if not is_perfect or len(nest_body) != 1:
            return
        nest = sorted(nest, key=lambda x: len(x), reverse=True)
        loops_info = []
        for cycle in nest:
            info = self.get_cycle_index_info(cycle)
            if info[1].isdigit():
                info = (info[0], int(info[1]), info[2])
            if info[2].isdigit():
                info = (info[0], info[1], int(info[2]))
            loops_info.append(info)
            if info is None:
                return
        print(loops_info)
        indexes = list(map(lambda x: x[0], loops_info))
        body_info = self.get_nest_body_info(nest_body[0], indexes)
        if body_info is None:
            return
        array_gen = self.analyze_array_use(body_info[0], indexes[1:])
        if array_gen is None:
            return None
        array_uses = []
        for use in body_info[1]:
            array_use = self.analyze_array_use(use, indexes[1:])
            if array_use is None:
                return None
            array_uses.append(array_use)
        print(array_gen)
        print(array_uses)
        distances = []
        indexes_gran = []
        for info in loops_info[1:]:
            indexes_gran.append((info[1], info[2]))
        for use in array_uses:
            if use[0] == array_gen[0]:
                distance, carriers = self.analyze_dep(array_gen[1], use[1], indexes_gran)
                if distance is not None:
                    distances.append((distance, carriers))
                distance, carriers = self.analyze_dep(use[1], array_gen[1], indexes_gran)
                if distance is not None:
                    distances.append((distance, carriers))
        print(distances)
        if len(distances) == 0:
            self.rectangular_tiling(nest, indexes)
        else:
            self.skewed_tiling(nest, indexes, distances)

    def rectangular_tiling(self, nest, indexes):
        n_cycles = len(nest)
        if n_cycles == 2:
            tile_sizes = tile_sizes1
        else:
            tile_sizes = tile_sizes2
        cycles_pairs = []
        enter_all, after_all = self.get_cycle_blocks(nest[0])
        self.graph.vertexes.remove(enter_all)
        enter_all = enter_all.input_vertexes[0]
        body = Vertex.init_empty_vertex()
        body.block = nest[-1][2].block
        for i in range(n_cycles):
            d = tile_sizes[i]
            latch = nest[i][0]
            enter, after = self.get_cycle_blocks(nest[i])
            start = None
            for instruction in enter.block[::-1]:
                if isinstance(instruction, AtomicAssign) and instruction.value == indexes[i]:
                    start = self.get_full_exp_instr(instruction, enter.block)
            cmp = latch.block[-2]
            end = None
            if isinstance(cmp.right, IdOperand) and "$" in cmp.right.value:
                for instr in latch.block:
                    if instr.value == cmp.right.value:
                        end = self.get_full_exp_instr(instr, latch.block)
                        break
            else:
                end = [cmp.right]
            cycle_enter = Vertex.init_empty_vertex()
            cycle_enter.block += start[1:]
            cycle_enter.block.append(AtomicAssign('int', indexes[i] + "!0", start[0], None))
            cycle_enter.block += end[1:]
            cmp_name = self.get_tmp()
            cycle_enter.block.append(
                BinaryAssign('int', cmp_name, "div", end[0], IntConstantOperand(d), None, 'int', 'int'))
            br_name = self.get_tmp()
            cycle_enter.block.append(
                BinaryAssign("bool", br_name, "<", IdOperand(indexes[i] + "!0"), IdOperand(cmp_name), None, 'int',
                             'int'))
            cycle_enter.block.append(IsTrueInstruction(IdOperand(br_name)))
            header_block = Vertex.init_empty_vertex()
            cycle_enter.add_output_connector(header_block)
            header_block.add_input_connector(cycle_enter)
            latch_block = Vertex.init_empty_vertex()
            latch_block.block.append(
                BinaryAssign('int', indexes[i] + "!0", "+", IdOperand(indexes[i] + "!0"), IntConstantOperand(1), None,
                             'int', 'int'))
            latch_block.block += end[1:]
            cmp_name = self.get_tmp()
            latch_block.block.append(
                BinaryAssign('int', cmp_name, "div", end[0], IntConstantOperand(d), None, 'int', 'int'))
            br_name = self.get_tmp()
            latch_block.block.append(
                BinaryAssign("bool", br_name, "<", IdOperand(indexes[i] + "!0"), IdOperand(cmp_name), None, 'int',
                             'int'))
            latch_block.block.append(IsTrueInstruction(IdOperand(br_name)))
            latch_block.add_output_connector(header_block)
            header_block.add_input_connector(latch_block)
            cycle1 = (cycle_enter, header_block, latch_block)

            cycle_enter = Vertex.init_empty_vertex()
            init_tmp = self.get_tmp()
            cycle_enter.block.append(
                BinaryAssign('int', init_tmp, '*', IdOperand(indexes[i] + "!0"), IntConstantOperand(d), None, 'int',
                             'int'))
            cycle_enter.block.append(AtomicAssign('int', indexes[i] + "!1", IdOperand(init_tmp), None))
            add_name = self.get_tmp()
            cycle_enter.block.append(
                BinaryAssign('int', add_name, "+", IdOperand(indexes[i] + "!0"), IntConstantOperand(1), None, 'int',
                             'int'))
            mul_name = self.get_tmp()
            cycle_enter.block.append(
                BinaryAssign('int', mul_name, '*', IdOperand(add_name), IntConstantOperand(d), None, 'int', 'int'))
            br_name = self.get_tmp()
            cycle_enter.block.append(
                BinaryAssign("bool", br_name, "<", IdOperand(indexes[i] + "!1"), IdOperand(mul_name), None, 'int',
                             'int'))
            cycle_enter.block.append(IsTrueInstruction(IdOperand(br_name)))
            header_block = Vertex.init_empty_vertex()
            cycle_enter.add_output_connector(header_block)
            header_block.add_input_connector(cycle_enter)
            latch_block = Vertex.init_empty_vertex()
            latch_block.block.append(
                BinaryAssign('int', indexes[i] + "!1", "+", IdOperand(indexes[i] + "!1"), IntConstantOperand(1), None,
                             'int', 'int'))
            add_name = self.get_tmp()
            latch_block.block.append(
                BinaryAssign('int', add_name, "+", IdOperand(indexes[i] + "!0"), IntConstantOperand(1), None, 'int',
                             'int'))
            mul_name = self.get_tmp()
            latch_block.block.append(
                BinaryAssign('int', mul_name, '*', IdOperand(add_name), IntConstantOperand(d), None, 'int', 'int'))
            br_name = self.get_tmp()
            latch_block.block.append(
                BinaryAssign("bool", br_name, "<", IdOperand(indexes[i] + "!1"), IdOperand(mul_name), None, 'int',
                             'int'))
            latch_block.block.append(IsTrueInstruction(IdOperand(br_name)))
            latch_block.add_output_connector(header_block)
            header_block.add_input_connector(latch_block)
            cycle2 = (cycle_enter, header_block, latch_block)
            cycles_pairs.append((cycle1, cycle2))

        one = [a for a, b, in cycles_pairs]
        two = [b for a, b in cycles_pairs]
        cycles_pairs = one + two
        for vertex in nest[0]:
            self.graph.vertexes.remove(vertex)
        enter_all.output_vertexes = []
        after_all.input_vertexes = []
        enter, after = enter_all, after_all
        for i, cycle in enumerate(cycles_pairs):
            for elem in cycle:
                self.graph.vertexes.append(elem)
            cycle[0].add_input_connector(enter)
            enter.add_output_connector(cycle[0])
            cycle[0].add_output_connector(after)
            after.add_input_connector(cycle[0])
            cycle[2].add_output_connector(after)
            after.add_input_connector(cycle[2])
            enter = cycle[1]
            after = cycle[2]
            if i == len(cycles_pairs) - 1:
                cycle[1].add_output_connector(body)
                body.add_input_connector(cycle[1])
                body.add_output_connector(cycle[2])
                cycle[2].add_input_connector(body)
                self.graph.vertexes.append(body)
        for index in indexes:
            self.names.remove((index, "int"))
            self.names.add((index + "!0", "int"))
            self.names.add((index + "!1", "int"))
            self.replace_name(body, index, index + "!1")
        print("tiled")

    def get_skew_matrix(self, distances):
        S = []
        for distance in distances:
            skew_matrix = np.eye(len(distances[0][0]) + 1, dtype=int)
            vector, carriers = distance[0], distance[1]
            for i, component in enumerate(vector):
                if component < 0:
                    for carrier in carriers:
                        skew_matrix[i + 1][carrier] = abs(component)
            S.append(skew_matrix)
        result_skew_matrix = np.eye(len(distances[0][0]) + 1, dtype=int)
        for i in range(len(distances[0][0]) + 1):
            for j in range(len(distances[0][0]) + 1):
                result_skew_matrix[i][j] = max(list(map(lambda x: x[i][j], S)))
        return result_skew_matrix

    def skewed_tiling(self, nest, indexes, distances):
        skew_matrix = self.get_skew_matrix(distances)
        print(skew_matrix)

    def tiling(self):
        loop_nests = self.graph.find_loop_nests()
        for nest in loop_nests:
            self.tiling_nest(nest)

    def replace_name(self, block, old, new):
        for instruction in block.block:
            instruction.replace_operand(old, new)
