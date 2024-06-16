#include <stdio.h>

int v_test(int *a, int u1, int *b, int u2, int *c, int u3, int *d, int u4, int *e, int u5) {
    for (int i = 0; i < u1; i++) {
        a[i] = c[i] * b[i];
        b[i + 1] = d[i] - e[i];
        c[i + 1] = a[i] * e[i];
    }
    return c[u2 - 1];
}

extern int v(int *a, int u1, int *b, int u2, int *c, int u3, int *d, int u4, int *e, int u5);

int main() {
    int u1 = 5;
    int u2 = 5;
    int u3 = 5;
    int u4 = 5;
    int u5 = 5;


    int a[u1], b[u3 + 1], c[u2 + 1], d[u4], e[u5];

    for (int i = 0; i < u1; i++) {
        a[i] = i + 1;
        b[i] = i + 2;
        c[i] = i + 3;
        d[i] = i + 4;
        e[i] = i + 5;
    }
    b[u3] = 0;
    c[u2] = 0;

    int result = v_test(a, u1, b, u3 + 1, c, u2 + 1, d, u4, e, u5);
    printf("Результат: %d\n", result);
    int a1[u1], b1[u3 + 1], c1[u2 + 1], d1[u4], e1[u5];

    for (int i = 0; i < u1; i++) {
        a1[i] = i + 1;
        b1[i] = i + 2;
        c1[i] = i + 3;
        d1[i] = i + 4;
        e1[i] = i + 5;
    }
    b1[u3] = 0;
    c1[u2] = 0;
    int result1 = v(a1, u1, b1, u3 + 1, c1, u2 + 1, d1, u4, e1, u5);
    printf("Результат сгенерированной программы: %d\n", result1);
    return 0;
}