import boto3
import botocore
import sys
import json
import ast
import pprint
import time, os
from collections import defaultdict
from pdf2image import convert_from_path, convert_from_bytes
from pdf2image.exceptions import (
    PDFInfoNotInstalledError,
    PDFPageCountError,
    PDFSyntaxError
)
        
        
if __name__ == "__main__":

    in_file = sys.argv[1]

    images = convert_from_path(in_file)
    
    file, ext = os.path.splitext(in_file)
    filename = file + ".jpg"
    
    images[0].save(filename, "JPEG")

    print("Inserting document into S3...")

    s3 = boto3.resource('s3')
    sns = boto3.client('sns')
    bucketname = "opif-textract-data"
    topic_ARN = "arn:aws:sns:us-east-2:891440894509:textract_operations"
    role_ARN = "arn:aws:iam::891440894509:role/textract_sns_role"
    
    data = open(filename, 'rb')
    try:
        s3.Object(bucketname, filename).load()
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            s3.Bucket(bucketname).put_object(Key=filename, Body=data)
        else:
            # Something else has gone wrong.
            raise e
    else:
        print("File '" + str(filename) + "' is already in S3 Bucket.")
    
    print("Object placed in S3. Parsing text data...")
    
    textract = boto3.client('textract',region_name='us-east-2')
    
    a='''result = textract.start_document_text_detection(
        DocumentLocation={
            'S3Object': {
                'Bucket': bucketname,
                'Name': filename
            }
        },
        NotificationChannel={
            'SNSTopicArn': topic_ARN,
            'RoleArn': role_ARN
        }
    )'''
    
    response = textract.detect_document_text(
        Document={
            'S3Object': {
                'Bucket': bucketname,
                'Name': filename,
            }
        }
    )
    
    #print(response)
    
    b='''response = textract.get_document_text_detection(JobId=result['JobId'])
    while(response['JobStatus'] != "SUCCEEDED"):
        print("Status: " + str(response['JobStatus']))
        time.sleep(2)
        response = textract.get_document_text_detection(JobId=result['JobId'])
    '''
   
    with open(sys.argv[2], "r") as templatefile:
        #response = datafile.read()
        #response = json.loads(response)
        
        template = templatefile.read()
        template = json.loads(template)
        
        parsedResults = defaultdict(str)
        
        for block in response['Blocks']:
            if block['BlockType'] == "LINE":
                geo = block['Geometry']['BoundingBox']
                for box in template:
                    if box['pageNumber'] == 1:
                        if geo['Left'] > box["pctLeft"] and geo['Left'] < (box['pctLeft'] + box['pctWidth']) and \
                        geo['Top'] > box["pctTop"] and geo['Top'] < (box['pctTop'] + box['pctHeight']):
                            parsedResults[box["label"]] += block['Text']
                        
        pprint.pprint(parsedResults)
            
    
    
    
    