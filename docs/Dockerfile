FROM node:20-slim
WORKDIR /app

RUN npm install -g pnpm


COPY package*.json pnpm-lock.yaml ./

RUN pnpm install

COPY . .

EXPOSE 8080

CMD ["npx", "vuepress", "dev", "docs"]
