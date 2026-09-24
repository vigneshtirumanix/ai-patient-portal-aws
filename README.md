# AI-Powered Healthcare Document Automation Pipeline

A serverless, AI-powered pipeline that automates a manual document-intake workflow. Staff upload scanned patient forms; the system extracts text via OCR, identifies clinical entities using medical NLP, stores the structured results, and exposes them through a secured, authenticated API and web frontend.

Built end-to-end on AWS using the Console (no CDK/CLI for infrastructure), with the frontend built as a plain HTML/JavaScript app.

## What it does

1. A staff member uploads a scanned patient form (image or PDF) to an S3 bucket
2. **Amazon Textract** automatically extracts the raw text (OCR)
3. **Amazon Comprehend Medical** processes that text to identify clinical entities: medications, conditions, procedures, and protected health information
4. The structured result is stored in **DynamoDB**
5. Authenticated users log in via **Amazon Cognito** and query the processed records through a secured **REST API**
6. A lightweight web frontend displays the records and their detected entities

## Architecture

```
[Staff uploads form]
        |
        v
   [S3: incoming/]
        |  (S3 event trigger)
        v
[Lambda #1: extract-text-textract]
        |
        v
   [Amazon Textract] --> raw extracted text
        |
        v
   [S3: processed/]
        |  (S3 event trigger)
        v
[Lambda #2: extract-medical-entities]
        |
        v
[Amazon Comprehend Medical] --> structured clinical entities
        |
        v
   [DynamoDB: PatientRecords]
        ^
        |
[Lambda #3: query-patient-records]
        ^
        |
   [API Gateway: GET /records]
        ^
        |  (JWT validation)
   [Amazon Cognito: User Pool + Authorizer]
        ^
        |
   [Frontend: HTML/JavaScript]
        ^
        |
    [End user, logged in]
```

Every Lambda function has its own IAM role, scoped to only the specific S3 prefixes, DynamoDB actions, and AWS service calls it actually needs (least-privilege access).

## Tech stack

- **Compute:** AWS Lambda (Python 3.12)
- **Storage:** Amazon S3 (encrypted, versioned, public access blocked)
- **Database:** Amazon DynamoDB (on-demand capacity)
- **API:** Amazon API Gateway (HTTP API)
- **Auth:** Amazon Cognito (User Pool + JWT Authorizer)
- **AI services:** Amazon Textract (OCR), Amazon Comprehend Medical (clinical NLP)
- **Monitoring:** Amazon CloudWatch
- **Frontend:** Vanilla HTML/CSS/JavaScript (no framework)
- **IAM:** Least-privilege roles scoped per Lambda function

## Security features

- S3 bucket has all public access blocked; files are only reachable via authenticated requests, never public URLs
- All data encrypted at rest (SSE-S3) and in transit (HTTPS/TLS)
- API endpoints require a valid Cognito-issued JWT; unauthenticated requests are rejected with 401
- Each Lambda function's IAM role is scoped narrowly (e.g., the OCR function can read from `incoming/` and write to `processed/`, and nothing else)
- No hardcoded credentials anywhere in the codebase

## Project structure

```
README.md
frontend/
  index.html          # Login + records viewer, plain HTML/JS
lambda/
  extract_text_textract.py       # Lambda #1: OCR via Textract
  extract_medical_entities.py    # Lambda #2: Clinical NLP via Comprehend Medical
  query_patient_records.py       # Lambda #3: Query API, handles CORS
```

The Lambda files here mirror exactly what's deployed in AWS Lambda; they're included for reference/review rather than automated deployment (this project was built through the AWS Console, not CDK/CLI).

## Setup

This project was built entirely through the AWS Console to maximize hands-on familiarity with each service, though the same architecture could be reproduced via CDK/Terraform.

1. **S3:** Create a bucket with public access blocked, versioning enabled, default encryption on. Create `incoming/` and `processed/` prefixes (they can also be created automatically on first upload).
2. **Lambda #1 (`extract-text-textract`):** Python 3.12 function triggered by S3 `ObjectCreated` events on `incoming/`. Calls Textract's synchronous `detect_document_text` API, writes results to `processed/`.
3. **DynamoDB:** Create a table named `PatientRecords` with partition key `record_id` (String), on-demand billing mode.
4. **Lambda #2 (`extract-medical-entities`):** Triggered by S3 `ObjectCreated` events on `processed/`. Calls Comprehend Medical's `detect_entities_v2`, writes structured results to DynamoDB.
5. **Lambda #3 (`query-patient-records`):** Reads from DynamoDB, returns JSON. Handles CORS preflight (OPTIONS) requests directly in code (see note below).
6. **API Gateway:** HTTP API with a `GET /records` route (and a separate `OPTIONS /records` route with no authorizer, for CORS preflight) pointing to Lambda #3.
7. **Cognito:** User Pool with email-based sign-in; a public app client (no secret) for browser-based authentication.
8. **JWT Authorizer:** Attached to the `GET /records` route, validating tokens against the Cognito User Pool's issuer.
9. **Frontend:** Update the config values at the top of `frontend/index.html` (Cognito Client ID, API URL, region) with your own resource IDs, then open the file in a browser.

Each IAM role's inline policy should be scoped to the specific resource ARNs involved (see comments in each Lambda's setup for the exact permissions used).

## Known limitations / what I'd improve with more time

- **CORS handling is implemented directly in Lambda code** rather than through API Gateway's built-in CORS configuration. During development, I found that API Gateway's automatic CORS system and a custom Lambda-based CORS response can conflict, with the platform-level config silently overriding the Lambda's response. Handling it explicitly in code proved more reliable for this project's scope.
- **DynamoDB queries use `Scan`** for listing all records, which doesn't scale well. At real scale, this would need a proper query pattern with a secondary index.
- **No real HIPAA compliance** — this project follows healthcare-adjacent security patterns (encryption, access control, least privilege) but does not include the legal/compliance apparatus (signed BAA, audit logging requirements, etc.) that real PHI handling would require.
- **No automated tests or CI/CD pipeline** yet — would add unit tests for each Lambda and a basic GitHub Actions workflow for linting/deployment checks.
- **Frontend is not yet hosted** — currently run locally by opening `index.html` directly; a production version would host this via S3 + CloudFront.

## A debugging note worth mentioning

The trickiest bug in this project was a duplicate Python function definition: two `def lambda_handler(event, context):` blocks existed in the same file, and Python silently let the second one overwrite the first. This meant a CORS-handling code path that looked correct in the file was actually dead code, never executing. It took working backward through Lambda console test events, direct `curl` testing against the live API, and comparing AWS's stated CORS configuration against actual server responses to isolate. A good reminder that "the code looks right" and "the code runs" are different claims worth verifying separately.

## Project status

Core pipeline (upload -> OCR -> clinical NLP -> storage -> secured API -> frontend display) is fully functional and tested end-to-end.
