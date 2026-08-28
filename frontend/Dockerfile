FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# node:20-alpine already ships a "node" user at uid/gid 1000, matching the
# host dev user, so the bind-mounted source stays writable without a root
# process.
RUN chown -R node:node /app
USER node

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
