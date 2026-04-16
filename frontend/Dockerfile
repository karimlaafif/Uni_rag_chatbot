# ── Stage 1 : Build ─────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copie des fichiers de dépendances d'abord (cache Docker)
COPY package.json ./
RUN npm install

# Copie du code source
COPY . .

# Variable d'environnement pour le proxy (pas nécessaire en prod avec nginx)
# VITE_API_BASE_URL est vide → le frontend utilisera /api (proxifié par nginx)
ENV VITE_API_BASE_URL=""

RUN npm run build

# ── Stage 2 : Production (nginx) ─────────────────────────────────────────────
FROM nginx:alpine

# Supprime la config nginx par défaut
RUN rm /etc/nginx/conf.d/default.conf

# Copie notre config nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copie les fichiers buildés
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
