# C 语言编程指南

## 基础语法

### 变量和数据类型

C 语言中的基本数据类型包括：
- `int`: 整数类型
- `float`: 单精度浮点数
- `double`: 双精度浮点数
- `char`: 字符类型

示例：
```c
int age = 25;
float price = 99.99;
char grade = 'A';
```

### 数组

数组是一组相同类型的数据集合。

声明数组：
```c
int numbers[10];  // 声明一个包含10个整数的数组
int scores[] = {85, 90, 78, 92, 88};  // 初始化数组
```

访问数组元素：
```c
numbers[0] = 100;  // 第一个元素
numbers[9] = 200;  // 最后一个元素
```

### 指针

指针是存储变量地址的变量。

```c
int x = 10;
int *ptr = &x;  // ptr 指向 x 的地址
printf("%d", *ptr);  // 输出 10
```

## 函数

### 函数定义

```c
int add(int a, int b) {
    return a + b;
}
```

### 函数调用

```c
int result = add(5, 3);  // result = 8
```

## 控制结构

### if-else 语句

```c
if (score >= 90) {
    printf("优秀");
} else if (score >= 60) {
    printf("及格");
} else {
    printf("不及格");
}
```

### for 循环

```c
for (int i = 0; i < 10; i++) {
    printf("%d\n", i);
}
```

### while 循环

```c
int i = 0;
while (i < 10) {
    printf("%d\n", i);
    i++;
}
```

## 字符串操作

### 字符串声明

```c
char str[] = "Hello";
char *str2 = "World";
```

### 字符串函数

```c
#include <string.h>

char str1[20] = "Hello";
char str2[20] = "World";

strcpy(str1, str2);  // 复制字符串
strcat(str1, str2);  // 连接字符串
int len = strlen(str1);  // 获取长度
int cmp = strcmp(str1, str2);  // 比较字符串
```

## 结构体

### 定义结构体

```c
struct Student {
    int id;
    char name[50];
    float score;
};
```

### 使用结构体

```c
struct Student s1;
s1.id = 1;
strcpy(s1.name, "张三");
s1.score = 95.5;
```

## 文件操作

### 打开文件

```c
FILE *fp;
fp = fopen("file.txt", "r");  // 读取模式
if (fp == NULL) {
    printf("文件打开失败");
}
```

### 读取文件

```c
char buffer[100];
fgets(buffer, 100, fp);  // 读取一行
fclose(fp);
```

### 写入文件

```c
FILE *fp = fopen("file.txt", "w");
fprintf(fp, "Hello World\n");
fclose(fp);
```

## 内存管理

### 动态分配内存

```c
#include <stdlib.h>

int *arr = (int*)malloc(10 * sizeof(int));  // 分配内存
if (arr == NULL) {
    printf("内存分配失败");
    return;
}

// 使用内存
for (int i = 0; i < 10; i++) {
    arr[i] = i;
}

free(arr);  // 释放内存
```

### calloc 和 realloc

```c
int *arr = (int*)calloc(10, sizeof(int));  // 分配并初始化为0
arr = (int*)realloc(arr, 20 * sizeof(int));  // 重新分配内存
```

## 常见修改操作

### 修改数组元素

```c
int arr[5] = {1, 2, 3, 4, 5};
arr[2] = 99;  // 修改第三个元素为 99
```

### 修改字符串

```c
char str[] = "Hello";
str[0] = 'h';  // 修改第一个字符
strcpy(str, "World");  // 替换整个字符串
```

### 修改结构体成员

```c
struct Student s;
s.id = 1;
s.score = 95.5;  // 修改分数
```

### 修改指针指向的值

```c
int x = 10;
int *ptr = &x;
*ptr = 20;  // 通过指针修改 x 的值为 20
```

### 修改文件内容

```c
FILE *fp = fopen("data.txt", "w");
fprintf(fp, "新内容\n");  // 写入新内容覆盖原文件
fclose(fp);
```

### 修改动态数组大小

```c
int *arr = (int*)malloc(5 * sizeof(int));
// 需要更多空间时
arr = (int*)realloc(arr, 10 * sizeof(int));
```

## 错误处理

### 检查返回值

```c
FILE *fp = fopen("file.txt", "r");
if (fp == NULL) {
    perror("打开文件失败");
    return -1;
}
```

### 空指针检查

```c
int *ptr = malloc(sizeof(int));
if (ptr == NULL) {
    printf("内存分配失败");
    return;
}
```

## 预处理器

### 宏定义

```c
#define MAX_SIZE 100
#define PI 3.14159

int array[MAX_SIZE];
```

### 条件编译

```c
#ifdef DEBUG
    printf("调试信息\n");
#endif
```

## 常见问题

### 如何修改数组大小？

使用 `realloc` 函数可以修改动态分配的数组大小：
```c
int *arr = malloc(5 * sizeof(int));
arr = realloc(arr, 10 * sizeof(int));
```

### 如何修改字符串中的字符？

直接通过索引修改：
```c
char str[] = "Hello";
str[0] = 'h';  // 修改为 "hello"
```

### 如何修改结构体？

直接给成员赋值：
```c
struct Student s;
s.score = 95.5;  // 修改分数
```

### 如何修改文件内容？

使用写入模式打开文件会覆盖原内容：
```c
FILE *fp = fopen("file.txt", "w");
fprintf(fp, "新内容");
fclose(fp);
```
