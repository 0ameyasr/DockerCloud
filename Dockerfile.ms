FROM python
WORKDIR /app
COPY . .
RUN pip install flask requests flask_cors pymongo configparser
ENV PYTHONUNBUFFERED=1
EXPOSE 5002
CMD ["python","message-service.py"]