call gradle build
cd build/distributions
call aws lambda update-function-code --function-name arn:aws:lambda:us-east-2:796077402566:function:og-pdf-to-jpg-conversion --zip-file fileb://pdf2image_java.zip
cd ../..
rem call aws lambda invoke --function-name arn:aws:lambda:us-east-2:891440894509:function:pdf2image_java --payload "{ \"key\": \"value\" }" response.json
rem echo Lambda result:
rem cat response.json