import json
import boto3
import os
from collections import defaultdict
import pprint

def lambda_handler(event, context):

    # {
      # "Records": [
        # {
          # "eventVersion": "2.1",
          # "eventSource": "aws:s3",
          # "awsRegion": "us-east-2",
          # "eventTime": "2019-09-03T19:37:27.192Z",
          # "eventName": "ObjectCreated:Put",
          # "userIdentity": {
            # "principalId": "AWS:AIDAINPONIXQXHT3IKHL2"
          # },
          # "requestParameters": {
            # "sourceIPAddress": "205.255.255.255"
          # },
          # "responseElements": {
            # "x-amz-request-id": "D82B88E5F771F645",
            # "x-amz-id-2": "vlR7PnpV2Ce81l0PRw6jlUpck7Jo5ZsQjryTjKlc5aLWGVHPZLj5NeC6qMa0emYBDXOo6QBU0Wo="
          # },
          # "s3": {
            # "s3SchemaVersion": "1.0",
            # "configurationId": "828aa6fc-f7b5-4305-8584-487c791949c1",
            # "bucket": {
              # "name": "lambda-artifacts-deafc19498e3f2df",
              # "ownerIdentity": {
                # "principalId": "A3I5XTEXAMAI3E"
              # },
              # "arn": "arn:aws:s3:::lambda-artifacts-deafc19498e3f2df"
            # },
            # "object": {
              # "key": "b21b84d653bb07b05b1e6b33684dc11b",
              # "size": 1305107,
              # "eTag": "b21b84d653bb07b05b1e6b33684dc11b",
              # "sequencer": "0C0F6F405D6ED209E1"
            # }
          # }
        # }
      # ]
    # }
    
    
    jpgbucket = event['document_bucket']
    templatebucket = event['templates_bucket']
    document = event['document'] #"NABForm"
    template = event['template'] #"NABtemplate_Issues_18.json"
    page = 0
    try:
        page = event['page']
    except Exception as e:
        pass
    tmpdir = '/tmp/'
    textract = boto3.client('textract')
    
    #minimum confidence percentage to be labelled as machine text instead of handwriting
    minimum_confidence = 95
    try:
        minimum_confidence = event['minimum_confidence']
    except Exception as e:
        pass
    
    #the minimum overlap between a template box and a recognized line in order for the template to catch the line
    overlap_threshold = 0.6
    try:
        overlap_threshold = event['overlap_threshold']
    except Exception as e:
        pass
    
    #establish S3 connection
    s3 = boto3.client('s3')
  
    #retrieve template JSON from S3 bucket
    s3.download_file(templatebucket, template, tmpdir + template)
    
    #retrieve list of JPGs that correspond to the pages of the PDF
    #format should be pdfname1.jpg, pdfname2.jpg, etc.
    jpg_list = s3.list_objects_v2(
        Bucket=jpgbucket,
        Prefix=document
    )
    jpg_list = [item['Key'] for item in jpg_list['Contents']]
    print(jpg_list)
    #custom sort function that sorts by the number at the end of the filename
    def split_sort(item):
        itemname = item.split('.')[0]
        num = itemname[len(document):]
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
            #if page is a valid page number, only process that page. Saves me some billed processing time lol
            if(page > 0 and page <= page_count):
                if page_count != page:
                    continue
        
            response = textract.detect_document_text(
                Document={'S3Object': {'Bucket': jpgbucket, 'Name': jpg}})

            #identify marker and figure offset
            page_offsets = {}
            for marker in [item for item in template if item['is_marker'] == True and item['pageNumber'] == page_count]:
                for block in response['Blocks']:
                    if block['BlockType'] == "LINE":
                        if block['Text'] in marker['label']:
                            geo = block['Geometry']['BoundingBox']
                            offsetX = geo['Left'] - marker['pctLeft']
                            offsetY = geo['Top'] - marker['pctTop']
                            page_offsets[marker['pageNumber']] = [offsetX, offsetY]
                            
                
            print(page_offsets)
            #iterate through every box in the template file
            for box in [item for item in template if item['is_marker'] == False and item['pageNumber'] == page_count]:
                #apply offsets gained from marker
                if page_count in page_offsets:
                    box["pctLeft"] += page_offsets[page_count][0]
                    box["pctTop"] += page_offsets[page_count][1]
                    box["pctWidth"] += page_offsets[page_count][0]
                    box["pctHeight"] += page_offsets[page_count][1]
            
                #if template box is on the right page
                group = defaultdict(str)
                group['text'] = ""
                group['handwritten'] = False
                for block in response['Blocks']:
                    #Textract returns text as a LINE BlockType
                    if block['BlockType'] == "LINE":
                        geo = block['Geometry']['BoundingBox']
                        
                        #calculate overlap. If overlap percentage is over threshold, assign text to template box
                        if get_overlap(box, geo) > overlap_threshold:
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
    
def get_overlap(box1, box2):
    """
    Calculate the overlap of the template box with the target text.

    Parameters
    ----------
    bb1 : dict
        Keys: {'x1', 'x2', 'y1', 'y2'}
        The (x1, y1) position is at the top left corner,
        the (x2, y2) position is at the bottom right corner
    bb2 : dict
        Keys: {'x1', 'x2', 'y1', 'y2'}
        The (x, y) position is at the top left corner,
        the (x2, y2) position is at the bottom right corner

    Returns
    -------
    float
        in [0, 1]
    """
    bb1 = {}
    bb2 = {}
    
    bb1['x1'] = box1['pctLeft']
    bb1['x2'] = box1['pctLeft'] + box1['pctWidth']
    bb1['y1'] = box1['pctTop']
    bb1['y2'] = box1['pctTop'] + box1['pctHeight']
    bb2['x1'] = box2['Left']
    bb2['x2'] = box2['Left'] + box2['Width']
    bb2['y1'] = box2['Top']
    bb2['y2'] = box2['Top'] + box2['Height']
    
    
    assert bb1['x1'] < bb1['x2']
    assert bb1['y1'] < bb1['y2']
    assert bb2['x1'] < bb2['x2']
    assert bb2['y1'] < bb2['y2']

    # determine the coordinates of the intersection rectangle
    x_left = max(bb1['x1'], bb2['x1'])
    y_top = max(bb1['y1'], bb2['y1'])
    x_right = min(bb1['x2'], bb2['x2'])
    y_bottom = min(bb1['y2'], bb2['y2'])

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    # The intersection of two axis-aligned bounding boxes is always an
    # axis-aligned bounding box
    intersection_area = (x_right - x_left) * (y_bottom - y_top)

    # compute the area of both AABBs
    bb2_area = (bb2['x2'] - bb2['x1']) * (bb2['y2'] - bb2['y1'])

    # compute the overlap of the intersection with the target text
    overlap = intersection_area / bb2_area
    
    assert overlap >= 0.0
    assert overlap <= 1.0
    return overlap