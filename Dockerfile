FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HTTP_PORT=8096
ENV MCP_HTTP_PATH=/mcp/latam
EXPOSE 8096
CMD ["python3", "server.py"]
