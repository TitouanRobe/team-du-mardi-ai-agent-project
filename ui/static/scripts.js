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
    openBtn.onclick = () => {
        modal.style.display = 'flex';
        // On cache le résultat précédent si on rouvre
        if(resultContainer) resultContainer.style.display = 'none';
    };

    // Fermer la modale (Bouton X)
    closeBtn.onclick = () => {
        modal.style.display = 'none';
    };

    // Fermer la modale (Clic à l'extérieur)
    window.onclick = (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    };

    // --- 3. GESTION DE LA SOUMISSION ET DE L'ANIMATION ---
    
    travelForm.onsubmit = (e) => {
        e.preventDefault(); // Empêche le rechargement de la page
        console.log("🚀 Lancement de la demande...");

        // A. ON LANCE L'ANIMATION
        modal.style.display = 'none';          // On cache le formulaire
        loadingOverlay.style.display = 'flex'; // On affiche l'avion en plein écran

        // B. ON SIMULE UN TEMPS D'ATTENTE (4 secondes)
        // (C'est ici que plus tard, on mettra l'appel à l'IA)
        setTimeout(() => {
            
            // C. FIN DE L'ANIMATION
            console.log("🛬 Arrivée !");
            loadingOverlay.style.display = 'none'; // On cache l'avion

            // D. AFFICHAGE D'UN RÉSULTAT TEST
            if (resultContainer) {
                resultContainer.style.display = 'block';
                resultContainer.innerHTML = "<h3>✅ L'avion a bien atterri !</h3><p>L'animation fonctionne. L'IA afficherait son résultat ici.</p>";
            } else {
                alert("L'animation est terminée !");
            }

        }, 4000); // 4000 ms = 4 secondes
    };
});