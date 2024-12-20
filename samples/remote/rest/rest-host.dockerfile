# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

RUN mkdir -p /app/libs
COPY requirements.txt /app
COPY vanilla_aiagents-0.7.0-py3-none-any.whl /app/libs/

# Install any needed packages specified in requirements.txt
RUN pip install /app/libs/vanilla_aiagents-0.7.0-py3-none-any.whl
RUN pip install --no-cache-dir -r requirements.txt


# Copy the current directory contents into the container at /app
COPY . /app

# Expose the port the app runs on
EXPOSE 8000

# Define environment variables
ENV PYTHONUNBUFFERED=1
ENV HOST 0.0.0.0
ENV PORT 8000

# Run the application
CMD ["python", "rest_host.py"]