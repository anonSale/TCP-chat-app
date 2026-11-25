FROM python:3.12-slim
WORKDIR /app
COPY server.py .
ENV CHAT_PORT=5000
EXPOSE 5000
CMD ["python", "-u", "server.py"]