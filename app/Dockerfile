FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt  && groupadd -r posuser && useradd -r -g posuser -d /app posuser  && mkdir -p /var/log/pos && chown -R posuser:posuser /app /var/log/pos
COPY --chown=posuser:posuser . .
USER posuser
EXPOSE 5000
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5000", "--access-logfile", "/var/log/pos/access.log", "--error-logfile", "/var/log/pos/error.log", "app:app"]
