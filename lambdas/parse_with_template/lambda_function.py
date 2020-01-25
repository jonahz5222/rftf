import json
import boto3
import os
from collections import defaultdict

def lambda_handler(event, context):


    jpgbucket = "test-jpg-data"
    templatebucket = "test-templates-data"
    document = "NABForm.jpg"
    template = "NABtemplate_Issues_18.json"
    tmpdir = '/tmp/'
    textract = boto3.client('textract')
    
    #minimum confidence percentage to be labelled as machine text instead of handwriting
    minimum_confidence = 95
    
    #establish S3 connection
    s3 = boto3.client('s3')
  
    #retrieve template JSON from S3 bucket
    s3.download_file(templatebucket, template, tmpdir + template)
    
    #retrieve list of JPGs that correspond to the pages of the PDF
    #format should be pdfname1.jpg, pdfname2.jpg, etc.
    jpg_list = s3.list_objects_v2(
        Bucket=jpgbucket,
        Prefix=document[:-4]
    )
    jpg_list = [item['Key'] for item in jpg_list['Contents']]
    
    #custom sort function that sorts by the number at the end of the filename
    def split_sort(item):
        num_idx = 0
        for i, c in enumerate(item):
            if c.isdigit():
                num_idx = i
                break
        itemname = item.split('.')[0]
        num = itemname[num_idx:]
        return int(num)
    
    #sort using above function
    jpg_list.sort(key=split_sort)
    
    
    #parse each JPG using template JSON
    page_count = 1
    parsedResults = defaultdict(str)
    with open(tmpdir + template, "r") as templatefile:
        template = templatefile.read()
        template = json.loads(template)
        for jpg in jpg_list:
            response = textract.detect_document_text(
                Document={'S3Object': {'Bucket': jpgbucket, 'Name': jpg}})

            #iterate through every box in the template file
            for box in template:
                #if template box is on the right page
                if box['pageNumber'] == page_count:
                    group = defaultdict(str)
                    group['text'] = ""
                    group['handwritten'] = False
                    for block in response['Blocks']:
                        #Textract returns text as a LINE BlockType
                        if block['BlockType'] == "LINE":
                            geo = block['Geometry']['BoundingBox']
                            #if the upper left corner of the text falls within the current template box, assign text to box
                            if geo['Left'] > box["pctLeft"] and geo['Left'] < (box['pctLeft'] + box['pctWidth']) and \
                            geo['Top'] > box["pctTop"] and geo['Top'] < (box['pctTop'] + box['pctHeight']):
                                group['text'] += block['Text']
                                #if Textract isn't confident about OCR, label it handwriting
                                if block['Confidence'] < minimum_confidence:
                                    group['handwritten'] = True
                    parsedResults[box['label']] = group
            page_count += 1
            
    #return parsed results
    return {
        'statusCode': 200,
        'body': parsedResults
    }