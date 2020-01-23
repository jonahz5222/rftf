exports.handler = async (event) => {
    console.log("Handler running...");
    require('child_process').execSync(
      'cp /var/task/graphicsmagick/bin/gm /tmp/.; cp /var/task/lambda-ghostscript/bin/gs /tmp/.; chmod 755 /tmp/gm; chmod 755 /tmp/gs;',//cp -r /var/task/graphicsmagick /tmp/.; cp -r /var/task/lambda-ghostscript /tmp/.; chmod -R 777 /tmp/; chmod -R 777 /tmp/graphicsmagick/bin; chmod -R 777 /tmp/lambda-ghostscript/bin;',
      function (error, stdout, stderr) {
        if (error) {
          throw error;
        } else {
          console.log("System Initialized...");
        }
      }
    )
    
    
    const gm = require('gm').subClass({ appPath: "/tmp/" }); 
    //process.env['PATH'] = process.env['PATH'] + ':' + "/tmp/graphicsmagick/bin/";
    //process.env['PATH'] = process.env['PATH'] + ':' + "/tmp/lambda-ghostscript/bin";
    //process.env['PATH'] = process.env['PATH'] + ':' + process.env['LAMBDA_TASK_ROOT'];
    process.env.PATH = process.env.PATH + ':/tmp/';
    
    console.log("Task started...");
    var fs      = require('fs');
    var path    = require('path');
    var pdf2img = require('pdf2img');
    
    console.log("Getting AWS SDK...");
    var AWS = require('aws-sdk');

    console.log("Getting S3 reference...");
    // get reference to S3 client
    var s3 = new AWS.S3();
    
    const srcBucket = 'opif-textract-data';
    const srcKey = 'contract.pdf'
    const filepath = '/tmp/' + srcKey;
    
    var params = {   Bucket: srcBucket,   Key: srcKey };  
    
    console.log("Retrieving S3 file...");
    
    const result = await s3.getObject(params).promise();

    fs.writeFileSync(filepath, result.Body, function(err) {
      if (err) return err;
    });
    
    console.log("File written successfully.");
    
    pdf2img.setOptions({
      type: 'jpg',                                // png or jpg, default jpg
      density: 600,                               // default 600
      outputdir: '/tmp/out', // output folder, default null (if null given, then it will create folder name same as file name)
      page: 1
    });

    console.log("Converting to JPEG...");
    /*
    pdf2img.convert(filepath, function(err, info) {
      if (err) throw err;
      else{
          console.log("Conversion successful...");
          return info;
      }
    });*/
    
    function convertWrapper(path) {
        return new Promise((resolve, reject) => {
            pdf2img.convert(path,(errorResponse) => {
                reject(errorResponse)
            },
            (successResponse) => {
                resolve(successResponse);
            });
        });
    }
    
    const conversion = await convertWrapper(filepath);
    return conversion;
    /*
    conversion = await pdf2img.convert(filepath, function(err, info) {
      if (err) throw err;
      else{
          console.log("Conversion successful...");
          return info;
      }
    }).promise();*/
    
    
    /*
    async.waterfall([
        function(callback) {
            s3.getObject(
                {
                    Bucket: srcBucket,
                    Key: srcKey
                }
                , callback);
        },
        function(response) {
            pdf2img.setOptions({
              type: 'jpg',                                // png or jpg, default jpg
              density: 600,                               // default 600
              outputdir: 'tmp/out', // output folder, default null (if null given, then it will create folder name same as file name)
            });

            pdf2img.convert(input, function(err, info) {
              if (err) console.log(err)
              else console.log(info);
            });
            callback(null, 'three');
        },
        function(arg1, callback) {
            // arg1 now equals 'three'
            callback(null, 'done');
        }
    ], function (err, result) {
        // result now equals 'done'
    });
    */
}
