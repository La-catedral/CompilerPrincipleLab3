/* test case for compiling system lab3*/

/* simple val*/
int val_f;
float val_s;
char c;

/* array define*/
char arr[8][8];

/* record */
struct obj{
    int val_1;
    double val_2;
};

/* process */
proc func;{
    char new_c;
    int new_i;
    new_c = arr[1][1];
}

/* operation */
val_s = val_f + 100;

/* array use and set */
arr[1][1] = "helo";
c = arr[1][0];

/* loop and branch */
while val_f >= val_s do {
    val_s = val_s + 1;
    if val_s == 0 then val_s = val_s + 1 ;
    else
        if val_f == val_s and not (val_f == 0) then val_f = 1;}

/* use process */
call func(val_f+arr[1][1], 100);