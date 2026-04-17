package ma.uiz.api;

import jakarta.annotation.security.RolesAllowed;
import jakarta.inject.Inject;
import jakarta.transaction.Transactional;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import ma.uiz.client.RagEngineClient;
import ma.uiz.client.RagEngineClient.RagChatRequest;
import ma.uiz.client.RagEngineClient.RagChatResponse;
import ma.uiz.domain.User;
import org.eclipse.microprofile.jwt.Claim;
import org.eclipse.microprofile.jwt.JsonWebToken;
import org.eclipse.microprofile.rest.client.inject.RestClient;
import org.jboss.logging.Logger;

/**
 * ChatResource — Endpoint principal du chatbot.
 *
 * ── La sécurité JWT en pratique ──────────────────────────────────────────
 *
 * Ce Resource est protégé par @RolesAllowed. Voici ce qui se passe
 * à chaque requête :
 *
 *   1. Le frontend envoie :
 *      POST /chat
 *      Authorization: Bearer eyJhbGci...
 *
 *   2. Quarkus intercepte la requête AVANT qu'elle arrive dans chat().
 *      Il extrait le token de l'en-tête Authorization.
 *
 *   3. Quarkus vérifie la signature RSA avec la clé publique.
 *      Si signature invalide → 401 Unauthorized automatique.
 *      Si token expiré      → 401 Unauthorized automatique.
 *
 *   4. Quarkus vérifie que le claim "groups" contient "student", "staff" ou "admin".
 *      Si le rôle manque → 403 Forbidden automatique.
 *
 *   5. Si tout est OK → chat() est appelé.
 *      JsonWebToken jwt contient toutes les infos du token déjà validé.
 *
 * En Spring Boot, tout ça était dans SecurityConfig + JwtFilter.
 * Ici, c'est juste @RolesAllowed — tout le reste est géré par Quarkus.
 *
 * ── CDI Request Scope (@RequestScoped) ───────────────────────────────────
 *
 * @RequestScoped = une nouvelle instance par requête HTTP.
 * C'est nécessaire quand on injecte des beans qui ont une portée plus courte
 * que l'application (comme @Claim qui change par requête).
 *
 * Si tu n'injectes pas de claims JWT directement, tu peux mettre @ApplicationScoped.
 */
@Path("/chat")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
@jakarta.enterprise.context.RequestScoped
public class ChatResource {

    private static final Logger LOG = Logger.getLogger(ChatResource.class);

    /**
     * @RestClient est l'annotation CDI pour injecter un MicroProfile Rest Client.
     * @Inject seul ne suffit pas pour les Rest Clients — il faut les deux.
     */
    @Inject
    @RestClient
    RagEngineClient ragClient;

    /**
     * JsonWebToken donne accès au token JWT de la requête courante.
     * Équivalent de Authentication.getPrincipal() dans Spring Security.
     *
     * Injecté automatiquement par Quarkus quand la requête est authentifiée.
     */
    @Inject
    JsonWebToken jwt;

    /**
     * @Claim permet d'injecter un claim spécifique directement.
     * Équivalent de jwt.getClaim("role") mais plus déclaratif.
     * Requiert @RequestScoped sur la classe.
     */
    @Inject
    @Claim("role")
    String userRole;

    @Inject
    @Claim("userId")
    Long userId;

    // ═════════════════════════════════════════════════════════════════════
    //  POST /chat
    // ═════════════════════════════════════════════════════════════════════

    /**
     * Envoie une question au moteur RAG Python.
     *
     * @RolesAllowed({"student", "staff", "admin"}) :
     *   Tous les utilisateurs authentifiés peuvent accéder.
     *   Si tu voulais réserver aux admins : @RolesAllowed("admin")
     *
     * Le rôle est extrait du JWT — impossible de le falsifier.
     * Le Python RAG reçoit le bon rôle et filtre les documents en conséquence.
     */
    @POST
    @RolesAllowed({"student", "staff", "admin"})
    public Response chat(@Valid ChatRequest request) {

        // Le rôle vient du JWT vérifié — pas du corps de la requête
        // C'est LA différence majeure avec le backend Python actuel :
        // ici, l'utilisateur ne peut PAS se mettre "admin" lui-même.
        String authenticatedRole = userRole != null ? userRole : "student";

        LOG.debugf("Chat request from user=%s role=%s session=%s",
                   jwt.getSubject(), authenticatedRole, request.sessionId());

        try {
            // Appel au moteur RAG Python via le Rest Client
            RagChatResponse ragResponse = ragClient.chat(
                new RagChatRequest(
                    request.query(),
                    request.sessionId(),
                    authenticatedRole,   // rôle certifié par le JWT
                    request.imageBase64()
                )
            );

            // On enrichit la réponse avec l'email de l'utilisateur
            ChatResponse response = new ChatResponse(
                ragResponse.answer(),
                ragResponse.sources(),
                ragResponse.sessionId(),
                ragResponse.model(),
                ragResponse.latencyMs(),
                ragResponse.tokensUsed(),
                jwt.getSubject()   // email de l'utilisateur connecté
            );

            return Response.ok(response).build();

        } catch (Exception e) {
            LOG.errorf("Erreur lors de l'appel au RAG engine: %s", e.getMessage());
            return Response.status(Response.Status.INTERNAL_SERVER_ERROR)
                           .entity(new ErrorResponse(
                               "Le moteur RAG est temporairement indisponible. Réessayez dans quelques instants."
                           ))
                           .build();
        }
    }

    // ═════════════════════════════════════════════════════════════════════
    //  DTOs
    // ═════════════════════════════════════════════════════════════════════

    public record ChatRequest(
        @NotBlank(message = "La question ne peut pas être vide")
        @Size(max = 4000, message = "Question trop longue (max 4000 caractères)")
        String query,

        @NotBlank(message = "session_id est requis")
        String sessionId,

        // imageBase64 est optionnel (multimodal CLIP)
        String imageBase64
    ) {}

    public record ChatResponse(
        String answer,
        java.util.List<RagEngineClient.SourceItem> sources,
        String sessionId,
        String model,
        int latencyMs,
        int tokensUsed,
        String askedBy   // email de l'utilisateur — enrichissement JEE
    ) {}

    public record ErrorResponse(String message) {}
}
