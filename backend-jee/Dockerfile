# ══════════════════════════════════════════════════════════════════════════
#  Dockerfile — Backend JEE (Quarkus)
#
#  Build en 2 étapes (multi-stage) :
#    Stage 1 : Maven compile le projet → génère le .jar
#    Stage 2 : JRE minimal exécute le .jar
#
#  Résultat : image ~250MB (vs ~700MB pour WildFly).
#  Démarrage : ~0.5 secondes (vs 30s pour WildFly).
# ══════════════════════════════════════════════════════════════════════════

# ── Stage 1 : Compilation Maven ───────────────────────────────────────────
FROM maven:3.9.6-eclipse-temurin-17 AS builder

WORKDIR /build

# Copie du pom.xml d'abord pour exploiter le cache Docker.
# Si tu ne modifies que le code Java (pas les dépendances),
# Maven ne re-télécharge pas les jars → build beaucoup plus rapide.
COPY pom.xml .
RUN mvn dependency:go-offline -q

# Copie du code source
COPY src ./src

# Build Quarkus (mode JVM — pas de compilation native GraalVM pour simplifier)
# -DskipTests → on ne relance pas les tests dans Docker (fait en CI)
RUN mvn package -DskipTests -q

# ── Stage 2 : Image d'exécution ───────────────────────────────────────────
FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

# Quarkus produit un "fast-jar" : un dossier quarkus-app/ avec des
# fichiers séparés (meilleur caching Docker que le fat-jar Spring Boot)
COPY --from=builder /build/target/quarkus-app/ ./

# Port HTTP de Quarkus
EXPOSE 8080

# Healthcheck Docker (utilise l'endpoint /q/health fourni par SmallRye Health)
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
  CMD wget -q --spider http://localhost:8080/q/health/ready || exit 1

# Lancement de Quarkus
# quarkus-run.jar est le point d'entrée du fast-jar
ENTRYPOINT ["java", \
  "-XX:+UseContainerSupport", \
  "-XX:MaxRAMPercentage=75.0", \
  "-jar", "quarkus-run.jar"]
