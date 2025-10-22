FROM python:3.13.3-slim

ARG UID=10001
ARG GID=10001

# Create group and user in a single RUN command to reduce layers
RUN groupadd -g ${GID} app && \
    useradd -m -u ${UID} -g ${GID} -s /usr/sbin/nologin app && \
    mkdir /app && chown -R app:app /app

# Switch to the non-root user
USER app

# Clone the URLClassifier exceptions manager
WORKDIR /app

# Copy requirements and install dependencies
COPY --chown=app:app requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY --chown=app:app . .

# Install the package for the app user only (no root needed)
RUN python -m pip install --no-cache-dir . --upgrade --user

# Add user's local bin to PATH
ENV PATH="/home/app/.local/bin:$PATH"

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Set the entrypoint to use our startup script
ENTRYPOINT ["/app/entrypoint.sh"]
