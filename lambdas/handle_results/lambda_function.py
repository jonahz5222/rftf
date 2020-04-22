import json
import boto3
import os
from collections import defaultdict
import pprint

def lambda_handler(event, context):
    #HANDLE RESULTS
    #jpgbucket = os.environ['JPG_BUCKET']
    #templatebucket = os.environ['TEMPLATE_BUCKET']
    status = event['responsePayload']['returnStatus']
    body = event['responsePayload']['body']
    document = event['requestPayload']['requestPayload']['requestPayload']['Records'][0]['s3']['object']['key']
    bucket = event['requestPayload']['requestPayload']['requestPayload']['Records'][0]['s3']['bucket']['name']
    
    if status == 'complete':
        print("Parsing completed.")
        s3 = boto3.client('s3')
        s3.delete_object(Bucket=bucket, Key=document)
        
        jpg_doc = document.split("/")
        jpg_doc[0] = "jpg"
        jpg_doc[1] = jpg_doc[1].split(".")[0]
        jpg_doc = "/".join(jpg_doc)
        print(jpg_doc)
        jpg_list = s3.list_objects_v2(
            Bucket=bucket,
            Prefix=jpg_doc
        )
        jpg_list = [item['Key'] for item in jpg_list['Contents'] if item['Key'][-4:] == ".jpg"]
        
        for jpg in jpg_list:
            s3.delete_object(Bucket=bucket, Key=jpg)
        
        return {
            'statusCode': 200,
            'returnStatus': 'success'
        }
    elif status == 'incomplete':
        print("Templates missing for some pages.")
        print(body)
        return {
            'statusCode': 200,
            'returnStatus': 'failure'
        }
    else:
        print("Parsing failed.")
        return {
            'statusCode': 200,
            'returnStatus': status
        }