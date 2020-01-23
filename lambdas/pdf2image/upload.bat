rm function.zip
7z a -r function.zip .
aws lambda update-function-code --function-name arn:aws:lambda:us-east-2:891440894509:function:pdf2jpg_node --zip-file fileb://function.zip