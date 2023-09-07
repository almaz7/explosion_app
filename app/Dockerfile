FROM python:3.10
WORKDIR /code
COPY requirements.txt .
RUN pip install -r requirements.txt
ENV TZ Europe/Moscow
COPY . .
CMD ["python", "main.py"]
