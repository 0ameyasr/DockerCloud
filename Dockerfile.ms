FROM python
WORKDIR /app
COPY templates /app/templates
COPY data_handler.py data_handler.py
COPY secrets.cfg secrets.cfg
RUN pip install flask requests flask_cors pymongo configparser
ENV PYTHONUNBUFFERED=1
EXPOSE 5002
CMD ["python","message-service.py"]