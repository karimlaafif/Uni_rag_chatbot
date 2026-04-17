package ma.uiz.auth;

import io.smallrye.jwt.build.Jwt;
import jakarta.enterprise.context.ApplicationScoped;
import ma.uiz.domain.User;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.time.Instant;
import java.util.Set;

/**
 * TokenService — Responsable de la génération des JWT.
 *
 * ── Pourquoi une classe dédiée ? ────────────────────────────────────────
 * En Spring Boot avec JJWT, tu aurais probablement fait un JwtUtil.java.
 * Même idée ici. Ce service encapsule toute la logique de création du token
 * pour qu'aucune autre classe ne s'en préoccupe.
 *
 * ── Structure du JWT généré ──────────────────────────────────────────────
 *
 * Header (algorithme RS256 — RSA + SHA-256) :
 *   { "alg": "RS256", "typ": "JWT" }
 *
 * Payload (claims = données dans le token) :
 *   {
 *     "iss": "https://uiz.ac.ma",          ← issuer (qui a émis le token)
 *     "sub": "anas@uiz.ac.ma",             ← subject (qui est l'utilisateur)
 *     "upn": "anas@uiz.ac.ma",             ← user principal name (spec MP-JWT)
 *     "groups": ["student"],               ← rôles (spec MP-JWT, ex-roles)
 *     "fullName": "Anas Benchikhi",        ← claim custom
 *     "department": "informatique",        ← claim custom
 *     "userId": 42,                        ← claim custom
 *     "iat": 1744408000,                   ← issued at (Unix timestamp)
 *     "exp": 1744436800                    ← expiration (iat + 8h)
 *   }
 *
 * Signature :
 *   RSA-SHA256(base64(header) + "." + base64(payload), clé_privée)
 *
 * ── Pourquoi "groups" et pas "roles" ? ──────────────────────────────────
 * La spec MicroProfile JWT appelle le claim des rôles "groups".
 * Quarkus le mappe automatiquement sur @RolesAllowed.
 * C'est juste une convention de nommage de la spec, pas un changement de sens.
 *
 * @ApplicationScoped = CDI, équivalent @Service en Spring Boot.
 */
@ApplicationScoped
public class TokenService {

    /**
     * @ConfigProperty injecte la valeur depuis application.properties.
     * Équivalent de @Value("${mp.jwt.verify.issuer}") en Spring Boot.
     */
    @ConfigProperty(name = "mp.jwt.verify.issuer")
    String issuer;

    /**
     * Durée de validité en secondes (configurée dans application.properties).
     * Par défaut 28800 = 8 heures.
     */
    @ConfigProperty(name = "smallrye.jwt.new-token.lifespan", defaultValue = "28800")
    long lifespanSeconds;

    /**
     * Génère un JWT signé pour l'utilisateur donné.
     *
     * io.smallrye.jwt.build.Jwt est le builder de tokens de Quarkus.
     * Il lit automatiquement la clé privée depuis le chemin configuré
     * (smallrye.jwt.sign.key.location dans application.properties).
     *
     * @param user L'utilisateur authentifié (email + rôle validés)
     * @return Le JWT sous forme de String (ex: "eyJhbGci...")
     */
    public String generateToken(User user) {
        Instant now        = Instant.now();
        Instant expiration = now.plusSeconds(lifespanSeconds);

        return Jwt
            // ── Claims standard (spec JWT RFC 7519) ────────────────────
            .issuer(issuer)                          // qui a émis le token
            .subject(user.email)                     // identité de l'utilisateur
            .issuedAt(now)                           // quand il a été créé
            .expiresAt(expiration)                   // quand il expire

            // ── Claim "groups" — requis par MicroProfile JWT ───────────
            // C'est ce claim que @RolesAllowed("student") va lire.
            // On passe un Set<String> avec le rôle en minuscule.
            .groups(Set.of(user.role.name().toLowerCase()))

            // ── Claims custom (données propres à notre app) ────────────
            // Ces claims sont lisibles dans n'importe quel endpoint
            // via @Inject JsonWebToken jwt; jwt.getClaim("fullName");
            .claim("upn",        user.email)         // requis par MP-JWT spec
            .claim("fullName",   user.fullName)
            .claim("department", user.department != null ? user.department : "")
            .claim("userId",     user.id)
            .claim("role",       user.role.name().toLowerCase())  // redondant mais pratique

            // ── Signature avec la clé privée ───────────────────────────
            // Quarkus lit la clé depuis META-INF/resources/privateKey.pem
            // (configuré dans application.properties)
            .sign();
    }
}
