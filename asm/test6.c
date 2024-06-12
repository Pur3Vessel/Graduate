#include <stdio.h>
#include <stdlib.h>
#include <time.h>

int tile_test(int *u, int n, int m) {
    for (int k = 0; k < 100; k++) {
        for (int i = 0; i < n - 3; i++) {
            for (int j = 0; j < m - 1; j++) {
                *(u + (i + 2) * m + (j + 1)) = *(u + (i + 2) * m + j) + *(u + (i + 3) * m + j) + *(u + i * m + j);
            }
        }
    }
    return *(u + 3000 * m + 3000);
}

extern int tile(int *u, int n, int m);

int main() {
   clock_t start, end;
   double cpu_time_used;
   int (*u)[4000] = malloc(sizeof(int[4000][4000]));
   for (int i = 0; i < 4000; i++) {
        for (int j = 0; j < 4000; j++) {
            u[i][j] = 2;
        }
   }
   int result = tile_test((int *)u, 4000, 4000);
   free(u);
   printf("Результат: %d\n", result);
   int (*u1)[4000] = malloc(sizeof(int[4000][4000]));
   for (int i = 0; i < 4000; i++) {
        for (int j = 0; j < 4000; j++) {
            u1[i][j] = 2;
        }
   }
   start = clock();
   int result1 = tile((int*) u1, 4000, 4000);
   end = clock();
   free(u1);
   printf("Результат сгенерированной программы: %d\n", result1);
   cpu_time_used = ((double) (end - start)) / CLOCKS_PER_SEC;
   printf("Время выполнения: %f секунд\n", cpu_time_used);
   return 0;
}