# app/Dockerfile

FROM python:3.10-slim

EXPOSE 443

WORKDIR /app

COPY requirements.txt /app/
COPY *.py /app/
COPY referees.db /app/
COPY databaseroot.crt ~/.postgresql/root.crt

RUN pip3 install -r requirements.txt

ENTRYPOINT ["streamlit", "run", "ui.py", "--server.port=443", "--server.address=0.0.0.0"]

# docker build . -t refmentor --build-arg mslusername=<username> --build-arg mslpassword=<password>
# docker tag refmentor:latest refmentor.azurecr.io/refmentor:latest
# docker push refmentor.azurecr.io/refmentor:latest
# docker run -p 443:443 --name refmentor refmentor:latest
