FROM --platform=$BUILDPLATFORM node:22.13.0 AS vite_env

RUN useradd -ms /bin/bash appuser
WORKDIR /app
RUN chown -R appuser /app

# install dependencies:
COPY --chown=appuser package.json package-lock.json /app/
USER appuser
RUN npm install

# copy rest of source code:
COPY --chown=appuser . /app/
RUN npx vite build

FROM vite_env as webserver_prod

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:55140 || exit 1

EXPOSE 55140
USER appuser
ENTRYPOINT ["npx"]
CMD ["vite", "preview", "--port", "55140"]
