from collections import defaultdict, deque
from enum import Enum
import re


class Color(Enum):
    WHITE = 0
    GRAY = 1
    BLACK = 2


def parse_expression(expression):
    pattern = re.compile(r'([+-]?\s*\d*)\s*\*\s*([a-zA-Z_][a-zA-Z_0-9]*)|([+-]?\s*)([a-zA-Z_][a-zA-Z_0-9]*)')
    constant_pattern = re.compile(r'([+-]?\s*\d+)$')

    matches = pattern.findall(expression)

    pairs = []

    for match in matches:
        if match[0]:
            coeff = match[0].replace(" ", "")
            var = match[1]
        else:
            coeff = match[2].replace(" ", "")
            var = match[3]

        if coeff == '+' or coeff == '':
            coeff = 1
        elif coeff == '-':
            coeff = -1
        else:
            coeff = int(coeff)

        pairs.append((coeff, var))
    constant_match = constant_pattern.search(expression)

    if constant_match:
        constant = int(constant_match.group().replace(" ", ""))
    else:
        constant = 0

    if pairs:
        return pairs, constant

    return None


def MIV(indexes1, indexes2, c1, c2, loops_info):
    return True


def weak_zero_SIV(indexes1, indexes2, c1, c2, loops_info):
    return True


def weak_crossing_SIV(indexes1, indexes2, c1, c2, loops_info):
    return True


def strong_SIV(indexes1, indexes2, c1, c2, loops_info):
    a = indexes1[0][0]
    c = c2 - c1
    if c % a != 0:
        return False, 0, 0
    d = c // a
    left, right = get_gran(indexes1[0][1], loops_info)
    if not (left <= abs(d) < right or d == 0):
        return False, 0, 0

    if d > 0:
        direction = 1
    else:
        direction = 0
    return True, direction, abs(d)


def get_gran(index, loops_info):
    for idx in loops_info:
        if idx[0] == index:
            left = idx[1]
            right = idx[2]
            if not isinstance(left, int):
                left = 0
            if not isinstance(right, int):
                right = float('inf')
            return left, right


def dependency_analyze(use1, use2, indexes, loops_info):
    use1_name = use1[0]
    use1_indixes = use1[1]
    use2_name = use2[0]
    use2_indixes = use2[1]
    inner_index = indexes[-1]

    use1_indixes_parsed = []
    use2_indixes_parsed = []
    for use1_index in use1_indixes:
        use1_index_parsed = parse_expression(use1_index)
        if use1_index_parsed is None:
            return None
        use1_indixes_parsed.append(use1_index_parsed)

    for use2_index in use2_indixes:
        use2_index_parsed = parse_expression(use2_index)
        if use2_index_parsed is None:
            return None
        use2_indixes_parsed.append(use2_index_parsed)

    use1_used_indixes = list(map(lambda x: list(map(lambda y: y[1], x[0])), use1_indixes_parsed))
    use2_used_indixes = list(map(lambda x: list(map(lambda y: y[1], x[0])), use2_indixes_parsed))
    if use1_name != use2_name:
        return False, False, False, False

    if len(use1_indixes_parsed) != len(use2_indixes_parsed):
        return False, False, False, False

    if not inner_index in use1_used_indixes[-1]:
        return None

    directions = []
    distances = []
    for i in range(len(use1_indixes_parsed)):
        use1_dim_i = use1_indixes_parsed[i]
        use2_dim_i = use2_indixes_parsed[i]
        c1 = use1_dim_i[1]
        c2 = use2_dim_i[1]
        indexes_1 = use1_dim_i[0]
        indexes_2 = use2_dim_i[0]
        if len(indexes_1) == len(indexes_2) == 0:
            return c1 == c2, False, True, True
        elif len(indexes_1) >= 2 or len(indexes_2) >= 2:
            if MIV(indexes_1, indexes_2, c1, c2, loops_info):
                return None
            else:
                return False, False, False, False
        else:
            if len(indexes_1) == 0 or len(indexes_2) == 0:
                if weak_zero_SIV(indexes_1, indexes_2, c1, c2, loops_info):
                    return None
                else:
                    return False, False, False, False
            a1 = indexes_1[0][0]
            a2 = indexes_2[0][0]
            if abs(a1) != abs(a2) or indexes_1[0][1] != indexes_2[0][1]:
                if MIV(indexes_1, indexes_2, c1, c2, loops_info):
                    return None
                else:
                    return False, False, False, False
            elif a1 != a2:
                if weak_crossing_SIV(indexes_1, indexes_2, c1, c2, loops_info):
                    return None
                else:
                    return False, False, False, False
            else:
                siv_test_result = strong_SIV(indexes_1, indexes_2, c1, c2, loops_info)
                if not siv_test_result[0]:
                    return False, False, False, False
                else:
                    directions.append(siv_test_result[1])
                    distances.append(siv_test_result[2])
    if any(list(map(lambda x: x > 0, distances[:-1]))):
        return False, 0, False, False
    if distances[-1] >= 4:
        return False, 0, False, False
    dir = check_directions(directions)
    if dir is None:
        return False, 0, False, False
    elif dir == 0:
        d1 = True
        d2 = False
    elif dir == 1:
        d1 = False
        d2 = True
    else:
        d1 = True
        d2 = True
    independ = distances[-1] != 0
    return True, independ, d1, d2


def check_directions(dirs):
    contains_2 = all(x == 2 for x in dirs)
    if contains_2:
        return 2
    contains_0_or_2 = all(x == 0 or x == 2 for x in dirs)
    contains_1_or_2 = all(x == 1 or x == 2 for x in dirs)

    if contains_0_or_2:
        return 0
    elif contains_1_or_2:
        return 1
    else:
        return None


class VertexDDG:
    def __init__(self, value):
        self.value = value
        self.input_vertexes = []
        self.output_vertexes = []
        self.visited = False
        self.color = None


class GraphDDG:
    def __init__(self):
        self.vertexes = []
        self.stack = []
        self.scc_list = []
        self.cycles_pairs = []
        self.connectors_types = {}

    def get_vertex(self, label):
        for vertex in self.vertexes:
            if vertex.value == label:
                return vertex
        return None

    def add_vertex(self, label):
        self.vertexes.append(VertexDDG(label))

    def add_connector(self, label1, label2, type):
        v1 = self.get_vertex(label1)
        v2 = self.get_vertex(label2)
        if v1 is None:
            self.add_vertex(label1)
            v1 = self.get_vertex(label1)
        if v2 is None:
            if label2 == label1:
                v2 = v1
            else:
                self.add_vertex(label2)
                v2 = self.get_vertex(label2)
        if v2 not in v1.output_vertexes:
            v1.output_vertexes.append(v2)
            v2.input_vertexes.append(v1)
        if (v1, v2) not in self.connectors_types or (
                (v1, v2) in self.connectors_types and not self.connectors_types[(v1, v2)]):
            self.connectors_types[(v1, v2)] = type

    def clear_visited(self):
        for vertex in self.vertexes:
            vertex.visited = False

    def cycle_dfs(self, vertex):
        vertex.color = Color.GRAY
        for out_v in vertex.output_vertexes:
            if out_v.color == Color.WHITE:
                self.cycle_dfs(out_v)
            if out_v.color == Color.GRAY and self.connectors_types[(vertex, out_v)]:
                self.cycles_pairs.append((vertex, out_v))
        vertex.color = Color.BLACK

    def check_cycle(self):
        if len(self.vertexes) == 0:
            return False
        self.cycles_pairs = []
        for v in self.vertexes:
            v.color = Color.WHITE
        self.cycle_dfs(self.vertexes[0])
        return len(self.cycles_pairs) > 0

    def dfs(self, node):
        node.visited = True
        for out in node.output_vertexes:
            if not out.visited:
                self.dfs(out)
        self.stack.append(node)

    def dfs_reverse(self, node, component):
        node.visited = True
        component.append(node)
        for out in node.input_vertexes:
            if not out.visited:
                self.dfs_reverse(out, component)

    def get_scc(self):
        self.clear_visited()
        self.stack = []
        for vertex in self.vertexes:
            if not vertex.visited:
                self.dfs(vertex)
        self.clear_visited()
        scc_list = []
        while self.stack:
            node = self.stack.pop()
            if not node.visited:
                component = []
                self.dfs_reverse(node, component)
                scc_list.append(component)
        self.scc_list = scc_list
        self.topological_sort()
        return self.scc_list

    def topological_sort(self):
        scc_graph = GraphSCC()
        component_mapping = {}
        for i, component in enumerate(self.scc_list):
            for node in component:
                component_mapping[node] = i
            scc_graph.add_vertex(i)

        for node in self.vertexes:
            for out in node.output_vertexes:
                scc1 = component_mapping[node]
                scc2 = component_mapping[out]
                scc_graph.add_connector(scc1, scc2)

        scc_graph.topological_sort()
        new_scc_list = []
        for v in scc_graph.vertexes:
            new_scc_list.append(self.scc_list[v.value])
        self.scc_list = new_scc_list


class VertexSCC:
    def __init__(self, value):
        self.value = value
        self.input_vertexes = []
        self.output_vertexes = []


class GraphSCC:
    def __init__(self):
        self.vertexes = []

    def add_vertex(self, label):
        self.vertexes.append(VertexSCC(label))

    def get_vertex(self, label):
        for vertex in self.vertexes:
            if vertex.value == label:
                return vertex

    def add_connector(self, label1, label2):
        if label1 == label2:
            return
        v1 = self.get_vertex(label1)
        v2 = self.get_vertex(label2)
        if v1 is not None and v2 is not None:
            if v2 not in v1.output_vertexes:
                v1.output_vertexes.append(v2)
            if v1 not in v2.input_vertexes:
                v2.input_vertexes.append(v1)
        else:
            print("ы")

    def topological_sort(self):
        in_degree = defaultdict(int)
        for node in self.vertexes:
            for out in node.output_vertexes:
                in_degree[out] += 1

        zero_in_degree_queue = deque([node for node in self.vertexes if in_degree[node] == 0])
        topological_order = []

        while zero_in_degree_queue:
            node = zero_in_degree_queue.popleft()
            topological_order.append(node)
            for out in node.output_vertexes:
                in_degree[out] -= 1
                if in_degree[out] == 0:
                    zero_in_degree_queue.append(out)

        if len(topological_order) != len(self.vertexes):
            print(topological_order, self.vertexes)
            raise ValueError("Граф содержит циклы, топологическая сортировка невозможна.")

        return topological_order
