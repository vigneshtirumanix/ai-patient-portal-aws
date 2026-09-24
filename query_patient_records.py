"""
Lambda #3: query-patient-records

Backs the GET /records and OPTIONS /records API Gateway routes.
Reads processed patient records from DynamoDB and returns them as JSON.

Note: CORS preflight (OPTIONS) requests are handled directly in code
here, rather than relying solely on API Gateway's built-in CORS
configuration. During development, API Gateway's automatic CORS
handling and this Lambda's own CORS headers conflicted, with the
platform-level config silently overriding the Lambda's response.
Handling it explicitly in code proved more reliable.
"""

import boto3
import json
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('PatientRecords')

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError

def lambda_handler(event, context):
    # Handle CORS preflight requests directly
    if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "authorization,content-type",
                "Access-Control-Allow-Methods": "GET,OPTIONS"
            },
            "body": ""
        }

    params = event.get('queryStringParameters') or {}
    record_id = params.get('record_id')

    if record_id:
        # Fetch a single record
        response = table.get_item(Key={'record_id': record_id})
        item = response.get('Item')
        if not item:
            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "authorization,content-type",
                    "Access-Control-Allow-Methods": "GET"
                },
                "body": json.dumps({"error": "Record not found"})
            }
        body = item
    else:
        # List all records. Fine at this scale; a real-scale version
        # would use a proper query pattern with a secondary index
        # instead of Scan.
        response = table.scan()
        body = response.get('Items', [])

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "authorization,content-type",
            "Access-Control-Allow-Methods": "GET"
        },
        "body": json.dumps(body, default=decimal_default)
    }
