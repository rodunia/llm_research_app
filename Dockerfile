# Use python 3.9 for better compatibility
FROM python:3.9-slim

# Set up a user (Hugging Face requires this to avoid permission errors)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy files
COPY --chown=user . $HOME/app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the app on port 7860
EXPOSE 7860

# IMPORTANT: Point to 'demo_progress.py' instead of 'app.py'
ENTRYPOINT ["streamlit", "run", "demo_progress.py", "--server.port=7860", "--server.address=0.0.0.0"]
