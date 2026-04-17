package ma.uiz.api;

import jakarta.annotation.security.RolesAllowed;
import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import ma.uiz.client.RagEngineClient;
import org.eclipse.microprofile.rest.client.inject.RestClient;
import org.jboss.logging.Logger;

/**
 * KnowledgeResource — Gestion de la base de connaissances.
 *
 * Illustre un cas RBAC plus strict :
 *
 *   GET  /knowledge/status  → accessible à tous les connectés
 *   POST /knowledge/update  → RÉSERVÉ aux admins (@RolesAllowed("admin"))
 *
 * En Spring Boot, tu aurais configuré ça dans SecurityConfig.authorizeHttpRequests().
 * Ici chaque méthode porte son annotation — plus lisible et colocalisé avec le code.
 *
 * ── Upload multipart ─────────────────────────────────────────────────────
 * L'upload de fichier passe par multipart/form-data.
 * En Jakarta EE : @MultipartForm + classe dédiée avec @PartType.
 * En Spring Boot : @RequestParam("file") MultipartFile file.
 *
 * Ici on réimplémente l'upload côté JEE et on le forwarde au Python.
 * Le Python garde la responsabilité de l'ingestion (chunking, CLIP, Qdrant).
 */
@Path("/knowledge")
@Produces(MediaType.APPLICATION_JSON)
public class KnowledgeResource {

    private static final Logger LOG = Logger.getLogger(KnowledgeResource.class);

    @Inject
    @RestClient
    RagEngineClient ragClient;

    /**
     * GET /knowledge/status — Statut de l'indexation.
     *
     * @RolesAllowed sans restriction de rôle spécifique →
     * tous les utilisateurs authentifiés (student/staff/admin) peuvent voir.
     *
     * Utile pour l'interface : afficher "Base à jour" ou "Indexation en cours".
     */
    @GET
    @Path("/status")
    @RolesAllowed({"student", "staff", "admin"})
    public Response getStatus() {
        try {
            RagEngineClient.KnowledgeStatus status = ragClient.knowledgeStatus();
            return Response.ok(status).build();
        } catch (Exception e) {
            LOG.errorf("Impossible de récupérer le statut RAG: %s", e.getMessage());
            return Response.status(Response.Status.SERVICE_UNAVAILABLE)
                           .entity(new ErrorResponse("Moteur RAG inaccessible"))
                           .build();
        }
    }

    /**
     * POST /knowledge/update — Upload d'un document pour indexation.
     *
     * RÉSERVÉ AUX ADMINS — @RolesAllowed("admin")
     *
     * Si un student ou staff essaie d'accéder → 403 Forbidden automatique.
     * Quarkus vérifie le rôle dans le JWT AVANT d'entrer dans la méthode.
     *
     * Note : Pour l'upload de fichiers, on délègue directement au Python
     * via le multipart. Voir l'endpoint /knowledge/update du FastAPI (api/main.py).
     */
    @POST
    @Path("/upload-info")
    @RolesAllowed("admin")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response uploadInfo(UploadRequest request) {
        // Dans une implémentation complète, tu recevrais le fichier ici en multipart
        // et tu le forwarderais au Python.
        // Pour l'instant, on retourne les infos que le frontend devra envoyer directement.
        // (L'upload direct vers Python reste possible depuis le panel admin React)
        LOG.infof("Admin requested document upload: dept=%s access=%s",
                  request.department(), request.accessLevel());

        return Response.ok(new UploadConfirm(
            "Upload autorisé. Envoyez le fichier directement à /knowledge/update du moteur RAG.",
            request.department(),
            request.accessLevel()
        )).build();
    }

    // DTOs
    public record UploadRequest(String department, String accessLevel) {}
    public record UploadConfirm(String message, String department, String accessLevel) {}
    public record ErrorResponse(String message) {}
}
