
#include <stdio.h>
int main(){
    
    

    double total_assets,zakat,nisab=85612.50,remaining;
     printf("you total assets:");
     scanf("%lf",&total_assets);
      if(total_assets>nisab){
         zakat=(total_assets*2.5)/100;
         printf("your Zakat:%lf\n",zakat);
          printf("*Allah has made Zakat obligatory for muslims*");
         
      }else{
       remaining=nisab-total_assets;
        printf("*Zakat is not yet obligatory on you*\n");
         printf("   *you are: %lf taka below the nisab limit*",remaining);

      }



    return 0;
  }
