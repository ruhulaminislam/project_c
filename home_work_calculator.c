#include <stdio.h>
#include <string.h>


int main(){

     char opration[10];
      int addition,subtraction,multiplication,division;
       int first_number,second_number;

        printf("enter the number:");
         scanf("%d %d",&first_number,&second_number);
          
          printf("enter the opration(+,-,*,/):");
           scanf(" %9s",&opration);

                if(strcmp(opration  , "+")==0){
                   addition=first_number+second_number;
                   printf("your result:%d\n",addition);

                     }else if(strcmp(opration , "-")==0){
                      subtraction=first_number-second_number;
                        printf("your result:%d\n",subtraction);

                          }else if(strcmp(opration ,"*")==0){
                            multiplication=first_number*second_number;
                             printf("your result:%d\n",multiplication);

                                }else if(strcmp(opration , "/")==0){
                                  division=first_number/second_number;
                                   printf("your result:%d\n",division);
       
              }else{
               printf("invalid method");
}
      
          
  return 0;
}