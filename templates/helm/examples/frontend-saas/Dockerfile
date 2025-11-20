# Build stage
FROM chek-images-cn-beijing.cr.volces.com/devops/library/node:20-alpine AS builder
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --no-frozen-lockfile
COPY . .
RUN pnpm build

# Runtime stage (serve static build via nginx)
FROM chek-images-cn-beijing.cr.volces.com/devops/library/nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx","-g","daemon off;"]
