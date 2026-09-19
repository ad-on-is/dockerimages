FROM caddy:builder AS builder

RUN xcaddy build \
    --with github.com/caddy-dns/cloudflare \
    --with github.com/WeidiDeng/caddy-cloudflare-ip \
    --with github.com/caddyserver/replace-response \
    --with github.com/caddy-dns/rfc2136 \
    --with github.com/caddy-dns/rfc2136 \
    --with github.com/ad-on-is/caddy-dns-technitium@main \
    --with github.com/abiosoft/caddy-exec \
    --with github.com/mholt/caddy-l4@master

FROM caddy:latest

RUN apk add curl ca-certificates

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
