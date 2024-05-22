import builder
from frontend import *


def opt_pass(tree):
    changed = False
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
        changed = builder.contexts[func.name].loop_invariant_code_motion() or changed
        print(func.name, changed)
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
        print(func.name, changed)
        # Dead code elimination
        changed = builder.contexts[func.name].dead_code_elimination() or changed
        print(func.name, changed)

    if changed:
        for func in tree.funcDefs:
            builder.contexts[func.name].remove_ssa()
    return changed


if __name__ == "__main__":
    n_tests = 5
    for i in range(1, n_tests + 1):
        builder.contexts = {}
        test_file = f"tests/test{i}.txt"
        out_file = f"out/out{i}.txt"
        out_file_start = f"out/out{i}_start.txt"
        out_file_rd = f"out/out{i}_rd.txt"
        tree = parse(test_file)
        tree.generate()
        for func in tree.funcDefs:
            builder.contexts[func.name].set_contexts(builder.contexts)
        builder.print_graph(out_file_start)
        changed = True
        j = 0
        while changed:
            j += 1
            changed = opt_pass(tree)
            # break
        print(f"Тест {i} завершился за {j - 1} пассов")
        builder.print_graph(out_file)
