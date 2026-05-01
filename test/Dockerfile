FROM python:3.12-slim
WORKDIR /app
COPY . /app/test/
RUN pip install --no-cache-dir -r /app/test/requirements-test.txt
CMD ["pytest", "/app/test/test_system_scenarios.py", "-v", "--tb=short"]
