#include <stdio.h>
#include <string.h>

int main() {
    char operation[10];
    int addition, subtraction, multiplication, division;
    int first_number, second_number;
    float zakat;

     printf("Enter the operation (operation, zakat): ");
      scanf(" %9s", operation);

if(strcmp(operation, "zakat") == 0) {
        float amount;
        printf("Enter the amount for zakat: ");
        scanf("%f", &amount);
        zakat = amount * 0.025;
        printf("Your zakat is: %.2f\n", zakat);}else

  if(strcmp(operation ,"operation")==0) {
        printf("enter the operation:");
        scanf("%2s",operation);
    printf("Enter two numbers: ");
    scanf("%d %d", &first_number, &second_number);

 

    if (strcmp(operation, "+") == 0) {
        addition = first_number + second_number;
        printf("Your result: %d\n", addition);

    } else if (strcmp(operation, "-") == 0) {
        subtraction = first_number - second_number;
        printf("Your result: %d\n", subtraction);

    } else if (strcmp(operation, "*") == 0) {
        multiplication = first_number * second_number;
        printf("Your result: %d\n", multiplication);

    } else if (strcmp(operation, "/") == 0) {
        if (second_number == 0) {
            printf("Cannot divide by zero.\n");
        } else {
            division = first_number / second_number;
            printf("Your result: %d\n", division);
        }

    } else if (strcmp(operation, "zakat") == 0) {
        float amount;
        printf("Enter the amount for zakat: ");
        scanf("%f", &amount);
        zakat = amount * 0.025;
        printf("Your zakat is: %.2f\n", zakat);

    } else {
        printf("Invalid method\n");
    }
   }
    return 0;
}
