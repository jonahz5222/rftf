import json
import boto3
import os
from collections import defaultdict
import pprint

def lambda_handler(event, context):
    #PARSE TEMPLATE

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
    
    
    jpgbucket = os.environ['JPG_BUCKET']
    templatebucket = os.environ['TEMPLATE_BUCKET']
    documents = event['responsePayload']['documents']
    matches = event['responsePayload']['matches']
    
    if None in matches:
        return {
            'statusCode': 200,
            'returnStatus': 'incomplete',
            'body': {'matches' : len(matches) - matches.count(None), 'total' : len(documents)}
        }

    tmpdir = '/tmp/'
    textract = boto3.client('textract')

    #minimum confidence percentage to be labelled as machine text instead of handwriting
    minimum_confidence = 95
    
    #the minimum overlap between a template box and a recognized line in order for the template to catch the line
    overlap_threshold = 0.75
    
    #establish S3 connection
    s3 = boto3.client('s3')
  

    #retrieve list of JPGs that correspond to the pages of the PDF
    #format should be pdfname1.jpg, pdfname2.jpg, etc.
    jpg_list = documents   
    
    #parse each JPG using template JSON
    page_count = 1
    parsedResults = defaultdict(str)
    
    for jpg in jpg_list:
        template_name = matches[page_count-1]['template']
        
        offsets = matches[page_count-1]['offsets']
        template_page = matches[page_count-1]['page']
        
        s3.download_file(templatebucket, template_name, tmpdir + template_name.split('/')[-1])
        with open(tmpdir + template_name.split('/')[-1], "r") as templatefile:
            template = templatefile.read()
            template = json.loads(template)
    
        
            response = textract.detect_document_text(
                Document={'S3Object': {'Bucket': jpgbucket, 'Name': jpg}})
            #iterate through every box in the template file
            
            ######
            template_page_count = 1
            for page in template["pages"]:
                if template_page_count == page_count:
                    boxes = [x for x in page["objects"] if x["type"] == "rect"]
                    for box in boxes:
                        box["pctLeft"] += offsets['x']
                        box["pctTop"] += offsets['y']
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
                template_page_count += 1
                
            ######             
            page_count += 1
            
    #return parsed results
    print("Result:")
    print(parsedResults)
    return {
        'statusCode': 200,
        'returnStatus': 'complete',
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