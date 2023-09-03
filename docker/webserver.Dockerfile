FROM --platform=$BUILDPLATFORM node:19.9.0 AS vite_env
RUN useradd -ms /bin/bash appuser
WORKDIR /app
COPY package.json /app
COPY package-lock.json /app
RUN npm install

FROM vite_env as webserver
EXPOSE 55140
WORKDIR /source_code/frontend
USER node
ENTRYPOINT ["npx", "vite"]
CMD []
