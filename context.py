from graph import *
from lattice import *


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

    def set_contexts(self, contexts):
        self.contexts = contexts

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
            self.change_numeration_by_name(name)

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
            using_set = self.graph.get_all_assign(name)
            places = self.graph.make_dfp(using_set)
            for place in places:
                phi_args = []
                for _ in place.input_vertexes:
                    phi_args.append(name)
                phi_args = list(map(lambda x: IdOperand(x), phi_args))
                phi_expr = PhiAssign(name, phi_args)
                place.insert_head(phi_expr)

    def loop_invariant_code_motion(self):
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
            changed = self.lycm_cycle(cycle) or changed
        return changed

    def lycm_cycle(self, cycle):
        invar_order = self.mark_invar(cycle)
        # for inst in invar_order:
        #    print(inst)
        changed = self.move_invars(invar_order, cycle)
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
        return isinstance(operand, IntConstantOperand) or isinstance(operand, BoolConstantOperand)

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
                operands = instruction.get_operands()
                for operand in operands:
                    # print(f"{instruction}: {operand}: {self.check_inv_operand(operand, block, cycle, instruction, inst_invar)}")
                    is_inv = is_inv and self.check_inv_operand(operand, block, cycle, instruction, inst_invar)
                if isinstance(instruction, AtomicAssign) and isinstance(instruction.argument,
                                                                        FuncCallOperand) and not self.is_pure_function(
                    instruction.argument.name):
                    is_inv = False
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
        subgraph = Graph()
        subgraph.vertexes = [preheader] + cycle + exits
        subgraph.build_dominators_tree()
        # print(instruction, self.dom_uses(instruction, cycle), self.dom_exits(instruction, subgraph, exits))
        is_pred = self.dom_uses(instruction, cycle) and self.dom_exits(instruction, subgraph, exits)
        self.graph.clean_dominators()
        return is_pred

    def move_invars(self, invar_order, cycle):
        changed = False
        if len(invar_order) != 0:
            preheader = self.graph.create_preheader(cycle)
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
                if is_assign(instr):
                    lattice.init_value(instr.value)
            for out_v in v.output_vertexes:
                exec_flag[(v, out_v)] = False
        for out_v in self.graph.vertexes[0].output_vertexes:
            flowWL.add((self.graph.vertexes[0], out_v))

        while len(flowWL) != 0 or len(SSAWL) != 0:
            if len(flowWL) != 0:
                e = flowWL.pop()
                # print("flow", e[1].block[0])
                if not exec_flag[e]:
                    exec_flag[e] = True
                    if len(e[1].block) == 0:
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
            # print(in_v.number, v.number)
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
        if isinstance(instr, (FuncDefInstruction, FuncCallInstruction, ReturnInstruction)):
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
        return isinstance(instruction, (IsTrueInstruction, ReturnInstruction)) or (
                isinstance(instruction, FuncCallInstruction) and not self.is_pure_function(instruction.name)) or (
                       isinstance(instruction, AtomicAssign) and isinstance(instruction.argument,
                                                                            FuncCallOperand) and not self.is_pure_function(
                   instruction.argument.name))

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

    def is_pure_function(self, func_name):
        if func_name == "print" or func_name == "input":
            return False
        # print(func_name, self.contexts[func_name].graph.is_pure_function())
        return self.contexts[func_name].graph.is_pure_function()

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
                if is_assign(instr) and len(instr.value.split("$")) == 1:
                    self.names.add(instr.value)
