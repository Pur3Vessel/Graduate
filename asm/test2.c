#include <stdio.h>

float multiply_test() {
    float a[3][3] = {{1.1, 1.2, 2.3}, {5.5, 6.4, 3.3}, {1.7, 1.5, 5.9}};
    float b[3][3] = {{1.1, 1.2, 2.3}, {5.5, 6.4, 3.3}, {1.7, 1.5, 5.9}};
    float c[3][3] = {0};
    int i, j, k;

    for (i = 0; i < 3; i++) {
        for (j = 0; j < 3; j++) {
            for (k = 0; k < 3; k++) {
                c[i][j] += a[i][j] * b[i][j];
            }
        }
    }
    int d = 3;
    return c[d - 1][2];
}

extern float multiply();

int main() {
    printf("Результат: %.2f\n", multiply_test());
    printf("Результат сгенерированной программы: %.2f\n", multiply());
    return 0;
}