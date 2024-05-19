from context import Context


class Builder:
    def __init__(self):
        self.context = None
        self.contexts = {}
        self.number = 0

    def add_context(self, func_name):
        context = Context()
        self.contexts[func_name] = context
        self.context = context

    def set_contexts(self, name):
        self.context = self.contexts[name]

    def create_block(self):
        result = self.context.graph.add_vertex()
        if self.context.cur_vertex is not None:
            self.add_connector(self.context.cur_vertex, result)
        self.context.cur_vertex = result
        # result.number = self.number
        self.number += 1
        return result

    def create_block_without(self):
        result = self.context.graph.add_vertex()
        self.context.cur_vertex = result
        # result.number = self.number
        self.number += 1
        return result

    def create_labeled_block_without(self, label):
        result = self.context.graph.add_vertex()
        self.context.cur_vertex = result
        # result.number = self.number
        self.number += 1
        result.label = label
        return result

    def create_labeled_block(self, label):
        result = self.context.graph.add_vertex()
        if self.context.cur_vertex is not None:
            self.add_connector(self.context.cur_vertex, result)
        self.context.cur_vertex = result
        # result.number = self.number
        self.number += 1
        result.label = label
        return result

    def set_insert(self, v):
        self.context.cur_vertex = v

    def add_expression(self, expr):
        self.context.cur_vertex.insert_tail(expr)

    def add_connector(self, from_v, to):
        from_v.add_output_connector(to)
        to.add_input_connector(from_v)

    def current_block(self):
        return self.context.cur_vertex

    def get_block_by_label(self, label):
        for v in self.context.graph.vertexes:
            if v.label == label:
                return v
        return None

    def print_graph(self, filename):
        with open(filename, 'w') as file:
            file.write("digraph g{\n")
            file.write("\tnode [shape = box]\n")
            for context in self.contexts.values():
                context.graph.print_graph(file)
            file.write("}\n")

    def print_graph_rd(self, filename):
        with open(filename, 'w') as file:
            file.write("digraph g{\n")
            file.write("\tnode [shape = box]\n")
            for context in self.contexts.values():
                context.graph.print_graph_rd(file)
            file.write("}\n")
