from IR import *
from collections import deque
from copy import deepcopy
import hashlib
import time
import random


def generate_unique_number():
    random_number = random.randint(0, 999999)

    current_time = int(time.time() * 1000)

    data = str(random_number) + str(current_time)

    unique_hash = hashlib.sha256(data.encode()).hexdigest()

    unique_number = int(unique_hash, 16)

    return unique_number


class Color(Enum):
    WHITE = 0
    GRAY = 1
    BLACK = 2


class Vertex:
    def __init__(self, block, input_vertexes, output_vertexes):
        self.block = block
        self.input_vertexes = input_vertexes
        self.output_vertexes = output_vertexes
        self.idom = None
        self.children = []
        self.number = generate_unique_number()
        self.checked = False
        self.dfs_number = None
        self.label = None
        self.color = None
        self.inB = set()
        self.outB = set()

    def replace_number(self):
        self.number = generate_unique_number()

    @staticmethod
    def init_empty_vertex():
        return Vertex([], [], [])

    def add_child(self, child):
        self.children.append(child)

    def insert_head(self, expr):
        self.block.insert(0, expr)

    def insert_tail(self, expr):
        self.block.append(expr)

    def add_output_connector(self, to):
        self.output_vertexes.append(to)

    def add_input_connector(self, from_v):
        self.input_vertexes.append(from_v)

    def to_graph(self, file):
        file.write("\t" + str(self.number) + "[label=\"\n")
        if self.label is not None:
            file.write("\t\t" + self.label + ":\n")
        for elem in self.block:
            file.write("\t\t" + str(elem) + "\n")
        file.write("\t\"]\n")
        for i, elem in enumerate(self.output_vertexes):
            if len(self.output_vertexes) == 2:
                if i == 0:
                    file.write("\t" + str(self.number) + "->" + str(elem.number) + "[label=\"Y\"]" + "\n")
                else:
                    file.write("\t" + str(self.number) + "->" + str(elem.number) + "[label=\"N\"]" + "\n")
            else:
                file.write("\t" + str(self.number) + "->" + str(elem.number) + "\n")
        for elem in self.children:
            file.write("\t" + str(self.number) + "->" + str(elem.number) + " [color = green]")

    def to_graph_rd(self, file, graph):
        file.write("\t" + str(self.number) + "[label=\"\n")
        in_b = "{"
        for i, p in enumerate(list(self.inB)):
            in_b += str(p)
            if i != len(self.inB) - 1:
                in_b += ", "
        in_b += "}"
        out_b = "{"
        for i, p in enumerate(list(self.outB)):
            out_b += str(p)
            if i != len(self.outB) - 1:
                out_b += ", "
        out_b += "}"
        file.write("\t\tInB = " + in_b + "\n")
        for elem in self.block:
            if is_assign(elem):
                file.write("\t\t" + str(graph.assign2point[elem]) + ": " + str(elem) + "\n")
            else:
                file.write("\t\t" + str(elem) + "\n")
        file.write("\t\tOutB = " + out_b)
        file.write("\t\"]\n")
        for i, elem in enumerate(self.output_vertexes):
            if len(self.output_vertexes) == 2:
                if i == 0:
                    file.write("\t" + str(self.number) + "->" + str(elem.number) + "[label=\"Y\"]" + "\n")
                else:
                    file.write("\t" + str(self.number) + "->" + str(elem.number) + "[label=\"N\"]" + "\n")
            else:
                file.write("\t" + str(self.number) + "->" + str(elem.number) + "\n")


class Graph:
    def __init__(self):
        self.vertexes = []
        self.DF = {}
        self.cycles_pairs = []
        self.cycles = []
        self.point2assign = {}
        self.assign2point = {}
        self.instructions_to_labels = {}
        self.labels_to_instructions = {}

    def add_vertex(self):
        vertex = Vertex.init_empty_vertex()
        self.vertexes.append(vertex)
        return vertex

    def make_p2a(self):
        self.point2assign = {value: key for key, value in self.assign2point.items()}

    def slice(self):
        new_vertexes = []
        for v in self.vertexes:
            if len(v.block) == 0 or len(v.block) == 1:
                new_vertexes.append(v)
                continue
            block_copy = deepcopy(v.block)
            prev_v = v
            v_out = v.output_vertexes
            v.output_vertexes = []
            for i, instr in enumerate(block_copy[1:]):
                v.block.pop(1)
                new_v = Vertex.init_empty_vertex()
                new_v.insert_tail(instr)
                new_v.add_input_connector(prev_v)
                prev_v.add_output_connector(new_v)
                prev_v = new_v
                if i == len(block_copy[1:]) - 1:
                    new_v.output_vertexes = v_out
                    for ver_out in v_out:
                        inputs = ver_out.input_vertexes
                        ver_out.input_vertexes = []
                        for v_in in inputs:
                            if v_in == v:
                                ver_out.add_input_connector(new_v)
                            else:
                                ver_out.add_input_connector(v_in)
                new_vertexes.append(new_v)
            new_vertexes.append(v)
        self.vertexes = new_vertexes

    def make_DF(self):
        post_order = self.generate_post_order()
        for elem in post_order:
            self.DF[elem] = set()
            for succ in elem.output_vertexes:
                if succ.idom != elem:
                    self.DF[elem].add(succ)
            for child in elem.children:
                for v in self.DF[child]:
                    if v.idom != elem:
                        self.DF[elem].add(v)

    def dfs(self):
        self.assign2point = {}
        self.point2assign = {}
        n = 0
        point = 0
        first = self.vertexes[0]
        stack = [first]
        for v in self.vertexes:
            v.checked = False

        while len(stack) != 0:
            current = stack.pop()
            current.checked = True
            current.dfs_number = n
            n += 1
            for instruction in current.block:
                if is_assign(instruction):
                    self.assign2point[instruction] = point
                    point += 1
            for next_v in current.output_vertexes:
                if not next_v.checked:
                    stack.append(next_v)
        self.make_p2a()
        self.remove_non_reachable()

    def labels_dfs(self):
        self.instructions_to_labels = {}
        first = self.vertexes[0]
        stack = [first]
        point = 0
        for v in self.vertexes:
            v.checked = False
        while len(stack) != 0:
            current = stack.pop()
            current.checked = True
            for i, instruction in enumerate(current.block):
                self.instructions_to_labels[instruction] = point
                if not isinstance(instruction, PhiAssign):
                    point += 1
                if isinstance(instruction, PhiAssign) and (
                        i == len(current.block) - 1 or not isinstance(current.block[i + 1], PhiAssign)):
                    point += 1
            for next_v in current.output_vertexes:
                if not next_v.checked:
                    stack.append(next_v)
        self.labels_to_instructions = {value: key for key, value in self.instructions_to_labels.items()}

    def dfs_without(self):
        n = 0
        first = self.vertexes[0]
        stack = [first]
        for v in self.vertexes:
            v.checked = False

        while len(stack) != 0:
            current = stack.pop()
            current.checked = True
            current.dfs_number = n
            n += 1
            for next_v in current.output_vertexes:
                if not next_v.checked:
                    stack.append(next_v)

    def remove_non_reachable(self):
        non_reachable = []
        for i, v in enumerate(self.vertexes):
            if not v.checked:
                non_reachable.append(i)
                for out_v in v.output_vertexes:
                    in_v = self.which_pred(out_v, v)
                    del out_v.input_vertexes[in_v]
        for i in sorted(non_reachable, reverse=True):
            del self.vertexes[i]
        return len(non_reachable) != 0

    def solve_rd(self):
        for v in self.vertexes:
            v.inB = set()
            v.outB = set()
        changed = True
        blocks = self.vertexes[1:]
        while changed:
            changed = False
            for block in blocks:
                for p in block.input_vertexes:
                    block.inB |= p.outB
                old = len(block.outB)
                block.outB = set(block.inB)
                for instruction in block.block:
                    if is_assign(instruction):
                        value = instruction.value
                        kill = set()
                        for point in block.outB:
                            if self.point2assign[point].value == value:
                                kill.add(point)
                        block.outB -= kill
                        block.outB.add(self.assign2point[instruction])
                if len(block.outB) != old:
                    changed = True

    def print_graph(self, file):
        for elem in self.vertexes:
            elem.to_graph(file)

    def print_graph_rd(self, file):
        for elem in self.vertexes:
            elem.to_graph_rd(file, self)

    def clean_dominators(self):
        for v in self.vertexes:
            v.children = []
            v.idom = None

    def generate_post_order(self):
        for elem in self.vertexes:
            elem.checked = False
        return self.generate_post_order_from(self.vertexes[0])

    def generate_post_order_from(self, start):
        if len(start.output_vertexes) == 0:
            if start.checked:
                return []
            start.checked = True
            return [start]
        else:
            if start.checked:
                return []
            start.checked = True
            result = []
            for elem in start.output_vertexes:
                local_post_order = self.generate_post_order_from(elem)
                result += local_post_order
            result.append(start)
            return result

    def build_dominators_tree(self):
        self.clean_dominators()
        first = self.vertexes[0]
        dominators = {}
        stack = []
        for elem in self.vertexes:
            dominators[elem] = []
        for elem in self.vertexes:
            for v in self.vertexes:
                v.checked = False
            elem.checked = True
            stack.append(first)
            while len(stack) != 0:
                current = stack.pop()
                current.checked = True
                for next in current.output_vertexes:
                    if not next.checked:
                        stack.append(next)
            for v in self.vertexes:
                if not v.checked:
                    dominators[v].append(elem)
        for elem in self.vertexes:
            maximum = None
            for v in dominators[elem]:
                if maximum is None or maximum.dfs_number < v.dfs_number:
                    maximum = v
            elem.idom = maximum
        for elem in self.vertexes:
            if elem.idom is not None:
                elem.idom.add_child(elem)
        first.add_child(first.output_vertexes[0])

    def get_all_assign(self, s):
        result = set()
        for elem in self.vertexes:
            for opp in elem.block:
                if (isinstance(opp, UnaryAssign) or isinstance(opp, BinaryAssign)) and opp.value == s:
                    result.add(elem)
                if isinstance(opp, AtomicAssign) and opp.value == s and opp.dimentions is None:
                    result.add(elem)
        return result

    def make_df_set(self, s):
        result = set()
        for elem in s:
            localResult = self.DF[elem]
            result = result.union(localResult)
        return result

    def make_dfp(self, s):
        changed = True
        dfp = self.make_df_set(s)
        prev = dfp.copy()
        while changed:
            changed = False
            s = s.union(dfp)
            dfp = self.make_df_set(s)
            if dfp != prev:
                changed = True
                prev = dfp.copy()
        return dfp

    def cycles_first_dfs(self, vertex):
        vertex.color = Color.GRAY
        for out_v in vertex.output_vertexes:
            if out_v.color == Color.WHITE:
                self.cycles_first_dfs(out_v)
            if out_v.color == Color.GRAY:
                self.cycles_pairs.append((vertex, out_v))
        vertex.color = Color.BLACK

    def cycles_second_dfs(self, pair):
        for v in self.vertexes:
            v.checked = False
            if v == pair[1]:
                v.checked = True
        cycle = [pair[0], pair[1]]
        stack = [pair[0]]
        while len(stack) != 0:
            v = stack.pop()
            if v != pair[0] and v != pair[1] and not v.checked:
                cycle.append(v)
            v.checked = True
            for out in v.input_vertexes:
                if not out.checked:
                    stack.append(out)
        self.cycles.append(cycle)

    def get_natural_cycles(self):
        self.cycles = []
        self.cycles_pairs = []
        for v in self.vertexes:
            v.color = Color.WHITE
        self.cycles_first_dfs(self.vertexes[0])
        for pair in self.cycles_pairs:
            self.cycles_second_dfs(pair)

    def bfs_cycle(self, cycle):
        for v in cycle:
            v.checked = False
        queue = deque([cycle[1]])
        order = []
        while queue:
            vertex = queue.popleft()
            if not vertex.checked and vertex in cycle:
                order.append(vertex)
                vertex.checked = True
                queue.extend(out for out in vertex.output_vertexes)
        return order

    def create_preheader(self, cycle):
        header = cycle[1]
        preheader = self.add_vertex()
        preheader.output_vertexes.append(header)
        on_delete = []
        for i, in_v in enumerate(header.input_vertexes):
            if in_v not in cycle:
                on_delete.append(i)
                preheader.input_vertexes.append(in_v)
        on_delete = sorted(on_delete, reverse=True)
        for i in on_delete:
            del header.input_vertexes[i]
        header.input_vertexes.append(preheader)
        for in_vert in preheader.input_vertexes:
            out_i = self.which_succ(in_vert, header)
            in_vert.output_vertexes[out_i] = preheader
        return preheader

    def delete_instruction(self, instruction):
        for v in self.vertexes:
            for i, inst in enumerate(v.block):
                if inst == instruction:
                    v.block.pop(i)
                    break

    def is_instruction_in_cycle(self, instruction, cycle):
        for v in cycle:
            for instr in v.block:
                if instr == instruction:
                    return True
        return False

    def get_block_by_instruction(self, instruction):
        for v in self.vertexes:
            for instr in v.block:
                if instr == instruction:
                    return v

    def get_all_uses_cycle_blocks(self, cycle, block, value):
        blocks = []
        for v in cycle:
            if v == block:
                continue
            for instr in v.block:
                if instr.is_use_op(value):
                    blocks.append(v)
                    break
        return blocks

    def is_dom(self, v, v1):
        visited = set()
        stack = [v]
        while len(stack) != 0:
            current_v = stack.pop()
            if current_v == v1:
                return True
            visited.add(current_v)
            for child in current_v.children:
                if child not in visited:
                    stack.append(child)
        return False

    def get_exits_for_cycle(self, cycle):
        exits = []
        visited = set()
        stack = [cycle[0]]

        while len(stack) != 0:
            current_v = stack.pop()
            visited.add(current_v)
            for v_out in current_v.output_vertexes:
                if v_out not in cycle:
                    # print(v_out.block[0])
                    exits.append(v_out)
                else:
                    if v_out not in visited:
                        stack.append(v_out)
        return exits

    def ssa_succ(self, value):
        succs = []
        for v in self.vertexes:
            if len(v.block) == 0:
                continue
            instr = v.block[0]
            if is_assign(instr):
                operands = instr.get_operands()
                for op in operands:
                    if isinstance(op, IdOperand) and op.value == value:
                        succs.append(v)
        return succs

    def which_pred(self, v1, v):
        for i, ver in enumerate(v1.input_vertexes):
            if ver.number == v.number:
                return i
        return None

    def mark_dfs(self):
        first = self.vertexes[0]
        stack = [first]
        for v in self.vertexes:
            v.checked = False

        while len(stack) != 0:
            current = stack.pop()
            current.checked = True
            if len(current.output_vertexes) == 2:
                branch = current.block[-1]
                assert isinstance(branch, IsTrueInstruction)
                if isinstance(branch.value, BoolConstantOperand):
                    val = branch.value.value
                    on_delete_connector = None
                    for i, next_v in enumerate(current.output_vertexes):
                        if val and i == 0 or not val and i == 1:
                            if not next_v.checked:
                                stack.append(next_v)
                        else:
                            on_delete_connector = i
                    out_v = current.output_vertexes[on_delete_connector]
                    current.output_vertexes.pop(on_delete_connector)
                    out_v.input_vertexes.pop(self.which_pred(out_v, current))
                else:
                    for next_v in current.output_vertexes:
                        if not next_v.checked:
                            stack.append(next_v)
            else:
                for next_v in current.output_vertexes:
                    if not next_v.checked:
                        stack.append(next_v)

    def get_empty_blocks(self):
        blocks = []
        for v in self.vertexes:
            if len(v.block) == 0:
                blocks.append(v)
        return blocks

    def which_succ(self, v1, v):
        for i, in_ver in enumerate(v1.output_vertexes):
            if v.number == in_ver.number:
                return i

    def remove_block(self, bl):
        rem_i = 0
        for i, v in enumerate(self.vertexes):
            if v.number == bl.number:
                if len(v.output_vertexes) != 0:
                    out_v = v.output_vertexes[0]
                    in_i = self.which_pred(out_v, v)
                    del out_v.input_vertexes[in_i]
                    for in_v in v.input_vertexes:
                        out_i = self.which_succ(in_v, v)
                        in_v.output_vertexes[out_i] = out_v
                        out_v.input_vertexes.append(in_v)
                rem_i = i
                break
        del self.vertexes[rem_i]

    def remove_fluous_edges(self):
        for v in self.vertexes:
            if len(v.output_vertexes) == 2 and v.output_vertexes[0].number == v.output_vertexes[1].number:
                v.output_vertexes.pop()
                del v.block[-1]

    def find_loop_nests(self):
        full_nests = []
        for i, cycle in enumerate(self.cycles):
            nest = [cycle]
            for j, other_cycle in enumerate(self.cycles):
                if j == i:
                    continue
                if set(other_cycle).issubset(set(cycle)):
                    nest.append(other_cycle)
            full_nests.append(nest)
        nests = []
        for i, nest in enumerate(full_nests):
            is_include = True
            for j, other_nest in enumerate(full_nests):
                if i == j:
                    continue
                if len(other_nest) > len(nest):
                    if nest[0] in other_nest:
                        is_include = False
                        break
            if is_include:
                nests.append(nest)
        return nests
