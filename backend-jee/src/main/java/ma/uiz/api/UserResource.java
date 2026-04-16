package ma.uiz.api;

import jakarta.annotation.security.RolesAllowed;
import jakarta.inject.Inject;
import jakarta.transaction.Transactional;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import ma.uiz.domain.Role;
import ma.uiz.domain.User;
import org.eclipse.microprofile.jwt.Claim;
import org.eclipse.microprofile.jwt.JsonWebToken;

import java.util.List;
import java.util.Map;

/**
 * UserResource — Gestion des utilisateurs.
 *
 * Illustre la RBAC fine : certaines actions dépendent non seulement
 * du rôle mais aussi de l'identité (un utilisateur peut voir SON profil,
 * un admin peut voir TOUS les profils).
 *
 * ── Tableau récapitulatif RBAC ────────────────────────────────────────────
 *
 *   GET  /users/me          → tout utilisateur connecté (son propre profil)
 *   GET  /users             → admin seulement
 *   GET  /users/{id}        → admin seulement
 *   PUT  /users/{id}/role   → admin seulement
 *   DELETE /users/{id}      → admin seulement (soft delete)
 */
@Path("/users")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
@jakarta.enterprise.context.RequestScoped
public class UserResource {

    @Inject
    JsonWebToken jwt;

    @Inject
    @Claim("userId")
    Long currentUserId;

    // ─────────────────────────────────────────────────────────────────────
    //  GET /users/me — Profil de l'utilisateur connecté
    // ─────────────────────────────────────────────────────────────────────

    /**
     * Retourne le profil de l'utilisateur actuellement connecté.
     *
     * @RolesAllowed({"student", "staff", "admin"}) → tout le monde.
     * On récupère l'ID depuis le JWT (@Claim("userId")) — pas de paramètre
     * URL pour éviter qu'un utilisateur accède au profil d'un autre.
     */
    @GET
    @Path("/me")
    @RolesAllowed({"student", "staff", "admin"})
    @Transactional
    public Response getMyProfile() {
        User user = User.findById(currentUserId);
        if (user == null) {
            return Response.status(Response.Status.NOT_FOUND)
                           .entity(Map.of("message", "Utilisateur non trouvé"))
                           .build();
        }
        return Response.ok(toDto(user)).build();
    }

    // ─────────────────────────────────────────────────────────────────────
    //  GET /users — Liste de tous les utilisateurs (admin)
    // ─────────────────────────────────────────────────────────────────────

    /**
     * Liste tous les utilisateurs.
     * ADMIN UNIQUEMENT — si un student essaie → 403 automatique.
     */
    @GET
    @RolesAllowed("admin")
    @Transactional
    public List<UserDto> listAll() {
        return User.<User>listAll()
                   .stream()
                   .map(this::toDto)
                   .toList();
    }

    // ─────────────────────────────────────────────────────────────────────
    //  PUT /users/{id}/role — Changer le rôle (admin)
    // ─────────────────────────────────────────────────────────────────────

    /**
     * Change le rôle d'un utilisateur.
     *
     * @PathParam injecte la variable {id} depuis l'URL.
     * Équivalent de @PathVariable en Spring Boot.
     *
     * @Transactional + dirty checking JPA :
     * On modifie user.role directement — Quarkus/Hibernate détecte le
     * changement et fait l'UPDATE automatiquement en fin de transaction.
     * Pas besoin d'appeler user.persist() ou userRepository.save().
     */
    @PUT
    @Path("/{id}/role")
    @RolesAllowed("admin")
    @Transactional
    public Response changeRole(
        @PathParam("id") Long id,
        RoleChangeRequest request
    ) {
        User user = User.findById(id);
        if (user == null) {
            return Response.status(Response.Status.NOT_FOUND)
                           .entity(Map.of("message", "Utilisateur non trouvé"))
                           .build();
        }

        try {
            user.role = Role.valueOf(request.role().toUpperCase());
            // Pas de user.persist() — @Transactional fait le UPDATE automatiquement
        } catch (IllegalArgumentException e) {
            return Response.status(Response.Status.BAD_REQUEST)
                           .entity(Map.of("message", "Rôle invalide : " + request.role()))
                           .build();
        }

        return Response.ok(toDto(user)).build();
    }

    // ─────────────────────────────────────────────────────────────────────
    //  DELETE /users/{id} — Désactivation (soft delete, admin)
    // ─────────────────────────────────────────────────────────────────────

    /**
     * Désactive un compte (soft delete — on ne supprime pas en base).
     *
     * Pourquoi ne pas supprimer vraiment ?
     * → Les logs de conversation font référence à l'userId.
     * → Conformité RGPD : on peut anonymiser plutôt que supprimer.
     * → Un admin peut réactiver le compte si besoin.
     */
    @DELETE
    @Path("/{id}")
    @RolesAllowed("admin")
    @Transactional
    public Response deactivate(@PathParam("id") Long id) {
        User user = User.findById(id);
        if (user == null) {
            return Response.status(Response.Status.NOT_FOUND)
                           .entity(Map.of("message", "Utilisateur non trouvé"))
                           .build();
        }

        user.active = false;  // soft delete — dirty checking fait le UPDATE
        return Response.ok(Map.of(
            "message", "Compte désactivé",
            "userId", id
        )).build();
    }

    // ─────────────────────────────────────────────────────────────────────
    //  Stats (admin)
    // ─────────────────────────────────────────────────────────────────────

    @GET
    @Path("/stats")
    @RolesAllowed("admin")
    @Transactional
    public Response getStats() {
        return Response.ok(Map.of(
            "total_students", User.countActiveByRole(Role.STUDENT),
            "total_staff",    User.countActiveByRole(Role.STAFF),
            "total_admins",   User.countActiveByRole(Role.ADMIN)
        )).build();
    }

    // ─────────────────────────────────────────────────────────────────────
    //  Méthodes utilitaires privées
    // ─────────────────────────────────────────────────────────────────────

    /** Convertit une entité User en DTO sans exposer le passwordHash. */
    private UserDto toDto(User user) {
        return new UserDto(
            user.id,
            user.email,
            user.fullName,
            user.role.name().toLowerCase(),
            user.department,
            user.active,
            user.createdAt != null ? user.createdAt.toString() : null,
            user.lastLoginAt != null ? user.lastLoginAt.toString() : null
        );
    }

    // DTOs
    public record UserDto(
        Long   id,
        String email,
        String fullName,
        String role,
        String department,
        boolean active,
        String createdAt,
        String lastLoginAt
    ) {}

    public record RoleChangeRequest(String role) {}
}
