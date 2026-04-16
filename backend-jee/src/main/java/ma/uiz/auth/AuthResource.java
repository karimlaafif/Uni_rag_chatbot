package ma.uiz.auth;

import io.quarkus.elytron.security.common.BcryptUtil;
import jakarta.inject.Inject;
import jakarta.transaction.Transactional;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import ma.uiz.domain.Role;
import ma.uiz.domain.User;

import java.time.Instant;

/**
 * AuthResource — Endpoints d'authentification.
 *
 * ── Correspondance Spring Boot ───────────────────────────────────────────
 *
 * Spring Boot :          │  Quarkus / Jakarta EE :
 * ─────────────────────────────────────────────────────────────────
 * @RestController        │  @Path (sur la classe)
 * @RequestMapping("/x")  │  @Path("/x")
 * @PostMapping           │  @POST
 * @GetMapping            │  @GET
 * @RequestBody           │  corps de la méthode (Jackson désérialise auto)
 * ResponseEntity<T>      │  Response (jakarta.ws.rs.core.Response)
 * @Service               │  @ApplicationScoped (CDI)
 * @Autowired             │  @Inject (CDI)
 *
 * ── Endpoints exposés ────────────────────────────────────────────────────
 * POST /auth/login    → connexion, retourne un JWT
 * POST /auth/register → inscription (désactivé en prod, admin seulement)
 * POST /auth/refresh  → renouvelle un token (à implémenter si besoin)
 *
 * @Path("/auth") sur la classe = préfixe commun à toutes les routes.
 * Équivalent de @RequestMapping("/auth") sur la classe en Spring Boot.
 */
@Path("/auth")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class AuthResource {

    /**
     * @Inject = CDI = équivalent exact de @Autowired en Spring Boot.
     * Le container Quarkus injecte automatiquement l'instance.
     */
    @Inject
    TokenService tokenService;

    // ═════════════════════════════════════════════════════════════════════
    //  POST /auth/login
    // ═════════════════════════════════════════════════════════════════════

    /**
     * Authentifie un utilisateur et retourne un JWT.
     *
     * Flux complet :
     *   1. Reçoit { email, password } en JSON
     *   2. Recherche l'utilisateur en base par email
     *   3. Compare le mot de passe avec le hash BCrypt
     *   4. Génère un JWT signé avec le rôle de l'utilisateur
     *   5. Retourne { token, user_info }
     *
     * @Valid déclenche Bean Validation sur LoginRequest.
     * Si une contrainte est violée (@NotBlank, @Email...), Quarkus retourne
     * automatiquement un 400 Bad Request avec les messages d'erreur.
     */
    @POST
    @Path("/login")
    @Transactional   // ouvre une transaction JPA pour la lecture en base
    public Response login(@Valid LoginRequest req) {

        // 1. Cherche l'utilisateur par email (méthode Panache dans User)
        User user = User.findByEmail(req.email)
                        .orElse(null);

        // 2. Sécurité : même message d'erreur si email inconnu OU mot de passe faux.
        //    C'est intentionnel — on ne veut pas dire "cet email n'existe pas"
        //    car ça permettrait d'énumérer les comptes existants.
        if (user == null || !user.active) {
            return Response.status(Response.Status.UNAUTHORIZED)
                           .entity(new ErrorResponse("Identifiants incorrects"))
                           .build();
        }

        // 3. Vérification BCrypt
        //    BcryptUtil.matches() compare "motdepasse_en_clair" avec le hash stocké.
        //    BCrypt est LENT volontairement (work factor 12 = 2^12 itérations)
        //    pour résister aux attaques par force brute.
        if (!BcryptUtil.matches(req.password, user.passwordHash)) {
            return Response.status(Response.Status.UNAUTHORIZED)
                           .entity(new ErrorResponse("Identifiants incorrects"))
                           .build();
        }

        // 4. Met à jour la date de dernière connexion
        user.lastLoginAt = Instant.now();
        // Pas besoin d'appeler user.persist() ici !
        // @Transactional + JPA = dirty checking automatique.
        // Quarkus détecte que l'entité a changé et fait le UPDATE à la fin de la transaction.
        // C'est la même chose qu'avec Spring @Transactional.

        // 5. Génère et retourne le token
        String token = tokenService.generateToken(user);

        return Response.ok(new LoginResponse(token, user)).build();
    }

    // ═════════════════════════════════════════════════════════════════════
    //  POST /auth/register  (admin uniquement en production)
    // ═════════════════════════════════════════════════════════════════════

    /**
     * Crée un nouveau compte utilisateur.
     *
     * En production, cet endpoint devrait être protégé par @RolesAllowed("admin").
     * Pour le développement, il reste ouvert pour créer le premier admin.
     *
     * @Transactional ici est crucial : si user.persist() échoue (ex: email déjà pris),
     * la transaction est rollbackée automatiquement → pas de données corrompues.
     */
    @POST
    @Path("/register")
    @Transactional
    public Response register(@Valid RegisterRequest req) {

        // Vérifie si l'email est déjà utilisé
        if (User.findByEmail(req.email).isPresent()) {
            return Response.status(Response.Status.CONFLICT)
                           .entity(new ErrorResponse("Cet email est déjà utilisé"))
                           .build();
        }

        // Hash du mot de passe avec BCrypt (work factor 12)
        // Ne JAMAIS stocker le mot de passe en clair
        String hash = BcryptUtil.bcryptHash(req.password);

        // Détermine le rôle (default: STUDENT)
        Role role = Role.STUDENT;
        if ("staff".equalsIgnoreCase(req.role))  role = Role.STAFF;
        if ("admin".equalsIgnoreCase(req.role))  role = Role.ADMIN;

        // Crée et persiste l'utilisateur
        User user = User.create(req.email, hash, req.fullName, role, req.department);
        user.persist();  // équivalent de userRepository.save(user) en Spring Data

        // Génère le token directement pour que l'utilisateur soit connecté après inscription
        String token = tokenService.generateToken(user);

        return Response.status(Response.Status.CREATED)
                       .entity(new LoginResponse(token, user))
                       .build();
    }

    // ═════════════════════════════════════════════════════════════════════
    //  DTOs (Data Transfer Objects) — Records Java 17
    // ═════════════════════════════════════════════════════════════════════
    //
    // En Spring Boot, tu utilisais probablement des classes avec getters/setters
    // ou des @Data Lombok. Avec Java 17+, les records sont plus propres :
    // immutables, pas de boilerplate, equals/hashCode/toString automatiques.
    // Jackson les sérialise/désérialise automatiquement.

    /**
     * Corps de la requête POST /auth/login
     *
     * @NotBlank et @Email sont des annotations Bean Validation.
     * Quarkus les valide automatiquement grâce à @Valid sur le paramètre.
     */
    public record LoginRequest(
        @NotBlank(message = "L'email est requis")
        @Email(message = "Format email invalide")
        String email,

        @NotBlank(message = "Le mot de passe est requis")
        String password
    ) {}

    /**
     * Corps de la requête POST /auth/register
     */
    public record RegisterRequest(
        @NotBlank @Email String email,
        @NotBlank @Size(min = 6, message = "Mot de passe min. 6 caractères") String password,
        @NotBlank String fullName,
        String role,         // "student", "staff", "admin"
        String department
    ) {}

    /**
     * Réponse retournée après login ou register.
     * Le frontend stocke le token et l'envoie dans chaque requête suivante.
     */
    public record LoginResponse(
        String token,
        String tokenType,
        long expiresIn,     // secondes avant expiration
        UserInfo user
    ) {
        // Constructeur de commodité
        LoginResponse(String token, User user) {
            this(
                token,
                "Bearer",
                28800L,
                new UserInfo(user.id, user.email, user.fullName,
                             user.role.name().toLowerCase(), user.department)
            );
        }
    }

    /**
     * Infos utilisateur exposées dans la réponse (sans passwordHash !)
     */
    public record UserInfo(
        Long   id,
        String email,
        String fullName,
        String role,
        String department
    ) {}

    /**
     * Réponse d'erreur uniforme.
     */
    public record ErrorResponse(String message) {}
}
