FROM python:3.12-slim
ARG user=python
RUN set -ex && \
    apt-get -qq update && \
    apt-get -qq install --no-install-recommends -y \
    curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -ms /bin/bash $user 

USER $user
WORKDIR /home/$user
ENV PATH="/home/${user}/.local/bin:${PATH}"

# Longhorn configuration
ENV LONGHORN_URL="http://longhorn-frontend.longhorn-system.svc.cluster.local"
# Volume id or name to restore
ENV VOLUME_HANDLE=""
ENV NUMBER_OF_REPLICAS="2"
ENV LOG_LEVEL="INFO"

# Copy application files
COPY --chown=$user:$user requirements.txt .
COPY --chown=$user:$user backup-restore.py .

# Install Python dependencies
RUN set -ex && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python3", "backup-restore.py"]