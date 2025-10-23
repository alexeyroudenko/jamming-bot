# pull official base image
FROM node:22-alpine

# set working directory
WORKDIR /app

# add `/app/node_modules/.bin` to $PATH
ENV PATH /app/node_modules/.bin:$PATH

# install app dependencies
COPY package.json ./
# COPY package-lock.json ./
RUN yarn
# RUN npm install --silent
# RUN npm install react-scripts@3.4.1 -g --silent
# RUN npm install react-d3-graph -g --silent

# add app
COPY . ./

# start app
CMD ["yarn", "start"]