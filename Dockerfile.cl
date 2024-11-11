FROM python
WORKDIR /app
COPY templates /app/templates
COPY cloud.py cloud.py
COPY cloud-secrets.cfg cloud-secrets.cfg
RUN pip install flask requests flask_cors pymongo configparser
ENV PYTHONUNBUFFERED=1
EXPOSE 5000
CMD ["python","cloud.py"]