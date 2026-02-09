// ui/static/scripts.js

document.addEventListener('DOMContentLoaded', () => {

    // --- 1. RÉCUPÉRATION DES ÉLÉMENTS DU DOM ---
    const modal = document.getElementById('modalOverlay');
    const openBtn = document.getElementById('openModal');
    const closeBtn = document.getElementById('closeModal');
    const travelForm = document.getElementById('travelForm');

    // Nouveaux éléments pour l'animation
    const loadingOverlay = document.getElementById('loading-overlay');
    const resultContainer = document.getElementById('resultContainer');

    // --- 2. GESTION DE LA MODALE (OUVERTURE / FERMETURE) ---

    // Ouvrir la modale
    if (openBtn) {
        openBtn.onclick = () => {
            modal.style.display = 'flex';
        };
    }

    // Fermer la modale (Bouton X)
    if (closeBtn) {
        closeBtn.onclick = () => {
            modal.style.display = 'none';
        };
    }

    // Fermer la modale (Clic à l'extérieur)
    window.onclick = (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    };

    // --- 3. GESTION DE LA SOUMISSION ET DE L'ANIMATION ---

    if (travelForm) {
        travelForm.onsubmit = (e) => {
            e.preventDefault(); // Empêche le rechargement immédiat
            console.log("🚀 Lancement de la demande...");

            // A. ON LANCE L'ANIMATION
            modal.style.display = 'none';          // On cache le formulaire
            if (loadingOverlay) {
                loadingOverlay.style.display = 'flex'; // On affiche l'avion en plein écran
            }

            // B. ON SIMULE UN TEMPS D'ATTENTE (Ex: 3 secondes pour l'effet)
            // Puis on soumet VRAIMENT le formulaire au serveur
            setTimeout(() => {
                console.log("🛬 Redirection vers les résultats...");
                e.target.submit(); // Soumission manuelle du formulaire (recharge la page vers /search)
            }, 3000);
        };
    }
});