# Getting Started with the CAP Model Registry

## How to use this Guide

Multiple domains exist for each model, for example:

* QA - For development
* EA - Early access for certain customers
* PRD - Production environment

All examples will use the QA version of the model API. To set up a model in another environment, use the correct API swagger page in place of the examples.

### SSO API Swagger Pages

* QA - https://qa-api.sso.moodysanalytics.net/sso-api/docs/
* EA - https://ea-api.sso.moodysanalytics.com/sso-api/docs/
* PRD - https://sso.moodysanalytics.com/sso-api/docs/

### Model Manager Swagger Pages

* QA - https://qa-api.cap.moodysanalytics.net/model/docs/
* EA - https://ea-api.cap.moodysanalytics.com/model/docs/
* PRD - https://api.cap.moodysanalytics.com/model/docs

## Procedures

### First steps

1. Get a valid JWT for the environment you are using.
   1. Go to https://qa-api.sso.moodysanalytics.net/sso-api/docs/
   2. At the top, click "Authorize" and provide a username and password. Click "Authorize."
   3. Open the POST /sso-api/auth/token endpoint and click "Try it out", followed by "Execute."
      1. If the API returns anything other than a 200 code, inspect your credentials.
   4. Copy the returned JWT from the response body, excluding the surrounding `"` characters.
2. Authorize the Model Manager API.
   1. Go to https://qa-api.cap.moodysanalytics.net/model/docs/
   2. At the top, click "Authorize" and paste in the JWT from the previous step. Click "Authorize."
3. Check for latest model ID and version.
   1. Expand `GET /v2/models` endpoint and select "Try it out."
   2. Enter the name of the model you are creating or updating and click "Execute."
   3. If the model exists, information will be returned for the latest version.
      1. If no model information is returned, then no model exists with that name.
      2. If you are creating a new model, and model information is returned, you must pick a new name.
         * __At the time of this writing, unique model names are not enforced by the Model Manager API. It is incumbent upon you, the developer, to ensure that no name duplication occurs.__

## Setting up a model for the first time

1. Ensure your model name is unique, following step 3 above.
2. Create model.
   1. Expand `POST /v2/models` endpoint and click "Try it out."
   2. Fill out the example JSON using correct values for your model.
   3. Click "Execute."
   4. Model version will be returned with a 200 status if model creation was successful.

## Updating an existing model

1. Retrieve the latest model version information, following step 3 above.
2. Update model.
   1. Expand `PUT /v2/models/{modelName}/versions/{versionName}` endpoint and click "Try it out."
   2. Fill out the example JSON using correct values for your model.
   3. Click "Execute."
   4. Model version will be returned with a 200 status if model update was successful.

## Next up

Check out the [FAQ](4_faq.md)