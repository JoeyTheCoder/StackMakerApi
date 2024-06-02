# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . .

# Install any needed dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 85 available to the world outside this container
EXPOSE 85

# Define environment variable
ENV NAME World

# Run main.py when the container launches

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "85"]

