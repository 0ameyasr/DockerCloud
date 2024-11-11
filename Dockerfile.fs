FROM python
WORKDIR /app
COPY templates /app/templates
COPY file-service.py file-service.py
COPY cloud-secrets.cfg cloud-secrets.cfg
RUN pip install flask requests flask_cors pymongo configparser
ENV PYTHONUNBUFFERED=1
EXPOSE 5001
CMD ["python","file-service.py"]