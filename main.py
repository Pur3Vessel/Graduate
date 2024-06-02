import builder
from frontend import *
from code_builder import *
import argparse


def opt_pass(tree, j):
    changed = False
    if j <= 2:
        is_preheader = False
    else:
        is_preheader = True
    for func in tree.funcDefs:
        # Обход в глубину
        builder.contexts[func.name].graph.dfs()
        # Удаление недостижимых вершин
        builder.contexts[func.name].graph.remove_non_reachable()
        # Выделение циклов
        builder.contexts[func.name].graph.get_natural_cycles()
        # Выявление достигающих определений
        builder.contexts[func.name].graph.solve_rd()
        # Loop invariant_code_motion
        if j > 1:
            changed = builder.contexts[func.name].loop_invariant_code_motion(is_preheader) or changed
        elif j == 1:
            builder.contexts[func.name].tiling()
        # Построение дерева доминаторов
        builder.contexts[func.name].graph.dfs()
        builder.contexts[func.name].graph.build_dominators_tree()
        # Построение DF для каждой вершины
        builder.contexts[func.name].graph.make_DF()
        # Расстановка phi функций
        builder.contexts[func.name].place_phi()
        # Переименовывание переменных
        builder.contexts[func.name].change_numeration()
        # Constant_propagation
        changed = builder.contexts[func.name].constant_propagation() or changed
        # print(func.name, changed)
        # Copy_propagation
        changed = builder.contexts[func.name].copy_propagation() or changed
        # Dead code elimination
        # print(func.name, changed)
        changed = builder.contexts[func.name].dead_code_elimination() or changed
        # print(func.name, changed)
    if j == 0:
        changed = True
    if changed:
        for func in tree.funcDefs:
            builder.contexts[func.name].remove_ssa()
    return changed


def generate_tests():
    n_tests = 7
    for i in range(1, n_tests + 1):
        builder.contexts = {}
        test_file = f"tests/test{i}.txt"
        out_file = f"out/out{i}.txt"
        out_file_start = f"out/out{i}_start.txt"
        tree = parse(test_file)
        tree.generate()
        for func in tree.funcDefs:
            builder.contexts[func.name].set_contexts(builder.contexts)
        builder.set_labels()
        builder.print_graph(out_file_start)
        changed = True
        j = 0
        while changed:
            changed = opt_pass(tree, j)
            j += 1
        print(f"Тест {i} завершился за {j} пассов")
        builder.set_labels()
        builder.print_graph(out_file)
        code_builder = CodeBuilder(tree.funcDefs, builder, i)
        code_builder.allocate_registers()
        code_builder.generate_code()


def generate_file(filename):
    builder.contexts = {}
    tree = parse(filename)
    tree.generate()
    for func in tree.funcDefs:
        builder.contexts[func.name].set_contexts(builder.contexts)
    builder.set_labels()
    changed = True
    j = 0
    while changed:
        j += 1
        changed = opt_pass(tree, j)
    builder.set_labels()
    code_builder = CodeBuilder(tree.funcDefs, builder, -1)
    code_builder.allocate_registers()
    code_builder.generate_code()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", nargs="?", default=None)
    args = parser.parse_args()
    if args.filename:
        generate_file(args.filename)
    else:
        generate_tests()
