# Use an official Python runtime as a parent image
FROM python:3.11

# Match entrypoint DATA_PATH=/.versa so versa_paths loads pickles/CSVs from /.versa/workflows
ENV VERSA_DATA_ROOT=/.versa

# Set the working directory in the container
WORKDIR /app

# install graphviz
RUN apt-get update && apt-get install -y graphviz

# Copy the requirements file and install dependencies (canonical: requirements-agent.txt)
COPY ./src /app/src
COPY ./run.py /app/run.py
COPY ./requirements-agent.txt /app/requirements-agent.txt
RUN pip install --no-cache-dir -r requirements-agent.txt

# Default Streamlit secrets (no real keys). Production: VERSA_STREAMLIT_SECRETS_B64 or /.versa/secrets.toml.
RUN mkdir -p /app/.streamlit /.versa
COPY ./.versa/secrets.example.toml /app/.streamlit/secrets.toml

# make a directory for images
RUN mkdir /images

# COPY workflow required files
COPY ./.versa/workflows /app/workflows

# COPY Images
COPY ./images /app/images

# copy entrypoint script
COPY ./docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# copy run script
COPY ./docker/run_app.sh /app/run_app.sh
RUN chmod +x /app/run_app.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

EXPOSE 8501

# Your application's default command or entrypoint, if applicable
CMD ["/app/run_app.sh"]
