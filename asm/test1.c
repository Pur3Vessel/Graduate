#include <stdio.h>
#include <time.h>
#include <stdlib.h>

int tile_test(int *u, int m, int n) {
    int i, j;
    for (i = 0; i < n; i++) {
        for (j = 0; j < m - 1; j++) {
            u[j + 1] = u[j + 1] + u[j];
        }
    }
    return u[m - 1];
}

extern int tile(int *u, int n, int m);

int main() {
    clock_t start, end;
    double cpu_time_used;
    int* u = malloc(sizeof(int[5000]));
    for (int i = 0; i < 5000; i++) {
        u[i] = i;
    }
    int result = tile_test((int*)u, 5000, 200);
    printf("Результат: %d\n", result);
    free(u);
    int* u1 = malloc(sizeof(int[5000]));
    for (int i = 0; i < 5000; i++) {
        u1[i] = i;
    }
    start = clock();
    int result1 = tile((int*)u1, 5000, 200);
    end = clock();
    printf("Результат сгенерированной программы: %d\n", result1);
    cpu_time_used = ((double) (end - start)) / CLOCKS_PER_SEC;
    printf("Время выполнения: %f секунд\n", cpu_time_used);
    free(u1);
    return 0;
}