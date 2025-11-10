FROM python:3.10-slim

EXPOSE 443

WORKDIR /app

COPY requirements.txt /app/
COPY *.py /app/
COPY root.crt /root/.postgresql/root.crt
COPY token.pickle /app/
COPY .streamlit/ /app/.streamlit/

RUN pip3 install -r requirements.txt

ARG STORAGE_ACCOUNT_NAME
ENV STORAGE_ACCOUNT_NAME $STORAGE_ACCOUNT_NAME

ARG mslUsername
ENV mslUsername $mslUsername
ARG mslPassword
ENV mslPassword $mslPassword
ARG db_url
ENV db_url $db_url
ARG STREAMLIT_CLOUD
ENV STREAMLIT_CLOUD $STREAMLIT_CLOUD
ARG EMAIL_USER
ENV EMAIL_USER $EMAIL_USER
ARG EMAIL_TOKEN
ENV EMAIL_TOKEN $EMAIL_TOKEN


ENTRYPOINT ["streamlit", "run", "ui.py", "--server.port=443", "--server.address=0.0.0.0"]

# docker run -p 443:443 --name refmentor refmentor:latest
