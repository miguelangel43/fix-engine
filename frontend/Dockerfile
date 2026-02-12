# Use a lightweight Python version
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first (to cache dependencies)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the frontend code
COPY . .

# Expose the port Dash runs on
EXPOSE 8050

# Command to run the app
CMD ["python", "main.py"]