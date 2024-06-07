#include <stdio.h>
#include <stdlib.h>
#include <time.h>

int multiply_test() {
    int (*a)[4000] = malloc(sizeof(int[4000][4000]));
    int (*b)[4000] = malloc(sizeof(int[4000][4000]));
    int (*c)[4000] = malloc(sizeof(int[4000][4000]));
    int i, j, k;
    for (i = 0; i < 4000; i++) {
        for (j = 0; j < 4000; j++) {
            a[i][j] = i + j + 2;
            b[i][j] = i - j + 5;
            c[i][j] = 0;
        }
    }

    for (k = 0; k < 250; k++) {
        for (i = 0; i < 4000; i++) {
            for (j = 0; j < 4000; j++) {
                c[i][j] = c[i][j] + a[i][j] + b[i][j];
            }
        }
    }
    int d = c[3999][3999];
    free(a);
    free(b);
    free(c);
    return d;
}
extern int multiply(int *a, int n, int m, int *b, int g, int h, int *c, int q, int r);

int main() {
    clock_t start, end;
    double cpu_time_used;
    printf("Результат: %d\n", multiply_test());
    int (*a)[4000] = malloc(sizeof(int[4000][4000]));
    int (*b)[4000] = malloc(sizeof(int[4000][4000]));
    int (*c)[4000] = malloc(sizeof(int[4000][4000]));
    int i, j, k;
    for (i = 0; i < 4000; i++) {
        for (j = 0; j < 4000; j++) {
            a[i][j] = i + j + 2;
            b[i][j] = i - j + 5;
            c[i][j] = 0;
        }
    }
    start = clock();
    int result = multiply((int *)a, 4000, 4000,  (int*)b, 4000, 4000, (int*)c, 4000, 4000);
    end = clock();
    printf("Результат сгенерированной программы: %d\n", result);
    cpu_time_used = ((double) (end - start)) / CLOCKS_PER_SEC;
    printf("Время выполнения: %f секунд\n", cpu_time_used);
    free(a);
    free(b);
    free(c);
    return 0;
}