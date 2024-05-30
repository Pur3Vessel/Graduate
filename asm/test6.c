#include <stdio.h>

int tile_test(int *u, int n, int m) {
    for (int k = 0; k < n; k++) {
        for (int i = 2; i < n - 1; i++) {
            for (int j = 1; j < m; j++) {
                *(u + i * m + j) = *(u + i * m + j - 1) + *(u + (i + 1) * m + j - 1) + *(u + (i - 2) * m + j - 1);
            }
        }
    }
    return *(u + 2 * m + 3);
}

extern int tile(int *u, int n, int m);

int main() {
   int u[5][5] = {
       {1, 2, 3, 4, 5},
       {1, 2, 3, 4, 5},
       {1, 2, 3, 4, 5},
       {1, 2, 3, 4, 5},
       {1, 2, 3, 4, 5}
   };
   int result = tile_test((int *)u, 5, 5);
   printf("Результат: %d\n", result);
   int u1[5][5] = {
       {1, 2, 3, 4, 5},
       {1, 2, 3, 4, 5},
       {1, 2, 3, 4, 5},
       {1, 2, 3, 4, 5},
       {1, 2, 3, 4, 5}
   };
   int result1 = tile((int*) u1, 5, 5);
   printf("Результат сгенерированной программы: %d\n", result1);
   return 0;
}