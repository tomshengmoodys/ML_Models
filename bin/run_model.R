library(argparser, quietly=TRUE)
library(jsonlite)
library(magrittr, warn.conflicts = FALSE)
library(data.table, warn.conflicts = FALSE)
library(log4r, warn.conflicts = FALSE)
# For testing: source("./bin/example_r_model_script.R")


# Define constants
NUMBER_OF_YEARS <- 10


# Parse input arguments
p <- arg_parser("TTC2PIT converter")
p <- add_argument(p, "--inputPath", help="model run parameter input path", short = '-p')
p <- add_argument(p, "--location", help="package directory path", short = '-l')
argv <- parse_args(p)

# For testing:  parameter.path <- "./test/sample-test/modelRunParameter.json"
parameter.path <- argv$inputPath
parameters <- read_json(parameter.path)

# Source model code
# For testing: package.path <- getwd()
package.path <- argv$location
source(file.path(package.path, "bin", "example_r_model_script.R"))

# Define logging utilities
log.path <- parameters$settings$logPath
dir.create(log.path, showWarnings = FALSE)
logger <- create.logger()
logfile(logger) <- file.path(log.path, "debug.log")
level(logger) <- "DEBUG"
  
LogMessage <- function(msg){
  debug(logger, msg)
}

LogErrorAndQuit <- function(err, msg){
  fatal(logger, err)
  debug(logger, msg)
  quit(status=1)
}

tracer <- create.logger()
logfile(tracer) <- file.path(log.path, "trace.log")
level(tracer) <- "DEBUG"

WriteTrace <- function(messages){
  for (msg in messages) {
    debug(tracer, msg)
  }
}


# Define step execution utilities
Execute <- function(argument, step) {
  tryCatch({
    LogMessage(paste(step, "Started"))
    eval(call(step, argument))
  }, error = function(err) {
    LogErrorAndQuit(err, paste(step, "Failed"))
  })
}

# Reading input data and reporting date
ReadData <- function(parameters) {
  data.path <- parameters$settings$inputPath
  data <- fread(file.path(data.path, "instrumentReference.csv"))

  # Cleanup input data: remove NA and change columns to all lower case
  data[is.na(data)] <- ""
  oldColnames = colnames(data)
  setnames(data, old = oldColnames, new = gsub(" ", "", tolower(colnames(data)), fixed = TRUE))

  reportingDate <- as.Date(parameters$settings$reportingDate, format="%Y-%m-%d")
  runDate <- as.Date(parameters$settings$runDate, format="%Y-%m-%d")

  # Record input data in trace
  WriteTrace(list("***************** Input data *******************",
                  "Input Data(by column):", data,
                  "Reporting Date:", reportingDate,
                  "Run Date:", runDate))

  return(list(data = data,
              reporting.date = reportingDate,
              run.date = runDate,
              parameters = parameters))
}

# Transform input data into get instrumetn risk metric
TransformData <- function(input) {


  # prepare arguments for transformation
  currentYear <- year(min(input$reporting.date, input$run.date))
  currentMonth <- month(min(input$reporting.date, input$run.date))

  # define transform function
  transformRow <- function(inst) {
    # prepare induustry classification and industry definition
    if (inst$moodysindustrysector != "") {
      industry.class <- "Sector"
      industry.definition <- inst$moodysindustrysector
    } else {
      industry.class <- "NAICS"
      industry.definition <- inst$primaryindustrynaics
    }

    # get runResult
    arguments <- list("Obligor Name"="",
                      "Obligor Key"="",
                      "Current Date - Year" = currentYear,
                      "Current Date - Month" = currentMonth,
                      "Region"=inst$borrowerstate,
                      "Industry Classification"=industry.class,
                      "TTC PD"=inst$ttcannualizedpdoneyear,
                      "Model Code"=inst$privatefirmmodelname,
                      "Industry Definition"=industry.definition,
                      "Number of Years"=NUMBER_OF_YEARS)
    runResult <- getCCAEDF(arguments)
    
    # transform runResult
    df <- data.frame(cbind(instrumentidentifier = inst$instrumentidentifier, term = 1:NUMBER_OF_YEARS))
    transformed <- cbind(t(unname(runResult[,1:NUMBER_OF_YEARS])), df)
    errMsg <- runResult$`Error Msg`
    return(list(data.transformed = transformed, 
                error.message = errMsg))
  }
  
  # initialize data holder for transformed result and error messages
  totalRows <- nrow(input$data) * NUMBER_OF_YEARS
  result <- data.frame(annualizedcumulativepd = rep(NA, totalRows),
                       instrumentidentifier = rep(NA, totalRows),
                       term = rep(NA, totalRows),
                       scenarioIdentifier = rep('0', totalRows),
                       asOfDate = rep(input$run.date, totalRows))
  errorMessages <- data.frame(analysisidentifier = character(),
                              errorcode = character(),
                              errormessgae = character(),
                              instrumentidentifier = character(),
                              modulecode = character(),
                              portfolioidentifier = character(),
                              scenarioidentifier = character())
  
  # transform data and put into data holder
  WriteTrace("***************** Model output *******************")
  for (row in 1:nrow(input$data)) {
    rowResult <- transformRow(input$data[row, ])
    WriteTrace(list(paste("Instrument:", input$data$instrumentidentifier[row]),
                    "Annualized Cummulative PD:", 
                    rowResult$data.transformed[ ,1]))
    
    # If there is error for this instrument, register the error message and discard the transformed result
    # else register the transformed result
    if (rowResult$error.message != "") {
      errorMessages <- rbind(errorMessages, list(analysisidentifier = "",
                                                 errorcode = "100",
                                                 errormessgae = rowResult$error.message,
                                                 instrumentidentifier = input$data$instrumentidentifier[row],
                                                 modulecode = "PIT Coverter",
                                                 portfolioidentifier = "",
                                                 scenarioidentifier = ""))
    } else { 
      start = (row - 1) * NUMBER_OF_YEARS + 1
      end = row*NUMBER_OF_YEARS
      result[start:end, 1:3] <- rowResult$data.transformed
    }
  }
  
  result.cleaned <- result[complete.cases(result$instrumentidentifier), ]
  return(list(data = result.cleaned,
              error.messages = errorMessages,
              parameters = input$parameters))
}

# Write csv
WriteOutput <- function(output) {
  
  # write risk metrics
  risk.metric.path <- output$parameters$settings$outputPaths$instrumentRiskMetric
  dir.create(risk.metric.path, showWarnings = FALSE, recursive = TRUE)
  write.csv(output$data, file.path(risk.metric.path, 'instrumentRiskMetric.csv'), row.names=FALSE, quote=FALSE)
  
  
  # write error file
  error.path <- output$parameters$settings$outputPaths$instrumentError
  if (nrow(output$error.messages) > 0 ) {
    dir.create(error.path, showWarnings = FALSE, recursive = TRUE)
    write.csv(output$error.messages, file.path(error.path, 'instrumentError.csv'), row.names=FALSE, quote=FALSE)
  }
  
  # copy paste instrumetnReference.csv
  data.path <- output$parameters$settings$inputPath
  instrument.path <- output$parameters$settings$outputPaths$instrumentReference
  dir.create(instrument.path, showWarnings = FALSE, recursive = TRUE)
  file.copy(from = file.path(data.path, "instrumentReference.csv"),
            to = file.path(instrument.path, "instrumentReference.csv"),
            overwrite = TRUE)
}


# Chain all steps together
parameters %>% Execute(step = "ReadData") %>% Execute(step = "TransformData") %>% Execute(step = "WriteOutput") 
  
log4r::debug(logger, 'Model Run Completed Successfully')