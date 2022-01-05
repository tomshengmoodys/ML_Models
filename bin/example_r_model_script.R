library(XML)
library(data.table)
library(plyr)

options(stringsAsFactors = FALSE)

# load all metadata, according to a model registry table

# For testing: location='data/'
location=paste0(package.path, '/data/')
source(paste(location,"smoothvlookup.R",sep=""))
source(paste(location,"inverselookup.R",sep=""))
load(paste0(location,"DDdata.RData"))
gammas=read.csv(paste(location,"all_gammas.csv",sep=""))
trans=read.csv(paste(location,"all_trans.csv",sep=""))
param=read.csv(paste(location,"ModelToSheet.csv",sep=""))
TermStruct=read.csv(paste(location,"TermStructure.csv",sep=""))
reqinputs=c("currentdate-year","currentdate-month","ttcpd","modelcode")
reqinputsLbls=c("Current Date - Year","Current Date - Month","TTC PD","Model Code")


getCCAEDF = function(input){
  
  #get inputs
  dt = setDT(lapply((input), function(l) sapply(l, function(x) ifelse(is.null(x),NA,x))))
  dt$id=1:nrow(dt)
  oldColnames = colnames(dt)
  setnames(dt, old = oldColnames, new = gsub(" ", "", tolower(colnames(dt)), fixed = TRUE))
  newColnames = colnames(dt)
  dt$ttcpd=as.numeric(dt$ttcpd)
  
  dt$ErrorMsg=""
  for(i in c(1:length(reqinputs))){
    msg = paste0(reqinputsLbls[i], ' is required; ')
    dt$ErrorMsg=paste0(dt$ErrorMsg,ifelse(dt[,get(reqinputs[i])]=="" | is.na(dt[,get(reqinputs[i])]),msg,""))
  }  
  dterror=subset(dt,ErrorMsg!="")
  dt=subset(dt,ErrorMsg=="")
  #get yearmonth
  dt$yearmonth=as.numeric(dt$"currentdate-year")*100+as.numeric(dt$"currentdate-month")
  #For now only working for 1Y TTC PD 
  #if(is.null(dt$"ttcpd-term")){ dt$term=rep(1,nRows)}else {dt$term= ifelse(dt$"ttcpd-term"=="",1,dt$"ttcpd-term")}
  term=1
  
  #get Lower Bounds by model
  dt=merge(dt,param[,c("Model","LowerBound1","LowerBound5")],by.x=c("modelcode"),by.y=c("Model"),all.x=TRUE)
  
  #If number of years not provided use 1
  dt$numberofyears= as.numeric(dt$numberofyears)
  if(is.null(dt$"numberofyears") | is.na(max(dt$numberofyears))| max(dt$numberofyears)<1){nYears=1} else {nYears=max(dt$numberofyears)}
  
  #For unemployment rate and vehicle sales we use the data as of 3 months ago the analysis date
  yearmonth.ur=as.POSIXlt(as.Date(paste0(substr(dt$yearmonth,5,6),"01",substr(dt$yearmonth,1,4)),"%m%d%Y"))
  yearmonth.ur$mon=yearmonth.ur$mon-3
  
  
  #For dd data we use the data as of 2 months ago the analysis date
  yearmonth.dd=yearmonth.ur
  yearmonth.dd$mon=yearmonth.dd$mon+1
  yearmonth.ur=format(yearmonth.ur,"%Y%m")
  yearmonth.dd=format(yearmonth.dd,"%Y%m")
  
  dt$yearmonth.ur=yearmonth.ur
  dt$yearmonth.dd=yearmonth.dd
  
  
  #TS=ifelse(is.null(input[["TermStructure"]])|term!=1,"NO",toupper(input[["TermStructure"]]))
  
  ListOfModels=unique(dt$modelcode)
  out=data.table()
  
  for (model in ListOfModels){
    #model="USA 4.0"
    #get transforms and gammas for the model that we want to use
    data=subset(dt,dt$modelcode==model)
    nrowdata=nrow(data)
    
    trans_model=subset(trans,Model==model & Year==term)[,c("Quant","Transform")]
    gamma_model=subset(gammas,Model==model & Year==term)[,c("Gamma")]
    
    #If Classification is a type of Codes (e.g. NAICS) search for the respective RiskCalc Sector
    #If Code is not found or RiskCalc Sector not found use Unassigned
    dsn<-xmlParse(paste0(location, subset(param,Model==model)[,c("SectorFile")]))
    
    classifications=(XML:::xmlAttrsToDataFrame(getNodeSet(dsn, path=paste0("//Classification"))))$Name
    
    sectortable=data.frame()
    for (class in classifications){
      stable=XML:::xmlAttrsToDataFrame(getNodeSet(dsn, path=paste0("//Classification[@Name='",class,"']//Code")))
      stable$classif=class
      sectortable=rbind.fill(sectortable,stable)
    }
    
    #if classification = "Sector",check that is on the RC covered sectors and use provided RC sector.
    #If a sector code provided, search for respective RC sector
    #Otherwise use Unassigned
    
    if(is.null(data$"industryclassification")){ data$industryclassification=rep("SECTOR",nrowdata)}else {data$industryclassification= ifelse(data$"industryclassification"=="","SECTOR",toupper(data$"industryclassification"))}    
    if(is.null(data$"industrydefinition")){ data$industrydefinition=rep("Unassigned",nrowdata)}else {data$industrydefinition= ifelse(data$"industrydefinition"=="","Unassigned",data$"industrydefinition")}    
    
    data=merge(data,sectortable[,c("Name","Sector","classif")],by.x=c("industryclassification","industrydefinition"),by.y=c("classif","Name"),all.x=TRUE)
    data$sector=ifelse(!is.na(data$Sector),data$Sector,ifelse(data$industrydefinition %in% unique(sectortable$Sector),data$industrydefinition,"Unassigned"))
    
    
    #get DD depending on the model, sector and yearmonth
    DDdata = get(subset(param,Model==model)[,"DDFile"])
    
    
    data$FSOEDF=ifelse(data$ttcpd<data$LowerBound1,data$LowerBound1,data$ttcpd)
    #get FSO intermediate score
    data=inverselookup(dataset=data.frame(data),lookup.table=trans_model,lookup.quant="Quant",lookup.trans="Transform",quant="FSOINTSCORE",trans="FSOEDF")
    
    #get CCA intermediate score
    if (model %in% c("USA 4.0", "UNP 4.0")){
      
      data=merge(data,DDdata,by.x=c("yearmonth.dd","sector"),by.y=c("yearmonth","sector"),all.x=TRUE)
      #data=data[order(data$id),]
      
      data$state=if(is.null(data$"region")){ data$region=rep("NATION",nrowdata)}else {data$region= ifelse(data$"region"=="","NATION",toupper(data$"region"))}
      
      data=merge(data,DDdata,by.x=c("yearmonth.ur","state"),by.y=c("yearmonth","sector"),all.x=TRUE)
      
      data$ErrorMsg=paste0(data$ErrorMsg,ifelse(is.na(data$dma36mdd1.y),paste0("DD Means ",data$state,": Data not found for ",data$yearmonth,";"),""))
      
      data$CCAINTSCORE=data$FSOINTSCORE*exp(gamma_model*(((1/(1+exp(-1*(0.5*data$dma36mdd1.x+0.5*data$dma36mdd1.y))))*4) - 2))
      #vars=c("yearmonth","sector","state")
      
    }else if(model %in% c("UDS 4.0")){
      
      
      data=merge(data,DDdata,by.x=c("yearmonth.ur","sector"),by.y=c("yearmonth","sector"),all.x=TRUE)
      
      data$state=if(is.null(data$"region")){ data$region=rep("NATION",nrowdata)}else {data$region= ifelse(data$"region"=="","NATION",toupper(data$"region"))}
      
      data=merge(data,DDdata,by.x=c("yearmonth.ur","state"),by.y=c("yearmonth","sector"),all.x=TRUE)
      
      data$ErrorMsg=paste0(data$ErrorMsg,ifelse(is.na(data$dma36mdd1.y),paste0("DD Means ",data$state,": Data not found for ",data$yearmonth,";"),""))
      
      data$CCAINTSCORE=data$FSOINTSCORE*exp(gamma_model*(((6/(1+exp(-(2/3)*(0.5*data$dma36mdd1.x-0.5*data$dma36mdd1.y))))) - 3))
      #vars=c("yearmonth","sector","state")
      
    }else{
      
      data=merge(data,DDdata,by.x=c("yearmonth.dd","sector"),by.y=c("yearmonth","sector"),all.x=TRUE)
      
      data$CCAINTSCORE=data$FSOINTSCORE*exp(gamma_model*(data$dma36mdd1))
      #vars=c("yearmonth","sector")
      
    }
    
    
    #get CCA EDF
    data=smoothvlookup(data,trans_model,"Quant","Transform","CCAINTSCORE","unadjCCA")
    data$ErrorMsg=paste0(data$ErrorMsg,ifelse(data$yearmonth.dd<min(DDdata$yearmonth) | data$yearmonth.dd>max(DDdata$yearmonth),"'Current Date': Current Date Range is invalid;",""))
    out=rbind.fill(out,data)
    
  }

  #apply boundaries and formatting
  out$adjCCA=ifelse(out$ttcpd<out$LowerBound1 & out$ttcpd>=0.000001,out$ttcpd*out$unadjCCA/out$FSOEDF,ifelse(out$ttcpd<0.000001,0.000001,ifelse(out$ttcpd==1 | out$unadjCCA>1,1,out$unadjCCA)))
  out=rbind.fill(out,dterror[,c("id","ErrorMsg"),with=FALSE])
  out$'PIT 1Y'=ifelse(is.na(out$adjCCA),"",round(out$adjCCA,digits=6))
  out=out[order(out$id),]
  
  
  if (nYears>1){
    
    
    lTS=ifelse(nYears>=5,5,nYears)
    output = data.frame(matrix(, nrow=nrow(out), ncol=lTS-1))
    
    # linear interpolation within the rating bucket
    for (i in 2:lTS) {
      
      output[,i-1]=smoothvlookup(dataset=as.data.frame(log(out$adjCCA)),lookup.table=TermStruct,lookup.quant="X1YLowBound",lookup.trans=paste0("X",i,"Y"),quant="log(out$adjCCA)",trans="TS")$TS
      
    }
    
    colnames(output)=paste0("PIT ",2:lTS,"Y")
    output=exp(output)
    
    
    if(nYears>5){
      
      #if term structure >5 years, use constant forward rate to extend the term structure
      
      fwd=1-((output$`PIT 5Y`-output$`PIT 4Y`)/(1-output$`PIT 4Y`))
      
      for(k in c(6:nYears)){
        
        output[,k-1]=ifelse(output[,"PIT 5Y"]==1,1,1-((1-output[,"PIT 5Y"])*((fwd)^(k-5))))
      }
      
    }
    
    #Annualized results
    
    for(l in c(2:nYears)){
      output[,l-1]=1-(1-output[,l-1])^(1/l)
      
    }
    
    
    
    colnames(output)=c(paste0("PIT ",c(2:nYears),"Y"))
    
    
    #formatting
    
    output=lapply((output), function(l) sapply(l, function(x) round(x,digits=6)))
    output=setDT(lapply((output), function(l) sapply(l, function(x) ifelse(is.na(x),"",x))))
    out=cbind(`PIT 1Y`=out[,c("PIT 1Y")],output,`Error Msg`=out[,c("ErrorMsg")])
    
  }else{
    out=cbind(`PIT 1Y`=out[,c("PIT 1Y")],`Error Msg`=out[,c("ErrorMsg")])
    
  }
  return(out)
}
 
 
 
#      Ex = fread('TestFiles/InputExamplev2.csv', check.names = F, stringsAsFactors = F)
#      Ex[is.na(Ex)] = ""
#      Ex$'Industry Classification'=c("SIC","Sector","Sector")
#      Ex$'Industry Definition'=c("100","Agriculture","Unassigned")
#      Ex$"Current Date - Year"=as.numeric(c("2019","2019","2019","2019","2019","2019"))
#       Ex$`TTC PD`=c(0.01,0.02,NA)
#      Ex$`TTC PD - Term`=c('',5)
#      #Ex$`TTC PD`=NULL
#     Ex$`Region`=c("NATION","NATION","NATION")
#      input=Ex
#      Ex$`Model Code`=c("USA 4.0","USA 4.0","USA 4.0")
#     Ex$`Number of Years`=c(NA,NA,NA,NA,NA,NA)
#      result=cbind(Ex,getCCAEDF(Ex))
