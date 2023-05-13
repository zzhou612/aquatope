ARG RUNTIME_IMAGE
FROM ${RUNTIME_IMAGE}

COPY requirements.txt requirements.txt

RUN  apt-get update \
    # Upgrade installed packages to get latest security fixes if the base image does not contain them already.
    && apt-get upgrade -y --no-install-recommends \
    # cleanup package lists, they are not used anymore in this image
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
    # install additional python modules
    && pip install --no-cache-dir -r requirements.txt \
    # Show actual python version in the build output.
    && echo "Actual python version is:" \
    && python --version \
    # Show actual /bin/proxy version in the build output, makes it easier to check if go security fixes need to be applied.
    && echo "Actual /bin/proxy version is:" \
    && /bin/proxy -version

# Download transformers models
COPY caching_models.py /faas/caching_models.py
RUN python /faas/caching_models.py

# Configure transformers to run in offline mode
ENV HF_DATASETS_OFFLINE=1
ENV TRANSFORMERS_OFFLINE=1

# Download the minimum corpora for textblob
RUN python -m textblob.download_corpora

# Run OpenWhisk actionLoop proxy
CMD ["/bin/proxy"]
