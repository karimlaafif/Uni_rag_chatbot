package ma.uiz.domain;

import io.quarkus.hibernate.orm.panache.PanacheEntity;
import jakarta.persistence.*;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.Optional;

/**
 * Entité JPA représentant un utilisateur de la plateforme UIZ.
 *
 * ── Quarkus Panache (équivalent Spring Data JPA) ─────────────────────────
 *
 * En Spring Boot, tu aurais fait :
 *   @Entity class User { Long id; ... }
 *   interface UserRepository extends JpaRepository<User, Long> {}
 *
 * Avec Panache, tu peux tout mettre dans la même classe :
 *   class User extends PanacheEntity { ... }
 *   User.find("email", email)    ← méthode statique directement !
 *
 * PanacheEntity fournit automatiquement un champ "id" (Long, auto-increment),
 * et toutes les méthodes CRUD : persist(), delete(), findById(), listAll()...
 *
 * ── Annotations JPA ──────────────────────────────────────────────────────
 * Ce sont les mêmes annotations qu'avec Spring Data JPA (c'est la spec JPA).
 * @Entity, @Table, @Column, @Enumerated — tu les connais déjà.
 */
@Entity
@Table(
    name = "uiz_users",
    uniqueConstraints = @UniqueConstraint(columnNames = "email")
)
public class User extends PanacheEntity {

    /**
     * Email — sert d'identifiant de connexion.
     * Stocké dans le JWT sous le claim "sub" (subject) et "upn".
     */
    @Column(nullable = false, unique = true, length = 200)
    @Email(message = "Format email invalide")
    @NotBlank(message = "L'email est obligatoire")
    public String email;

    /**
     * Mot de passe hashé avec BCrypt.
     * JAMAIS stocké en clair. Le hash est irréversible.
     *
     * Exemple de hash BCrypt pour "motdepasse123" :
     *   $2a$12$K8HFl/TrjZs6n7KyM.8Z3OhwRi8F7e0tJX5Q3vN2lR4dM0eY7a9pW
     */
    @Column(nullable = false)
    @NotBlank
    public String passwordHash;

    /**
     * Prénom et nom — affiché dans l'interface.
     */
    @Column(nullable = false, length = 100)
    @NotBlank(message = "Le nom est obligatoire")
    public String fullName;

    /**
     * Rôle dans le système.
     *
     * @Enumerated(STRING) → stocké comme "STUDENT" / "STAFF" / "ADMIN" en base.
     * Ne pas utiliser ORDINAL (si tu ajoutes un rôle, les indices changent).
     */
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    @NotNull
    public Role role;

    /**
     * Département / composante de l'université.
     * Ex : "informatique", "medecine", "administration"
     */
    @Column(length = 100)
    public String department;

    /**
     * Compte actif ou désactivé (soft delete).
     * Un admin peut désactiver un compte sans le supprimer.
     */
    @Column(nullable = false)
    public boolean active = true;

    /**
     * Date de création du compte.
     * Instant (timestamp UTC) — meilleure pratique que Date ou LocalDateTime.
     */
    @Column(nullable = false, updatable = false)
    public Instant createdAt;

    /**
     * Date de dernière connexion — utile pour les statistiques d'usage.
     */
    @Column
    public Instant lastLoginAt;

    // ── Lifecycle JPA ─────────────────────────────────────────────────────

    /**
     * @PrePersist : appelé automatiquement avant le premier INSERT en base.
     * Équivalent de @CreationTimestamp en Spring Data JPA (Hibernate).
     */
    @PrePersist
    void onPrePersist() {
        this.createdAt = Instant.now();
    }

    // ── Méthodes statiques Panache (requêtes) ─────────────────────────────
    //
    // En Spring Boot, ces méthodes seraient dans UserRepository.
    // Avec Panache, elles vivent directement dans l'entité.
    // Panache génère le SQL automatiquement à partir du nom du champ.

    /**
     * Cherche un utilisateur par email.
     * Panache traduit "email" en : SELECT * FROM uiz_users WHERE email = ?
     *
     * @param email adresse email
     * @return Optional<User> — vide si pas trouvé
     */
    public static Optional<User> findByEmail(String email) {
        return find("email", email).firstResultOptional();
    }

    /**
     * Cherche tous les utilisateurs d'un département.
     * Panache traduit "department = ?1" en JPQL.
     */
    public static java.util.List<User> findByDepartment(String department) {
        return list("department = ?1 AND active = true", department);
    }

    /**
     * Compte le nombre d'utilisateurs actifs par rôle.
     * Exemple de requête JPQL plus complexe.
     */
    public static long countActiveByRole(Role role) {
        return count("role = ?1 AND active = true", role);
    }

    // ── Constructeur factory ──────────────────────────────────────────────

    /**
     * Crée un utilisateur avec toutes les infos nécessaires.
     * Le passwordHash doit déjà être haché (BCrypt) avant d'appeler cette méthode.
     */
    public static User create(String email, String passwordHash,
                               String fullName, Role role, String department) {
        User user = new User();
        user.email        = email.toLowerCase().trim();
        user.passwordHash = passwordHash;
        user.fullName     = fullName;
        user.role         = role;
        user.department   = department;
        user.active       = true;
        return user;
    }

    @Override
    public String toString() {
        return "User{id=" + id + ", email='" + email + "', role=" + role + "}";
    }
}
