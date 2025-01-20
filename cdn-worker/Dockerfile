FROM node:20-slim
WORKDIR /app

RUN npm install -g pnpm wrangler

COPY package*.json pnpm-lock.yaml ./

RUN pnpm install

COPY . .

EXPOSE 8787

CMD ["wrangler", "dev"]
