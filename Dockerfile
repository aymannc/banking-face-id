FROM python:3.7
ENV PIP_NO_CACHE_DIR=1
WORKDIR /project
ADD . /project
RUN apt-get update
RUN apt-get install default-libmysqlclient-dev -y
RUN apt-get install ffmpeg libsm6 libxext6 -y
RUN pip install --upgrade pip && pip install -r requirements.txt
CMD ["python","web_service.py"]