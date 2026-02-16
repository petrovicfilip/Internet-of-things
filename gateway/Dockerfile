# -------- build stage
FROM node:20-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# -------- runtime stage
FROM node:20-alpine
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

COPY --from=build /app/package*.json ./
RUN npm ci --omit=dev

COPY --from=build /app/dist ./dist
# ako koristiš gateway/proto + process.cwd()
COPY --from=build /app/proto ./proto

EXPOSE 3000
CMD ["node", "dist/main.js"]