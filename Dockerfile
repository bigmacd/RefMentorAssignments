FROM python:3.10-slim

EXPOSE 443

WORKDIR /app

COPY requirements.txt /app/
COPY *.py /app/
COPY root.crt /root/.postgresql/root.crt
COPY token.pickle /app/
COPY .streamlit /app/.streamlit

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

ARG _client_id
ENV _client_id $_client_id
ARG _client_secret
ENV _client_secret $_client_secret
ARG _default_scopes
ENV _default_scopes $_default_scopes
ARG _enable_reauth_refresh
ENV _enable_reauth_refresh $_enable_reauth_refresh
ARG _granted_scopes
ENV _granted_scopes $_granted_scopes
ARG _id_token
ENV _id_token $_id_token
ARG _quota_project_id
ENV _quota_project_id $_quota_project_id
ARG _rapt_token
ENV _rapt_token $_rapt_token
ARG _refresh_handler
ENV _refresh_handler $_refresh_handler
ARG _refresh_token
ENV _refresh_token $_refresh_token
ARG _scopes
ENV _scopes $_scopes
ARG _token_uri
ENV _token_uri $_token_uri
ARG expired=False
ENV expired $expired
ARG expiry
ENV expiry $expiry

ENTRYPOINT ["streamlit", "run", "ui.py", "--server.port=443", "--server.address=0.0.0.0"]

# docker run -p 443:443 --name refmentor refmentor:latest
