FROM python:3.12-slim
WORKDIR /app
COPY notifier.py .
ENV PORT=8080
EXPOSE 8080
USER nobody
CMD ["python", "notifier.py"]
