import json
import boto3
import os
from collections import defaultdict

def lambda_handler(event, context):
    # TODO implement
    print("Running handler...")
    jpgbucket = "test-jpg-data"
    templatebucket = "test-templates-data"
    document = "NABForm.jpg"
    template = "NABtemplate_Issues_18.json"
    tmpdir = '/tmp/'
    textract = boto3.client('textract')
    s3 = boto3.client('s3')
  
    s3.download_file(templatebucket, template, tmpdir + template)
    
    jpg_list = s3.list_objects_v2(
        Bucket=jpgbucket,
        Prefix=document[:-4]
    )
    jpg_list = [item['Key'] for item in jpg_list['Contents']]
    
    def split_sort(item):
        num_idx = 0
        for i, c in enumerate(item):
            if c.isdigit():
                num_idx = i
                break
        itemname = item.split('.')[0]
        num = itemname[num_idx:]
        return int(num)
    
    jpg_list.sort(key=split_sort)
    
    page_count = 1
    parsedResults = defaultdict(str)
    with open(tmpdir + template, "r") as templatefile:
        template = templatefile.read()
        template = json.loads(template)
        for jpg in jpg_list:
            response = textract.detect_document_text(
                Document={'S3Object': {'Bucket': jpgbucket, 'Name': jpg}})
            #response = datafile.read()
            #response = json.loads(response)
            
            for block in response['Blocks']:
                if block['BlockType'] == "LINE":
                    geo = block['Geometry']['BoundingBox']
                    for box in template:
                        if box['pageNumber'] == page_count:
                            if geo['Left'] > box["pctLeft"] and geo['Left'] < (box['pctLeft'] + box['pctWidth']) and \
                            geo['Top'] > box["pctTop"] and geo['Top'] < (box['pctTop'] + box['pctHeight']):
                                parsedResults[box["label"]] += block['Text']
            page_count += 1
    return {
        'statusCode': 200,
        'body': parsedResults
    }