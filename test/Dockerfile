FROM python:3.12-slim

WORKDIR /app

COPY requirements-test.txt /app/test/requirements-test.txt
RUN pip install --no-cache-dir -r /app/test/requirements-test.txt

COPY . /app/test/

CMD ["python", "-m", "pytest", "/app/test/test_system_scenarios.py", "-v", "--tb=short"]
