FROM python:slim

# Copy the repository source code in
COPY . /src

# Install python dependencies
RUN pip install -e /src

# Run mscbot
# We use CMD here instead of ENTRYPOINT, as it allows you to exec in easily
CMD ["/usr/local/bin/python3", "-m", "mscbot", "-c", "/config/config.yaml"]
