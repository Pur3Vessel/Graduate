#!/bin/bash

gcc -m32 -c test1.c -o test1.o

nasm -f elf32 program1.asm -o program1.o

gcc -m32 test1.o program1.o help.o -o test1

./test1






gcc -m32 -c test3.c -o test3.o

nasm -f elf32 program3.asm -o program3.o

gcc -m32 test3.o program3.o help.o -o test3

./test3

gcc -m32 -c test4.c -o test4.o

nasm -f elf32 program4.asm -o program4.o

gcc -m32 test4.o program4.o help.o -o test4

./test4


gcc -m32 -c test5.c -o test5.o

nasm -f elf32 program5.asm -o program5.o

gcc -m32 test5.o program5.o help.o -o test5

./test5


gcc -m32 -c test6.c -o test6.o

nasm -f elf32 program6.asm -o program6.o

gcc -m32 test6.o program6.o help.o -o test6

./test6

gcc -m32 -c test7.c -o test7.o

nasm -f elf32 program7.asm -o program7.o

gcc -m32 test7.o program7.o help.o -o test7

./test7