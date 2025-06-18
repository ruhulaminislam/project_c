#include <stdio.h>



int main(){

     char opration;
      int addition,subtraction,multiplication,division;
       int fist_number,secend_number;

        printf("enter the number:");
         scanf("%d %d",&fist_number,&secend_number);
          
          printf("enter the opration(+,-,*,/):");
           scanf(" %c",&opration);

                if(opration  == '+'){
                   addition=fist_number+secend_number;
                   printf("your result:%d\n",addition);

                     }else if(opration == '-'){
                      subtraction=fist_number-secend_number;
                        printf("your result:%d\n",subtraction);

                          }else if(opration =='*'){
                            multiplication=fist_number*secend_number;
                             printf("your result:%d\n",multiplication);

                                }else if(opration == '/'){
                                  division=fist_number/secend_number;
                                   printf("your result:%d\n",division);
       
              }else{
               printf("invilite mathiod");
}
      
          
  return 0;
}