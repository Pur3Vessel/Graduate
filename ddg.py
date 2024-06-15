from collections import defaultdict, deque
from enum import Enum

class Color(Enum):
    WHITE = 0
    GRAY = 1
    BLACK = 2


def dependency_analyze():
    pass


class VertexDDG:
    def __init__(self, value):
        self.value = value
        self.input_vertexs = []
        self.output_vertexes = []
        self.visited = False
        self.color = None


class GraphDDG:
    def __init__(self):
        self.vertexes = []
        self.stack = []
        self.scc_list = []
        self.cycles_pairs = []

    def get_vertex(self, label):
        for vertex in self.vertexes:
            if vertex.value == label:
                return vertex

    def add_vertex(self, label):
        self.vertexes.append(VertexDDG(label))

    def add_connector(self, label1, label2):
        v1 = self.get_vertex(label1)
        v2 = self.get_vertex(label2)
        if v1 is None:
            self.add_vertex(label1)
            v1 = self.get_vertex(label1)
        if v2 is None:
            self.add_vertex(label2)
            v2 = self.get_vertex(label2)
        v1.output_vertexes.append(v2)
        v2.input_vertexes.append(v1)

    def clear_visited(self):
        for vertex in self.vertexes:
            vertex.visited = False

    def cycle_dfs(self, vertex):
        vertex.color = Color.GRAY
        for out_v in vertex.output_vertexes:
            if out_v.color == Color.WHITE:
                self.cycle_dfs(out_v)
            if out_v.color == Color.GRAY:
                self.cycles_pairs.append((vertex, out_v))
        vertex.color = Color.BLACK

    def check_cycle(self):
        self.cycles_pairs = []
        for v in self.vertexes:
            v.color = Color.WHITE
        self.cycle_dfs(self.vertexes[0])
        return len(self.cycles_pairs) == 0

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
                self.dfs_reverse(node, component)

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
        self.input_vertexs = []
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
