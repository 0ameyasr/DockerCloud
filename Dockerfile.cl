FROM python
WORKDIR /app
COPY . .
RUN pip install flask requests flask_cors pymongo configparser
ENV PYTHONUNBUFFERED=1
EXPOSE 5050
CMD ["python","cloud.py"]