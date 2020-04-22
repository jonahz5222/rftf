import json
import boto3
import os
from collections import defaultdict
import pprint
from statistics import stdev, mean

def lambda_handler(event, context):
    #IDENTIFY TEMPLATE

    #{
      # 'version': '1.0',
      # 'timestamp': '2020-02-22T01:16:34.701Z',
      # 'requestContext': {
        # 'requestId': 'ef75c37b-044a-441f-8b03-1d5a497dd0eb',
        # 'functionArn': 'arn:aws:lambda:us-east-2:796077402566:function:og-pdf-to-jpg-conversion:$LATEST',
        # 'condition': 'Success',
        # 'approximateInvokeCount': 1
      # },
      # 'requestPayload': {
        # 'Records': [
          # {
            # 'eventVersion': '2.1',
            # 'eventSource': 'aws:s3',
            # 'awsRegion': 'us-east-2',
            # 'eventTime': '2020-02-22T01:16:14.620Z',
            # 'eventName': 'ObjectCreated:Put',
            # 'userIdentity': {
              # 'principalId': 'AWS:AIDA3SWPJFHDINSURJT46'
            # },
            # 'requestParameters': {
              # 'sourceIPAddress': '128.206.251.148'
            # },
            # 'responseElements': {
              # 'x-amz-request-id': '32D75585C920AC68',
              # 'x-amz-id-2': 'zk0mltzH+LFMsLw/9iKbXrhwVZxUoS1zvczVOf8f9018METmJ36LIftkGAqO9HxO1BdxO4iQ9GV4REaiT15BT/i4QSk7BNho'
            # },
            # 's3': {
              # 's3SchemaVersion': '1.0',
              # 'configurationId': 'pdf-to-jpg-trigger',
              # 'bucket': {
                # 'name': 'og-document-data',
                # 'ownerIdentity': {
                  # 'principalId': 'A3ELL71ISRS6EL'
                # },
                # 'arn': 'arn:aws:s3:::og-document-data'
              # },
              # 'object': {
                # 'key': 'pdf/Josh_Hawley_for_Senate_Agreement.pdf',
                # 'size': 93263,
                # 'eTag': '851a3270d2e885c38117ec750ef28951',
                # 'sequencer': '005E5080DE945CDCB4'
              # }
            # }
          # }
        # ]
      # },
      # 'responseContext': {
        # 'statusCode': 200,
        # 'executedVersion': '$LATEST'
      # },
      # 'responsePayload': {
        # 'empty': False
      # }
    # }
    
    
    jpgbucket = os.environ['JPG_BUCKET']
    jpgfolder = os.environ['JPG_FOLDER']
    templatebucket = os.environ['TEMPLATE_BUCKET']
    document = None
    jpg_list = None
    template_list = None
    
    s3 = boto3.client('s3')
    
    if "retry" in event:
        jpg_list = event['jpgs']
        template_list = event['templates']
    else:
        document = event['requestPayload']['Records'][0]['s3']['object']['key']
        document = document.split(".")[0].split("/")[-1]
        jpg_list = s3.list_objects_v2(
            Bucket=jpgbucket,
            Prefix=jpgfolder + document
        )
        jpg_list = [item['Key'] for item in jpg_list['Contents'] if item['Key'][-4:] == ".jpg"]
        
        template_list = s3.list_objects_v2(
            Bucket=templatebucket
        )
        template_list = [item['Key'] for item in template_list['Contents'] if item['Key'][-1] != "/"]
    #template = event['template'] #"NABtemplate_Issues_18.json"
    page = 0
    
    match_threshold = 0.8

    tmpdir = '/tmp/'
    textract = boto3.client('textract')
    
    #establish S3 connection
    
  
    #retrieve template JSON from S3 bucket
    #s3.download_file(templatebucket, template, tmpdir + template)
    
    #retrieve list of JPGs that correspond to the pages of the PDF
    #format should be pdfname1.jpg, pdfname2.jpg, etc.
    
    
    #custom sort function that sorts by the number at the end of the filename
    def split_sort(item):
        item = item.split('/')[-1]
        item = item.split('.')[0]
        return int(item)
    
    #sort using above function
    jpg_list.sort(key=split_sort)
    
    
    #parse each JPG using template JSON
    page_count = 1
    parsedResults = defaultdict(str)
    
    
    def median(a, l, r): 
        n = r - l + 1
        n = (n + 1) // 2 - 1
        return n + l 
  
    # Function to calculate interquartile range
    def IQR(a, n): 
      
        a.sort() 
      
        # Index of median of entire data 
        mid_index = median(a, 0, n) 
      
        # Median of first half 
        Q1 = a[median(a, 0, mid_index)] 
      
        # Median of second half 
        Q3 = a[median(a, mid_index + 1, n)] 
      
        # IQR calculation 
        return (Q3 - Q1)
    
    
    
    matches = []
    jpgNum = 1
    for jpg in jpg_list:
        response = textract.detect_document_text(
            Document={'S3Object': {'Bucket': jpgbucket, 'Name': jpg}})

        candidates = {}
        linearOffsets = {}
        candidate_pages = {}
        for templatename in [obj for obj in template_list if obj[-8:] == "ocr.json"]:
            
            if not os.path.isdir('/tmp/' + templatename.split('/')[0]):
                os.mkdir('/tmp/' + templatename.split('/')[0])
            s3.download_file(templatebucket, templatename, tmpdir + templatename)
            with open(tmpdir + templatename, "r") as templatefile:
                template = templatefile.read()
                template = json.loads(template)
                
                pageNum = 0
                for page in [p for p in template["Blocks"] if p["BlockType"] == "PAGE"]:
                    pageNum += 1
                    h_offsets = []
                    v_offsets = []
                    matched_word_count = 0
                    checked = {}
                    for line in [l for l in template["Blocks"] if l["BlockType"]=="LINE" and l["Id"] in page["Relationships"][0]["Ids"]]:
                        for child in [c for c in template["Blocks"] if c["BlockType"]=="WORD" and c["Id"] in line["Relationships"][0]["Ids"]]:
                            occurrence = next((word for word in response["Blocks"] if (word["BlockType"] == "WORD" and word["Text"] == child["Text"] and word["Id"] not in checked)), None)
                            if occurrence is not None:
                                matched_word_count += 1
                                h_offsets.append(occurrence["Geometry"]["BoundingBox"]["Left"] - child["Geometry"]["BoundingBox"]["Left"])
                                v_offsets.append(occurrence["Geometry"]["BoundingBox"]["Top"] - child["Geometry"]["BoundingBox"]["Top"])
                                
                                checked[occurrence["Id"]] = 1
                                #if abs(occurrence["Geometry"]["BoundingBox"]["Left"] - child["Geometry"]["BoundingBox"]["Left"]) > 0.2:
                                #    print(occurrence["Text"])
                                
                    hIQR = IQR(h_offsets, len(h_offsets))
                    vIQR = IQR(v_offsets, len(v_offsets))
                    match_pct = matched_word_count/len([x for x in template["Blocks"] if x["BlockType"] == "WORD"])
                    #print("Page #" + str(pageNum) + " stats:")
                    #print(hIQR)
                    #print(vIQR)
                    #print(match_pct)
                    #print("---")
                    if match_pct >= match_threshold:
                        candidates[templatename] = (hIQR + vIQR)/2
                        candidate_pages[templatename] = pageNum
                        linearOffsets[templatename] = {'x':mean(h_offsets), 'y':mean(v_offsets)}
                    
        if len(candidates) != 0:
            #print("Best candidate for JPG " + jpg + ": " + min(candidates, key=candidates.get))
            best_candidate = min(candidates, key=candidates.get)
            matches.append({'template':best_candidate[:-8] + "boxes.json", 'page':candidate_pages[best_candidate], 'offsets':linearOffsets[best_candidate]})
        else:
            print("No candidate found for JPG #" + str(jpgNum))
            matches.append(None)
            
        jpgNum += 1
    result = {
        'statusCode': 200,
        'documents': jpg_list,
        'matches': matches
    }
    print(result)
    return result
    
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