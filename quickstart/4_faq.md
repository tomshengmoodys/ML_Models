# Frequently Asked Questions

## My model takes some additional command line inputs beyond what's available here. Where can I add them?

Check out the `model/run.py` script. Here, you can add CLI flags. Don't forget to pass them to the model (`model/model.py`).

## I use an API that requires credentials other than those of the tenant user. How can I use them?

Use the `-t` flag to pass an additional JWT or `-p` flag to pass a username and password for a proxy user. A separate `CAPSession` object will be authenticated for the user and is available in the model module as `self.proxy_cap_session`.

## Where can I find some examples?

Check out the following models for inspiration:

* [Commercial Mortgage Metrics](https://github.com/moodysanalytics/model-cmm.git): Model with proxy user usage for external API call
* [Commercial Real Estate - Loss Rate](https://github.com/moodysanalytics/model-cre-lr.git): Model wrapping existing Python code
* [Private Firm Converter](https://github.com/moodysanalytics/model-pit-converter.git): Model wrapping existing R code
* [RiskCalc LGD](https://github.com/moodysanalytics/model-risk-calc-lgd.git): Model with proxy user for internal API call
* [MUNI Loss Forecast](https://github.com/moodysanalytics/model-muni.git): Model with proxy user for external API call