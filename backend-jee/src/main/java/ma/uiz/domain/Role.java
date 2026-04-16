package ma.uiz.domain;

/**
 * Enum des rôles utilisateur dans le système UIZ.
 *
 * Ces valeurs sont stockées en base et embedées dans le JWT.
 * Le backend Python RAG utilise les mêmes valeurs string ("student", etc.)
 * pour filtrer l'accès aux documents Qdrant.
 *
 * En Spring Boot tu aurais utilisé GrantedAuthority.
 * Ici c'est un simple enum Java — MicroProfile JWT sait le lire directement.
 */
public enum Role {

    /**
     * Étudiant : accès aux documents publics uniquement.
     * Peut consulter programmes, calendriers, infos générales.
     */
    STUDENT,

    /**
     * Personnel universitaire : accès aux documents publics + staff.
     * Peut consulter procédures internes, listes étudiants, etc.
     */
    STAFF,

    /**
     * Administrateur : accès complet.
     * Peut uploader des documents, lancer les benchmarks, voir tous les logs.
     */
    ADMIN
}
