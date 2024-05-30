#include <stdio.h>

int tile_test(int *u, int m, int n) {
    int i, j;
    for (i = 0; i < n; i++) {
        for (j = 1; j < m; j++) {
            u[j] = u[j] + u[j-1];
        }
    }
    return u[m - 1];
}

extern int tile(int *u, int n, int m);

int main() {
    int u[30] = {0};
    for (int i = 0; i < 30; i++) {
        u[i] = i;
    }
    int result = tile_test(u, 30, 20);
    printf("Результат: %d\n", result);
    for (int i = 0; i < 30; i++) {
        u[i] = i;
    }
    int result1 = tile(u, 30, 20);
    printf("Результат сгенерированной программы: %d\n", result1);
    return 0;
}