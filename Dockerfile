FROM python:3.7-slim-buster
WORKDIR /project
ADD src /project
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
CMD ["python","web_service.py"]