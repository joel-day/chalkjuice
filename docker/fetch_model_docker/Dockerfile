# FROM downloads the specified image template from Docker Hub; 
# templates can be downloaded ahead of time as well.
# Use the official AWS Lambda Python 3.12 image
FROM public.ecr.aws/lambda/python:3.12

# Copy your app.py file into the container
COPY app.py ${LAMBDA_TASK_ROOT}
# If you have dependencies, copy requirements.txt and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Command for AWS Lambda to execute the function.
# This particular image will be used with AWS lambda and AWS Eventbridge, 
# so the CMD is set to run a definition titled 'lambda_handler' 
# within my python script.
CMD ["app.lambda_handler"]