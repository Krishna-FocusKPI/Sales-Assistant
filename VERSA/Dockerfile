# Use an official Python runtime as a parent image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# install graphviz
RUN apt-get update && apt-get install -y graphviz

# Copy the requirements file and install dependencies
COPY ./src /app/src
COPY ./run.py /app/run.py
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy a runnable config file in
RUN mkdir /app/.streamlit
COPY ./.versa/secrets.toml /app/.streamlit/secrets.toml

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
