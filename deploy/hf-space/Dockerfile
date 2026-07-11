# Bastion Console — Hugging Face Spaces showcase instance
# Runs the REAL router/classifier/metrics/audit code with a simulated engine
# (BASTION_DEMO=1) so judges always have a live URL. Honest ribbon in the UI.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY router/ router/
COPY dashboard/ dashboard/

ENV BASTION_DEMO=1
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "uvicorn router.main:app --host 0.0.0.0 --port ${PORT}"]
