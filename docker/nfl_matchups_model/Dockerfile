
# --- Stage 2: Copy into Lambda image ---
FROM public.ecr.aws/lambda/python:3.12

# Copy app code
COPY app/ .

# If you have dependencies, copy requirements.txt and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Lambda entrypoint
CMD ["nfl_matchups_model.lambda_handler"]
