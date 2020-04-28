import json
import boto3
import os
from collections import defaultdict
import pprint
from statistics import stdev, mean

def lambda_handler(event, context):
    #IDENTIFY TEMPLATE

    """
    This lambda identifies the correct form/template to use on the given document.
    It does this by calculating the linear offsets between identical words on both the given form and on a template.
    If the interquartile range of those offsets is close to 0, we can be reasonably confident that it is the correct template to use.
    """
    
    # state variables
    jpgbucket = os.environ['JPG_BUCKET']
    jpgfolder = os.environ['JPG_FOLDER']
    templatebucket = os.environ['TEMPLATE_BUCKET']
    document = None
    jpg_list = None
    template_list = None
    
    s3 = boto3.client('s3')
    
    # check if this identification request is coming from an added PDF or an added template
    if "retry" in event:
        # if triggered by an added template, get information from og-retry-template
        jpg_list = event['jpgs']
        template_list = event['templates']
        print(event['templates'])
    else:
        # if triggered from an added PDF, get JPG file list and list of all template files
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
    
    page = 0
    
    match_threshold = 0.8

    tmpdir = '/tmp/'
    textract = boto3.client('textract')
    
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
    
    # loop through each JPG to be parsed
    for jpg in jpg_list:
    
        # get Textract results on current JPG page
        response = textract.detect_document_text(
            Document={'S3Object': {'Bucket': jpgbucket, 'Name': jpg}})

        candidates = {}
        linearOffsets = {}
        candidate_pages = {}
        
        # for each template to be tested
        for templatename in [obj for obj in template_list if obj[-8:] == "ocr.json"]:
            
            # create a temporary directory and download the template file to it
            if not os.path.isdir('/tmp/' + templatename.split('/')[0]):
                os.mkdir('/tmp/' + templatename.split('/')[0])
            s3.download_file(templatebucket, templatename, tmpdir + templatename)
            
            
            with open(tmpdir + templatename, "r") as templatefile:
                template = templatefile.read()
                template = json.loads(template)
                
                pageNum = 0
                
                # for each page in a template, determine how similar a page is to the current JPG
                for page in [p for p in template["Blocks"] if p["BlockType"] == "PAGE"]:
                    pageNum += 1
                    h_offsets = []
                    v_offsets = []
                    matched_word_count = 0
                    page_word_count = 0
                    checked = {}
                    
                    # for each matched word pairing, calculated offset between the positions of the words on the JPG and template page
                    for line in [l for l in template["Blocks"] if l["BlockType"]=="LINE" and l["Id"] in page["Relationships"][0]["Ids"]]:
                        for child in [c for c in template["Blocks"] if c["BlockType"]=="WORD" and c["Id"] in line["Relationships"][0]["Ids"]]:
                            page_word_count += 1
                            occurrence = next((word for word in response["Blocks"] if (word["BlockType"] == "WORD" and word["Text"] == child["Text"] and word["Id"] not in checked)), None)
                            if occurrence is not None:
                                matched_word_count += 1
                                h_offsets.append(occurrence["Geometry"]["BoundingBox"]["Left"] - child["Geometry"]["BoundingBox"]["Left"])
                                v_offsets.append(occurrence["Geometry"]["BoundingBox"]["Top"] - child["Geometry"]["BoundingBox"]["Top"])
                                
                                checked[occurrence["Id"]] = 1
                                
                                
                    # calculate interquartile range horizontally and vertically
                    hIQR = IQR(h_offsets, len(h_offsets))
                    vIQR = IQR(v_offsets, len(v_offsets))
                    
                    # calculate how much of the template page matches word-for-word with the JPG
                    match_pct = matched_word_count/page_word_count
                    #print("Template Page #" + str(pageNum) + " stats:")
                    #print(hIQR)
                    #print(vIQR)
                    #print(match_pct)
                    #print("---")
                    
                    # if the page has enough matched words, mark it as a candidate
                    if match_pct >= match_threshold:
                        candidates[templatename] = (hIQR + vIQR)/2
                        candidate_pages[templatename] = pageNum
                        linearOffsets[templatename] = {'x':mean(h_offsets), 'y':mean(v_offsets)}
                    
        # determine the best candidate page out of the available candidates to parse the JPG with
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
    
    # send results of this lambda to og-parse-with-template
    pylambda = boto3.client('lambda')
    pylambda.invoke(FunctionName="og-parse-with-template",InvocationType="Event",Payload=json.dumps(result))
    
    return {}
    
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