#include <stdio.h>


float calc2_test(float a, float*b, int c, int d) {
    float reverse = -a;
    if ((a > d) && !(d <= 0)) {
        b[c - 1] = reverse;
    }
    int g = -d;
    float g1 = 1.0f / g;
    g1 = g1 - b[c - 1];
    return g1;
}


float calc1_test(float a, int d) {
    float c = a / d;
    int d1 = d / 5;
    float b[10] = {1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 5.5, 4.4, 3.3, 2.2};
    float f = calc2_test(a, b, 10, d1);
    int d2 = d % 5;
    d1 = (d2 * 5) + (3 * d);
    if (c > d1) {
        return f;
    } else {
        b[7] = f / 5.7f;
        b[7] = b[7] * d2;
        return b[7];
    }
}

extern float calc1(float a, int d);

int main() {
    float result = calc1_test(900.0f, 15);
    printf("Результат: %f\n", result);
    float result1 = calc1(900.0f, 15);
    printf("Результат сгенерированной программы: %f\n", result1);
    return 0;
}