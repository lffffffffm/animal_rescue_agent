# 第一阶段：构建前端静态资源
FROM node:18-alpine AS build-stage

WORKDIR /app

# 复制依赖定义并安装
COPY package*.json ./
RUN npm install

# 复制源码并构建
COPY . .
RUN npm run build

# 第二阶段：使用 Nginx 托管静态文件
FROM nginx:stable-alpine AS production-stage

# 复制构建产物到 Nginx 目录
COPY --from=build-stage /app/dist /usr/share/nginx/html

# 复制 Nginx 配置（可选，用于处理 SPA 路由）
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

