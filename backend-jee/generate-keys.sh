#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  generate-keys.sh — Génère la paire de clés RSA pour signer les JWT
#
#  À exécuter UNE SEULE FOIS avant le premier lancement.
#  Les clés sont persistantes : ne pas les regénérer en prod
#  sinon tous les tokens existants deviennent invalides.
#
#  Concept RSA dans notre contexte :
#    • Clé PRIVÉE → seul le serveur JEE la connaît → signe le token au login
#    • Clé PUBLIQUE → peut être partagée → vérifie les tokens entrants
#
#  En Spring Boot tu aurais fait : KeyStoreKeyFactory ou un fichier .jks
#  Ici on utilise directement des fichiers PEM (plus lisible).
# ═══════════════════════════════════════════════════════════════════════════

DEST="src/main/resources/META-INF/resources"
mkdir -p "$DEST"

echo "🔑 Génération de la clé privée RSA 2048 bits..."
# La taille 2048 bits est le minimum recommandé pour RSA.
# 4096 bits = plus sécurisé mais signature un peu plus lente.
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
        -out "$DEST/privateKey.pem" 2>/dev/null

echo "🔓 Extraction de la clé publique correspondante..."
openssl rsa -pubout -in "$DEST/privateKey.pem" \
            -out "$DEST/publicKey.pem" 2>/dev/null

echo ""
echo "✅ Clés générées dans $DEST/"
echo "   privateKey.pem → NE PAS COMMITTER en production"
echo "   publicKey.pem  → peut être partagée"
echo ""
echo "⚠️  Ajoutez privateKey.pem à .gitignore pour la production !"
