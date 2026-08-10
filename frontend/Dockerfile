FROM node:20-alpine AS build

ARG NPM_REGISTRY=https://registry.npmmirror.com
ARG BASE_PATH=/
ENV npm_config_registry=${NPM_REGISTRY}
ENV npm_registry=${NPM_REGISTRY}
ENV PNPM_HOME=/pnpm
ENV PATH=${PNPM_HOME}:${PATH}
ENV BASE_PATH=${BASE_PATH}

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN corepack enable \
    && corepack prepare pnpm@9.15.9 --activate \
    && pnpm install --no-frozen-lockfile --prefer-offline

COPY . /app
RUN rm -f pnpm-workspace.yaml \
    && pnpm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
