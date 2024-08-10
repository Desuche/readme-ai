# Use a base image with Python 3.10 installed (multi-platform)
FROM --platform=${BUILDPLATFORM} python:3.10-slim-buster

# Set working directory
WORKDIR /app

COPY requirements.txt requirements.txt

# Install pip requirements
RUN pip install -r requirements.txt

# Set environment variable for Git Python
ENV GIT_PYTHON_REFRESH=quiet

# Install system dependencies and clean up apt cache
RUN apt-get update && apt-get install -y git \
    && rm -rf /var/lib/apt/lists/*


# Create a non-root user with a specific UID and GID (i.e. 1000 in this case)
RUN groupadd -r tempuser -g 1000 && \
    useradd -r -u 1000 -g tempuser tempuser && \
    mkdir -p /home/tempuser && \
    chown -R tempuser:tempuser /home/tempuser

# Set permissions for the working directory to the new user
RUN chown tempuser:tempuser /app

# Switch to the new user
USER tempuser

# Add the directory where pip installs user scripts to the PATH
ENV PATH=/home/tempuser/.local/bin:$PATH

COPY . .

# Set the command to run the CLI
ENTRYPOINT ["python3"] 
CMD ["-m", "readmeai.cli.main", "-r", "https://github.com/eli64s/readme-ai"]
