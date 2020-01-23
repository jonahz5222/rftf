rm function.zip
7z a -r function.zip package/.
7z u function.zip lambda_function.py
aws lambda update-function-code --function-name arn:aws:lambda:us-east-2:891440894509:function:pdf2jpg --zip-file fileb://function.zip