package pdf2image;

import com.amazonaws.services.lambda.runtime.Context; 
import com.amazonaws.services.lambda.runtime.LambdaLogger;
import java.io.File;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.IOException;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.FileFilter;
import java.io.FileInputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;


import org.apache.pdfbox.tools.PDFToImage;

import com.amazonaws.AmazonServiceException;
import com.amazonaws.SdkClientException;
import com.amazonaws.auth.profile.ProfileCredentialsProvider;
import com.amazonaws.regions.Regions;
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3ClientBuilder;
import com.amazonaws.services.s3.model.GetObjectRequest;
import com.amazonaws.services.s3.model.ResponseHeaderOverrides;
import com.amazonaws.services.s3.model.S3Object;
import com.amazonaws.services.s3.model.S3ObjectInputStream;
import com.amazonaws.services.s3.model.PutObjectRequest;
import com.amazonaws.services.s3.event.S3EventNotification;
import com.amazonaws.services.lambda.AWSLambda;
import com.amazonaws.services.lambda.AWSLambdaClientBuilder;
import com.amazonaws.services.lambda.model.InvokeRequest;
import com.amazonaws.services.lambda.model.InvokeResult;
import com.amazonaws.auth.DefaultAWSCredentialsProviderChain;

import org.json.JSONObject;
/*
import org.apache.pdfbox.pdmodel.*;
import org.apache.pdfbox.rendering.*;
import java.awt.image.*;
import java.io.*;
import javax.imageio.*;
*/

public class PdfToImage{

    private static String getFileChecksum(MessageDigest digest, File file) throws IOException
    {
        //Get file input stream for reading the file content
        FileInputStream fis = new FileInputStream(file);
         
        //Create byte array to read data in chunks
        byte[] byteArray = new byte[1024];
        int bytesCount = 0; 
          
        //Read file data and update in message digest
        while ((bytesCount = fis.read(byteArray)) != -1) {
            digest.update(byteArray, 0, bytesCount);
        };
         
        //close the stream; We don't need it now.
        fis.close();
         
        //Get the hash's bytes
        byte[] bytes = digest.digest();
         
        //This bytes[] has bytes in decimal format;
        //Convert it to hexadecimal format
        StringBuilder sb = new StringBuilder();
        for(int i=0; i< bytes.length ;i++)
        {
            sb.append(Integer.toString((bytes[i] & 0xff) + 0x100, 16).substring(1));
        }
         
        //return complete hash
       return sb.toString();
    }
    
    
    public JSONObject myHandler(S3EventNotification event, Context context) {
        final AmazonS3 s3 = AmazonS3ClientBuilder.standard().withRegion(Regions.US_EAST_2).build();
        String bucket_name = event.getRecords().get(0).getS3().getBucket().getName();
        String key_name_base = event.getRecords().get(0).getS3().getObject().getKey();
        String key_name = key_name_base.substring(4,key_name_base.length());
        
        JSONObject output = new JSONObject();
        
        try {      
            S3Object o = s3.getObject(bucket_name, key_name_base);
            S3ObjectInputStream s3is = o.getObjectContent();
            FileOutputStream fos = new FileOutputStream(new File("/tmp/" + key_name));
            byte[] read_buf = new byte[1024];
            int read_len = 0;
            while ((read_len = s3is.read(read_buf)) > 0) {
                fos.write(read_buf, 0, read_len);
            }
            s3is.close();
            fos.close();
        } catch (AmazonServiceException e) {
            System.err.println(e.getErrorMessage());
            System.exit(1);
        } catch (FileNotFoundException e) {
            System.err.println(e.getMessage());
            System.exit(1);
        } catch (IOException e) {
            System.err.println(e.getMessage());
            System.exit(1);
        }
        
        try {
            String[] args = {"/tmp/" + key_name};
            PDFToImage.main(args);
        } catch (IOException e) {
            System.err.println(e.getMessage());
            System.exit(1);
        }
        try {
            File dir = new File("/tmp"); 
            FileFilter fileFilter 
                = new FileFilter() {
                  //Override accept method
                  public boolean accept(File file) {
                     //if the file extension is .jpg return true, else false
                     if (file.getName().endsWith(".jpg")) {
                        return true;
                     }
                     return false;
                  }
               }; 
            // For taking both .JPG and .jpg files (useful in *nix env) 
            MessageDigest md5Digest = null;
            try{
                md5Digest = MessageDigest.getInstance("MD5");
            } catch (NoSuchAlgorithmException e)
            {
                System.err.println(e.getMessage());
                System.exit(1);
            }
            File[] fileList = dir.listFiles(fileFilter); 
            String baseName = key_name.split("\\.")[0];//getFileChecksum(md5Digest, fileList[i]);
            for (int i = 0; i < fileList.length; i++) {
                if (fileList[i].isFile()) {
                  
                    output.put("document",baseName);
                    PutObjectRequest request = new PutObjectRequest(bucket_name, "jpg/" + baseName + "/" + Integer.toString(i+1) + ".jpg", new File("/tmp/" + fileList[i].getName()));
                    s3.putObject(request);
                    
                } 
            }
            
        } catch (AmazonServiceException e) {
            e.printStackTrace();
            System.exit(1);
        } catch (SdkClientException e) {
            e.printStackTrace();
            System.exit(1);
        }
        
        /*
        String base_name = key_name.split("\\.")[0];
        String func_arn = "arn:aws:lambda:us-east-2:891440894509:function:parse_with_template";
        InvokeRequest invokeRequest = new InvokeRequest()
                .withFunctionName(func_arn)
                .withPayload("{\"bucket\":\"" + jpg_bucket_name + "\",\"document\":\"" + base_name + "\"}");
        InvokeResult invokeResult = null;

        try {
            AWSLambda awsLambda = AWSLambdaClientBuilder.standard()
                    .withCredentials(DefaultAWSCredentialsProviderChain.getInstance())
                    .withRegion(Regions.US_EAST_2).build();

            invokeResult = awsLambda.invoke(invokeRequest);

            String ans = new String(invokeResult.getPayload().array(), StandardCharsets.UTF_8);

            //write out the return value
            System.out.println(ans);

        } catch (AmazonServiceException e) {
            System.out.println(e);
        }

        System.out.println(invokeResult.getStatusCode());
        */
        System.out.println(output);
        return output;
        /*LambdaLogger logger = context.getLogger();
        logger.log("received : " + myCount);
        return String.valueOf(myCount);*/
    }
}