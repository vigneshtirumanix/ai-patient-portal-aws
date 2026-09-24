"""
Lambda #1: extract-text-textract

Triggered by S3 ObjectCreated events on the 'incoming/' prefix.
Calls Amazon Textract's synchronous DetectDocumentText API to extract
raw text from an uploaded patient form (image or single-page PDF),
then writes the result as JSON to the 'processed/' prefix, which
triggers Lambda #2 (extract-medical-entities).
"""

import boto3
import json
import os

textract = boto3.client('textract')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    record = event['Records'][0]
    bucket = record['s3']['bucket']['name']
    key = record['s3']['object']['key']

    # Synchronous Textract call - works for images and single-page PDFs.
    # For multi-page documents at scale, the async Textract API with an
    # SNS callback would be the right choice instead.
    response = textract.detect_document_text(
        Document={'S3Object': {'Bucket': bucket, 'Name': key}}
    )

    lines = [b['Text'] for b in response['Blocks'] if b['BlockType'] == 'LINE']
    extracted_text = "\n".join(lines)

    output_key = f"processed/{os.path.basename(key)}.json"
    s3.put_object(
        Bucket=bucket,
        Key=output_key,
        Body=json.dumps({"source_key": key, "extracted_text": extracted_text})
    )

    return {"status": "success", "output_key": output_key}
