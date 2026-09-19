# Stage 1: crawl the SPA and produce a static mirror into /var/www/html.
FROM python:3.12-alpine AS crawler

RUN apk add --no-cache ca-certificates

WORKDIR /app
COPY ./crawl.py /app/crawl.py

ENV CRAWL_URL=https://footrue.com \
    OUTPUT_DIR=/var/www/html \
    CONCURRENCY=8 \
    HTTP_TIMEOUT=30

RUN python /app/crawl.py

# Stage 2: serve the mirror with Caddy.
FROM caddy:latest

COPY --from=crawler /var/www/html /var/www/html

EXPOSE 80

CMD ["caddy", "file-server", "--root", "/var/www/html"]
