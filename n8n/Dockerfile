## Add your dockerfile here
FROM docker.n8n.io/n8nio/n8n
USER root
WORKDIR /tmp/selenium
RUN corepack enable pnpm
RUN pnpm i selenium-webdriver
RUN mv ./node_modules/.pnpm/selenium* /usr/local/lib/node_modules/n8n/node_modules/.pnpm/
RUN mv ./node_modules/selenium* /usr/local/lib/node_modules/n8n/node_modules/

USER node
ENTRYPOINT ["tini", "--", "/docker-entrypoint.sh"]
