FROM node:20-slim AS builder

WORKDIR /app

ARG PUBLIC_BACKEND_URL=http://localhost:5998
ENV PUBLIC_BACKEND_URL=$PUBLIC_BACKEND_URL

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

FROM node:20-slim

WORKDIR /app
COPY --from=builder /app/build ./build
COPY --from=builder /app/node_modules ./node_modules
COPY package.json .

EXPOSE 5999
ENV PORT=5999
CMD ["node", "build"]
