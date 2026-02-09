// ui/static/script.js

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('modalOverlay');
    const openBtn = document.getElementById('openModal');
    const closeBtn = document.getElementById('closeModal');
    const travelForm = document.getElementById('travelForm');

    // Ouvrir la modale
    openBtn.onclick = () => {
        modal.style.display = 'flex';
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

    // Gestion de la soumission du formulaire
    travelForm.onsubmit = (e) => {
        e.preventDefault();
        console.log("Décollage de l'IA...");
        // Ici, on déclenchera l'animation de l'avion plus tard
    };
});