from collections import defaultdict

label_to_color = {
    1: "red",
    2: "blue",
    3: "green",
    4: "yellow",
    5: "purple",
    6: "orange"
}

class IFG_vertex:
    def __init__(self, value):
        self.value = value.replace("$", "_")
        self.adjacency = []
        self.color = None

    def set_color(self, max_color):
        adjacency_colors = list(map(lambda x: x.color, self.adjacency))
        for k in range(1, max_color + 1):
            if k not in adjacency_colors:
                self.color = k
                break

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        return self.value == other.value

    def __str__(self):
        return self.value

    def add_adj(self, adj):
        for a in self.adjacency:
            if a.value == adj.value:
                return
        self.adjacency.append(adj)

    def to_graph(self, file, pairs):
        if self.color is None:
            color = "black"
        else:
            color = label_to_color[self.color]
        file.write("\t" + self.value + "[label=\"\n")
        file.write("\t\t" + self.value)
        file.write("\t\", color = " + color + "]\n")
        for elem in self.adjacency:
            pair1 = (self.value, elem.value)
            pair2 = (elem.value, self.value)
            if pair1 not in pairs and pair2 not in pairs:
                file.write("\t" + self.value + "--" + elem.value + "\n")
                pairs.add(pair1)


class IFG:
    def __init__(self, k):
        self.k = k
        self.vertexes = []
        self.vars_to_color = {}

    def add_vertex(self, value):
        self.vertexes.append(IFG_vertex(value))

    def to_graph(self, filename):
        with open(filename, 'w') as file:
            file.write("graph g{\n")
            file.write("\tnode [shape = circle]\n")
            pairs = set()
            for vertex in self.vertexes:
                vertex.to_graph(file, pairs)
            file.write("}\n")

    def get_vertex(self, var):
        var = var.replace("$", "_")
        for vertex in self.vertexes:
            if vertex.value == var:
                return vertex

    def build(self, context, is_int_variables, restrickted_vars, added_vars):
        self.vertexes = []
        if is_int_variables:
            variables = context.get_int_variables()
        else:
            variables = context.get_float_variables()
        variables = list(map(lambda x: x.replace("$", "_"), variables))
        variables += added_vars
        variables = [v for v in variables if v not in restrickted_vars]
        for var in variables:
            self.add_vertex(var)
        for var in variables:
            for other_var in variables:
                if var == other_var:
                    continue
                for label, lives in context.labels_to_live.items():
                    if var in lives and other_var in lives:
                        #if var == "i_2":
                        #    print(var, other_var, context.not_phi_once(label, var, other_var))
                        if context.not_phi_once(label, var, other_var):
                            v1 = self.get_vertex(var)
                            v2 = self.get_vertex(other_var)
                            v1.add_adj(v2)
                            v2.add_adj(v1)
                            break

    def lexBFS(self):
        order = []
        gamma = [set(self.vertexes)]
        while gamma:
            current_set = gamma[0]
            v = current_set.pop()
            if not current_set:
                gamma.pop(0)
            order.append(v)
            T = [set() for _ in gamma]
            for w in v.adjacency:
                for i, S in enumerate(gamma):
                    if w in S:
                        S.remove(w)
                        T[i].add(w)
            gamma = [item for pair in zip(T, gamma) for item in pair]
            gamma = [s for s in gamma if s]
        return order

    def is_clique(self, vertexes):
        for v in vertexes:
            for other in vertexes:
                if v == other:
                    continue
                if other not in v.adjacency:
                    print(list(map(lambda x: x.value, vertexes)))
                    print(v.value, other.value)
                    return False
        return True

    def is_chordal(self):
        if len(self.vertexes) == 0:
            return True, 0, []
        order = self.lexBFS()
        order = order[::-1]
        # print(list(map(lambda x: str(x), order)))
        pos = {v: i for i, v in enumerate(order)}
        max_clique = 0
        for i in range(len(self.vertexes)):
            v = order[i]
            neighbors = [u for u in v.adjacency if pos[u] > i]
            if len(neighbors) < 2:
                if max_clique < len([v] + neighbors):
                    max_clique = len([v] + neighbors)
                continue
            if self.is_clique([v] + neighbors):
                if len([v] + neighbors) > max_clique:
                    max_clique = len([v] + neighbors)
            else:
                return False, max_clique, order
        return True, max_clique, order

    def try_color(self):
        is_ch, max_clique, order = self.is_chordal()
        order = order[::-1]
        # print(is_ch, max_clique)
        assert is_ch
        if max_clique > self.k:
            return self.choose_spill()
        else:
            self.color(order)
            return None

    def choose_spill(self):
        self.vertexes = sorted(self.vertexes, key=lambda x: len(x.adjacency), reverse=True)
        return self.vertexes[0].value

    def color(self, order):
        self.vars_to_color = {}
        for v in order:
            v.set_color(self.k)
            if v.color is None:
                self.to_graph("IFG/ifg.txt")
                raise RuntimeError("Неполадка с раскраской")
            self.vars_to_color[v.value] = v.color



