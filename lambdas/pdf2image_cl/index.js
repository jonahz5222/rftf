
const s3Util = require('./s3-util'),
	childProcessPromise = require('./child-process-promise'),
	path = require('path'),
	os = require('os'),
	EXTENSION = ".jpg",
	THUMB_WIDTH = 200,
	OUTPUT_BUCKET = "opif-textract-data",
	MIME_TYPE =  process.env.MIME_TYPE;

exports.handler = function (eventObject, context) {
	//const eventRecord = eventObject.Records && eventObject.Records[0],
	const =	inputBucket = "opif-textract-data",
            key = "contract.pdf",
            id = "test";//context.awsRequestId,
            resultKey = key.replace(/\.[^.]+$/, EXTENSION),
            workdir = os.tmpdir(),
            inputFile = path.join(workdir,  id + path.extname(key)),
            outputFile = path.join(workdir, 'converted-' + id + EXTENSION);


	console.log('converting', inputBucket, key, 'using', inputFile);
	return s3Util.downloadFileFromS3(inputBucket, key, inputFile)
		.then(() => childProcessPromise.spawn(
			'/opt/bin/convert',
			[inputFile, '-resize', `${THUMB_WIDTH}x`, outputFile],
			{env: process.env, cwd: workdir}
		))
		.then(() => s3Util.uploadFileToS3(OUTPUT_BUCKET, resultKey, outputFile, MIME_TYPE));
};
