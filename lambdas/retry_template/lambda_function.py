import json
import boto3
import os
from collections import defaultdict
import pprint

def lambda_handler(event, context):
    #HANDLE RESULTS
    #jpgbucket = os.environ['JPG_BUCKET']
    #templatebucket = os.environ['TEMPLATE_BUCKET']
    
    jpgbucket = os.environ['JPG_BUCKET']
    templatebucket = event['Records'][0]['s3']['bucket']['name']
    document = event['Records'][0]['s3']['object']['key']
    document = document.split("/")[0]
    #document = document.split("/")[-2]
    bucket = event['Records'][0]['s3']['bucket']['name']
    
    s3 = boto3.client('s3')
  
    template_list = s3.list_objects_v2(
        Bucket=templatebucket,
        Prefix=document
    )
    template_list = [item['Key'] for item in template_list['Contents'] if item['Key'][-1] != "/"]
    
    validation_flags = [False,False]
    for temp in template_list:
        if "boxes.json" in temp:
            validation_flags[0] = True
        if "ocr.json" in temp:
            validation_flags[1] = True
    
    if validation_flags[0] != True or validation_flags[1] != True:
        return {}
  
    jpg_list = s3.list_objects_v2(
        Bucket=jpgbucket,
        Prefix='jpg'
    )
    jpg_list = [item['Key'] for item in jpg_list['Contents'] if item['Key'][-4:] == ".jpg"]
    grouped_jpgs = {}
    for jpg in jpg_list:
        idx = 0
        for i,ch in enumerate(jpg):
            if ch == "/":
                idx = i
    
        prefix = jpg[:idx+1]
        if prefix in grouped_jpgs:
            grouped_jpgs[prefix].append(jpg)
        else:
            grouped_jpgs[prefix] = [jpg]
    print(jpg_list)
    print(grouped_jpgs)
    
    #with open("/tmp/payload.json", "w") as f:
    #    f.write("{'test':1}")
    for key in grouped_jpgs:
        payload = {}
        payload['retry'] = 1
        payload['jpgs'] = grouped_jpgs[key]
        payload['templates'] = template_list
        pylambda = boto3.client('lambda')
        pylambda.invoke(FunctionName="og-identify-template",InvocationType="Event",Payload=json.dumps(payload))
    

    
    