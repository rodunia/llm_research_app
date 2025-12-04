FROM python:3.9-slim

# Force rebuild - products and prompts should be included
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files explicitly
COPY app.py .
COPY frontend/ ./frontend/
COPY products/ ./products/
COPY prompts/ ./prompts/
COPY runner/ ./runner/
COPY analysis/ ./analysis/
COPY .streamlit/ ./.streamlit/

# Expose port
EXPOSE 7860

# Set environment variables
ENV STREAMLIT_SERVER_PORT=7860
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true

# Run the app
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
