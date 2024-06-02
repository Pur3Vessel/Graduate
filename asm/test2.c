#include <stdio.h>
#include <stdlib.h>
#include <time.h>

float multiply_test() {
    float (*a)[4000] = malloc(sizeof(float[4000][4000]));
    float (*b)[4000] = malloc(sizeof(float[4000][4000]));
    float (*c)[4000] = malloc(sizeof(float[4000][4000]));
    int i, j, k;
    for (i = 0; i < 4000; i++) {
        for (j = 0; j < 4000; j++) {
            a[i][j] = 50.5;
            b[i][j] = a[i][j] + 2.5;
        }
    }

    for (k = 0; k < 250; k++) {
        for (i = 0; i < 4000; i++) {
            for (j = 0; j < 4000; j++) {
                c[i][j] = c[i][j] + a[i][j] * b[i][j];
            }
        }
    }
    float d = c[3999][3999];
    free(a);
    free(b);
    free(c);
    return d;
}
extern float multiply(float *a, int n, int m, float *b, int g, int h, float *c, int q, int r);

int main() {
    clock_t start, end;
    double cpu_time_used;
    printf("Результат: %.2f\n", multiply_test());
    float (*a)[4000] = malloc(sizeof(float[4000][4000]));
    float (*b)[4000] = malloc(sizeof(float[4000][4000]));
    float (*c)[4000] = malloc(sizeof(float[4000][4000]));
    int i, j, k;
    for (i = 0; i < 4000; i++) {
        for (j = 0; j < 4000; j++) {
            a[i][j] = 50.52;
            b[i][j] = a[i][j] + 2.5;
        }
    }
    start = clock();
    float result = multiply((float *)a, 4000, 4000,  (float*)b, 4000, 4000, (float*)c, 4000, 4000);
    end = clock();
    printf("Результат сгенерированной программы: %.2f\n", result);
    cpu_time_used = ((double) (end - start)) / CLOCKS_PER_SEC;
    printf("Время выполнения: %f секунд\n", cpu_time_used);
    free(a);
    free(b);
    free(c);
    return 0;
}