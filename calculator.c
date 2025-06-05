
#include <stdio.h>


int main(){
char oprations,egual;
double n1 ,n2;
   jump:
  printf("enter the opertor(n1+n2=):");
   scanf("%lf %c %lf %c",&n1,&oprations,&n2,&egual);
   if(egual != '='){
     printf("invalid format.please end the expression whith'='\n");
    goto jump;
     return 0;
   }
    switch(oprations)
    {
       
        case '+':
         printf("%.1lf+%.1lf=%.1lf",n1,n2,n1+n2);
          break;
           case '-':
            printf("%.1lf-%.1lf=%.1lf",n1,n2,n1-n2);
             break;
              case '*':
                printf("%.1lf*%.1lf=%.1lf",n1,n2,n1*n2);   
                 break;
                 if(n2>0){
                  case '/':
                    printf("%.1lf/%.1lf=",n1,n2,n1/n2);
              break;
                 }
         default:
         printf("enter the error number");
        
        printf("ruhulamin");
    }
  



    return 0;
}
