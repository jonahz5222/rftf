rm function.zip
7z a -r function.zip .
aws lambda update-function-code --function-name arn:aws:lambda:us-east-2:796077402566:function:og-identify-template --zip-file fileb://function.zip