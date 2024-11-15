FROM python
WORKDIR /app
COPY . .
RUN pip install flask requests flask_cors pymongo configparser
ENV PYTHONUNBUFFERED=1
EXPOSE 5001
CMD ["python","file-service.py"]