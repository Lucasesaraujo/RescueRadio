FROM node:22-alpine AS build

WORKDIR /app

COPY apps/web/package*.json ./

RUN npm install

COPY apps/web .

RUN npm run build


FROM nginx:alpine

COPY --from=build /app/dist/web/browser /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]