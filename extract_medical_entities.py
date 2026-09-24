"""
Lambda #2: extract-medical-entities

Triggered by S3 ObjectCreated events on the 'processed/' prefix
(i.e., fires automatically after Lambda #1 finishes).
Reads the extracted text, calls Amazon Comprehend Medical to identify
clinical entities (medications, conditions, procedures, PHI), and
writes a structured record into the PatientRecords DynamoDB table.
"""

import boto3
import json
import uuid

comprehend_medical = boto3.client('comprehendmedical')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('PatientRecords')

def lambda_handler(event, context):
    record = event['Records'][0]
    bucket = record['s3']['bucket']['name']
    key = record['s3']['object']['key']

    # Read the extracted text from Lambda #1's output
    obj = s3.get_object(Bucket=bucket, Key=key)
    data = json.loads(obj['Body'].read())
    text = data['extracted_text']

    # Call Comprehend Medical to pull out clinical entities
    response = comprehend_medical.detect_entities_v2(Text=text)

    entities = []
    for entity in response['Entities']:
        entities.append({
            "text": entity['Text'],
            "category": entity['Category'],
            "type": entity['Type'],
            # DynamoDB's Python SDK doesn't accept native floats directly;
            # converting to string is the simplest fix at this scale.
            "score": str(entity['Score'])
        })

    record_id = str(uuid.uuid4())
    table.put_item(
        Item={
            "record_id": record_id,
            "source_key": data['source_key'],
            "raw_text": text,
            "entities": entities
        }
    )

    return {"status": "success", "record_id": record_id}
