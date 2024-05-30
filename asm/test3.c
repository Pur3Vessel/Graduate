#include <stdio.h>

float calculate_test(float n) {
    float b = 5.3;
    int c = 2;
    for (int i = 0; i < 5; i++) {
        float a = 3.2;
        float d = n * n;
        b = b * c * i + a * a + d;
    }
    return b;
}


extern float calculate(float n);

int main() {
    float result = calculate_test(5);
    printf("Результат: %f\n", result);
    float result1 = calculate(5);
    printf("Результат сгенерированной программы: %f\n", result1);
    return 0;
}