FROM node:18
WORKDIR /app
COPY ../../adapter/package.json ./
# COPY adapter/adapter.js ./
RUN yarn
#COPY adapter/. .
EXPOSE 4000
EXPOSE 5001

CMD ["yarn", "start"]