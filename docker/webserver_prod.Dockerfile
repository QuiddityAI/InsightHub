FROM --platform=$BUILDPLATFORM node:19.9.0 AS vite_env
RUN useradd -ms /bin/bash appuser
WORKDIR /app
COPY package.json /app
COPY package-lock.json /app
RUN npm install

FROM vite_env as webserver_prod

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:55140 || exit 1

EXPOSE 55140
WORKDIR /source_code/frontend
USER node
ENTRYPOINT ["sh", "-c"]
CMD ["npx vite build && npx vite preview --port 55140"]
