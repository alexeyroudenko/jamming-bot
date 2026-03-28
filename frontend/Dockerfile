# pull official base image
# Node 23 is excluded by some transitive deps (e.g. expect@30); use 22 LTS
FROM node:22-alpine

# set working directory
WORKDIR /app

# add `/app/node_modules/.bin` to $PATH
ENV PATH /app/node_modules/.bin:$PATH

# install app dependencies (yarn.lock keeps install aligned with the repo)
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile
# RUN npm install --silent
# RUN npm install react-scripts@3.4.1 -g --silent
# RUN npm install react-d3-graph -g --silent

# add app
COPY . ./

# start app
CMD ["yarn", "start"]