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

    // --- 3. GESTION DES OPTIONS AVANCÉES ---
    const toggleOptions = document.getElementById('toggleOptions');
    const advancedOptions = document.getElementById('advanced-options');

    if (toggleOptions && advancedOptions) {
        toggleOptions.onclick = () => {
            toggleOptions.classList.toggle('active');
            advancedOptions.classList.toggle('open');
        };
    }

    // --- 4. GESTION DE LA SOUMISSION ET DE L'ANIMATION ---

    if (travelForm) {
        travelForm.onsubmit = (e) => {
            e.preventDefault(); // Empêche le rechargement
            console.log("🚀 Lancement de la demande Streaming...");

            // A. AFFICHER L'ANIMATION + LOGS
            const startTime = Date.now(); // On note l'heure de départ
            modal.style.display = 'none';
            if (loadingOverlay) {
                loadingOverlay.style.display = 'flex';
            }
            const logsContainer = document.getElementById('logs');
            if (logsContainer) logsContainer.innerHTML = '<div>Connexion au satellite...</div>';

            // B. RÉCUPÉRATION DES PARAMÈTRES
            const origin = document.getElementById('origin').value;
            const dest = document.getElementById('destination').value;
            const pref = document.getElementById('preferences').value;
            const dateDept = document.getElementById('departure_date').value;
            const budget = document.getElementById('budget_max').value;
            const airline = document.getElementById('airline').value;
            const activities = document.getElementById('activities').value;
            const hotelBudget = document.getElementById('hotel_budget_max').value;
            const hotelAmenities = document.getElementById('amenities').value;

            // On construit l'URL avec tous les paramètres
            // Note: encodeURIComponent est une bonne pratique pour éviter les bugs avec des espaces ou caractères spéciaux
            const params = new URLSearchParams({
                origin: origin,
                destination: dest,
                preferences: pref,
                budget_max: budget,
                airline: airline,
                date: dateDept,
                activities: activities,
                hotel_budget_max: hotelBudget,
                amenities: hotelAmenities
            });

            const url = `/stream_search?${params.toString()}`;

            const eventSource = new EventSource(url);

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    // --- C. GESTION DES LOGS ---
                    if (data.type === 'log' || data.type === 'tool' || data.type === 'error') {
                        const div = document.createElement('div');
                        div.className = `log-entry ${data.type}`;
                        div.textContent = `> ${data.message}`;
                        if (logsContainer) {
                            logsContainer.appendChild(div);
                            logsContainer.scrollTop = logsContainer.scrollHeight; // Auto-scroll
                        }
                    }

                    // --- D. ARRIVÉE / MODIFICATION DE PAGE ---
                    else if (data.type === 'complete') {
                        console.log("🛬 Terminé ! Affichage des résultats.");
                        eventSource.close();

                        // CALCUL DU DELAI RESTANT (Minimum 6 secondes d'animation)
                        const elapsedTime = Date.now() - startTime;
                        const remainingTime = Math.max(0, 6000 - elapsedTime);

                        console.log(`Temps écoulé: ${elapsedTime}ms. Attente de: ${remainingTime}ms.`);

                        setTimeout(() => {
                            // Option 1 : Remplacer le contenu de la page (effet SPA)
                            document.open();
                            document.write(data.html);
                            document.close();
                        }, remainingTime);
                    }

                } catch (err) {
                    console.error("Erreur parsing SSE:", err);
                }
            };

            eventSource.onerror = (err) => {
                console.error("Erreur EventSource:", err);
                eventSource.close();
                if (logsContainer) {
                    const div = document.createElement('div');
                    div.style.color = "red";
                    div.textContent = "> ❌ Connexion perdue.";
                    logsContainer.appendChild(div);
                }
            };
        };
    }
});