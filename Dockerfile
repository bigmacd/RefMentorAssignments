# app/Dockerfile

FROM python:3.10-slim

EXPOSE 443

WORKDIR /app

COPY requirements.txt /app/
COPY *.py /app/
COPY root.crt /root/.postgresql/root.crt

RUN pip3 install -r requirements.txt

ARG STORAGE_ACCOUNT_NAME
ENV STORAGE_ACCOUNT_NAME $STORAGE_ACCOUNT_NAME

ARG mslusername=mcooley
ENV mslUsername $mslusername
ARG mslpassword=mslSW@
ENV mslPassword $mslpassword
ARG db_url
ENV db_url $db_url
ARG badmentor1
ENV badmentor1 $badmentor1
ARG badmentor2
ENV badmentor2 $badmentor2
ARG badmentor3
ENV badmentor3 $badmentor3
ARG STREAMLIT_CLOUD=False
ENV STREAMLIT_CLOUD $STREAMLIT_CLOUD

ENTRYPOINT ["streamlit", "run", "ui.py", "--server.port=443", "--server.address=0.0.0.0"]


# docker run -p 443:443 --name refmentor refmentor:latest
