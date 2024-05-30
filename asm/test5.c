#include <stdio.h>

int aboba_test() {
    int a[5] = {1, 2, 3, 4, 5};
    int b[5] = {1, 2, 3, 4, 5};
    int c[5] = {1, 2, 3, 4, 5};
    for (int i = 1; i < 5; i++) {
        b[i] = b[i] + c[i];
        a[i] = a[i - 1] + b[i];
        c[i] = a[i] + 1;
    }
    return c[4];
}

extern int aboba();

int main() {
    int result = aboba_test();
    printf("Результат: %d\n", result);
    printf("Результат сгенерированной программы : %d\n", aboba());
    return 0;
}