from collections import defaultdict


class IFG_vertex:
    def __init__(self, value):
        self.value = value.replace("$", "_")
        self.adjacency = []

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
        file.write("\t" + self.value + "[label=\"\n")
        file.write("\t\t" + self.value)
        file.write("\t\"]\n")
        for elem in self.adjacency:
            pair1 = (self.value, elem.value)
            pair2 = (elem.value, self.value)
            if pair1 not in pairs and pair2 not in pairs:
                file.write("\t" + self.value + "--" + elem.value + "\n")
                pairs.add(pair1)


class IFG:
    def __init__(self):
        self.vertexes = []

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

    def build(self, context):
        variables = context.get_variables()
        context.build_lives()
        for var in variables:
            self.add_vertex(var)
        for var in variables:
            for other_var in variables:
                if var == other_var:
                    continue
                for label, lives in context.labels_to_live.items():
                    if var in lives and other_var in lives:
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
        order = self.lexBFS()
        order = order[::-1]
        print(list(map(lambda x: str(x), order)))
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
                return False, max_clique
        return True, max_clique

    def print_lives(self, var, context):
        for label, lives in context.labels_to_live.items():
            if var in lives:
                print(context.graph.labels_to_instructions[label])
