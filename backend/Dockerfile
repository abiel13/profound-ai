FROM python:3.11

WORKDIR /

COPY requirements.txt .

RUN pip install -r requirements.txt && pip list

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]