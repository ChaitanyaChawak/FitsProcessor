FROM python:3.13-slim

LABEL Description="FitsProcessor"

SHELL ["/bin/bash", "-c"]
WORKDIR /workdir

RUN apt-get update && \
    apt-get install -y python3-dev && \
    apt-get clean

RUN python3 -m venv .venv

RUN cd /workdir && \
    source .venv/bin/activate && \
    pip install --upgrade pip

COPY . /workdir

RUN source .venv/bin/activate && \
    pip install .

CMD ["/bin/bash"]
