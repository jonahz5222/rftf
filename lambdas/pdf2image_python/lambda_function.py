from pdf2image import convert_from_path, convert_from_bytes
from pdf2image.exceptions import (
    PDFInfoNotInstalledError,
    PDFPageCountError,
    PDFSyntaxError
)
import boto3

s3_client = boto3.client('s3')

def lambda_handler(event, context):

    bucket = 'opif-textract-data'
    key = 'contract.pdf'
    tmp = '/tmp/'

    s3_client.download_file(bucket, key, tmp)
    
    in_file = tmp + key

    images = convert_from_path(in_file)
        
    images[0].save(tmp + key, "JPEG")
    return images[0]