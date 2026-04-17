package ma.uiz.client;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import org.eclipse.microprofile.rest.client.inject.RegisterRestClient;

import java.util.List;

/**
 * RagEngineClient — Client HTTP vers le moteur Python RAG (FastAPI).
 *
 * ── MicroProfile Rest Client ─────────────────────────────────────────────
 *
 * C'est la spec Jakarta EE pour faire des appels HTTP sortants de façon
 * déclarative — exactement comme @FeignClient en Spring Cloud.
 *
 * Tu DÉCLARES l'interface Java avec les mêmes annotations JAX-RS (@POST, @Path...)
 * et Quarkus génère automatiquement le code HTTP sous-jacent.
 * Zéro boilerplate, zéro RestTemplate.
 *
 * Configuration dans application.properties :
 *   ma.uiz.client.RagEngineClient/mp-rest/url=http://localhost:8000
 *
 * @RegisterRestClient(configKey = "RagEngineClient") →
 *   Quarkus cherche "ma.uiz.client.RagEngineClient/mp-rest/url" dans les props.
 *   (le préfixe est le chemin complet de l'interface)
 *
 * Utilisation dans un Resource :
 *   @Inject
 *   @RestClient
 *   RagEngineClient ragClient;
 *
 *   RagChatResponse res = ragClient.chat(new RagChatRequest(...));
 */
@RegisterRestClient(configKey = "RagEngineClient")
@Path("/")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public interface RagEngineClient {

    /**
     * Envoie une question au RAG Python.
     * Correspond exactement à POST /chat sur le FastAPI.
     */
    @POST
    @Path("/chat")
    RagChatResponse chat(RagChatRequest request);

    /**
     * Récupère le statut d'indexation de la base de connaissances.
     * Correspond à GET /knowledge/status sur le FastAPI.
     */
    @GET
    @Path("/knowledge/status")
    KnowledgeStatus knowledgeStatus();

    // ═══════════════════════════════════════════════════════════════════
    //  DTOs — Miroir exact des schémas Pydantic côté Python
    // ═══════════════════════════════════════════════════════════════════
    //
    // @JsonProperty sert à mapper les noms snake_case Python
    // vers les noms camelCase Java (convention Java normale).
    // Ex: "session_id" (Python) ↔ sessionId (Java)

    /**
     * Corps envoyé au POST /chat du FastAPI Python.
     * Miroir de ChatRequest dans api/schemas.py.
     */
    record RagChatRequest(
        @JsonProperty("query")
        String query,

        @JsonProperty("session_id")
        String sessionId,

        @JsonProperty("user_role")
        String userRole,

        @JsonProperty("image_base64")
        String imageBase64
    ) {
        /** Constructeur de commodité sans image */
        RagChatRequest(String query, String sessionId, String userRole) {
            this(query, sessionId, userRole, null);
        }
    }

    /**
     * Réponse reçue du GET /chat du FastAPI Python.
     * Miroir de ChatResponse dans api/schemas.py.
     */
    record RagChatResponse(
        String answer,
        List<SourceItem> sources,

        @JsonProperty("session_id")
        String sessionId,

        String model,

        @JsonProperty("latency_ms")
        int latencyMs,

        @JsonProperty("tokens_used")
        int tokensUsed
    ) {}

    /**
     * Une source documentaire citée dans la réponse.
     * Miroir de SourceItem dans api/schemas.py.
     */
    record SourceItem(
        String title,
        String url,

        @JsonProperty("rerank_score")
        Double rerankScore,

        @JsonProperty("access_level")
        String accessLevel
    ) {}

    /**
     * Statut de la base de connaissances.
     * Miroir de KnowledgeStatusResponse dans api/schemas.py.
     */
    record KnowledgeStatus(
        String status,

        @JsonProperty("last_update")
        String lastUpdate
    ) {}
}
