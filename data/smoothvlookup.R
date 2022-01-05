smoothvlookup<-function(dataset,lookup.table,lookup.quant,lookup.trans,quant,trans){
  temp<-dataset[,quant]
  output<-(lookup.table[1,lookup.trans]+
             (temp-lookup.table[1,lookup.quant])*
             (lookup.table[2,lookup.trans]-lookup.table[1,lookup.trans])/
             (lookup.table[2,lookup.quant]-lookup.table[1,lookup.quant]))*
    (temp<lookup.table[1,lookup.quant])
  for (i in 2:nrow(lookup.table)){
    if (lookup.table[i,lookup.quant]>lookup.table[i-1,lookup.quant]){
      output<-output+(lookup.table[i-1,lookup.trans]+
                        (temp-lookup.table[i-1,lookup.quant])*
                        (lookup.table[i,lookup.trans]-lookup.table[i-1,lookup.trans])/
                        (lookup.table[i,lookup.quant]-lookup.table[i-1,lookup.quant]))*
        (temp>=lookup.table[i-1,lookup.quant])*(temp<lookup.table[i,lookup.quant])
    }  
  }
  output<-output+(lookup.table[nrow(lookup.table),lookup.trans]+
                    (temp-lookup.table[nrow(lookup.table),lookup.quant])*
                    (lookup.table[nrow(lookup.table),lookup.trans]-lookup.table[nrow(lookup.table)-1,lookup.trans])/
                    (lookup.table[nrow(lookup.table),lookup.quant]-lookup.table[nrow(lookup.table)-1,lookup.quant]))*
    (temp>=lookup.table[nrow(lookup.table),lookup.quant])
  dataset[,trans]<-output
  return(dataset)
}