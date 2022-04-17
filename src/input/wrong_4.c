/* 对非数组变量使用数组操作符 */
int not_arr;
not_arr[1]=1;

/* 数组下标不是整数 */
int arr[6][6];
a[1][0.5] = 5;

/* 对非函数变量使用函数操作符 */
call not_arr(1,2);

/* 函数变量未声明 */
call function(1,2);