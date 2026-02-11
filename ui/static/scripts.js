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
            e.preventDefault(); // Empêche le rechargement
            console.log("Lancement de la demande Streaming...");

            // 1. AFFICHER L'ANIMATION + CACHER LE CONTENU
            const startTime = Date.now();
            const mainEl = document.querySelector('main');
            if (mainEl) mainEl.style.display = 'none';
            modal.style.display = 'none';
            if (loadingOverlay) {
                loadingOverlay.style.display = 'flex';
            }
            const logsContainer = document.getElementById('logs');
            // Rebuild the progress bar structure
            if (logsContainer) {
                logsContainer.innerHTML = `
                    <div class="progress-current-step" id="currentStep">Connexion au satellite...</div>
                    <div class="progress-vertical-track">
                        <div class="progress-vertical-fill" id="progressFill"></div>
                    </div>
                `;
            }
            let progressCount = 0;

            // 2. RÉCUPÉRATION DES PARAMÈTRES
            const formData = new FormData(travelForm);
            const params = new URLSearchParams();
            for (const pair of formData.entries()) {
                params.append(pair[0], pair[1]);
            }

            // 3. LANCEMENT DU STREAM (EventSource)
            const url = `/stream_search?${params.toString()}`;
            const eventSource = new EventSource(url);

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    // --- A. GESTION DES LOGS + BARRE DE PROGRESSION ---
                    if (data.type === 'log' || data.type === 'tool' || data.type === 'error') {
                        // Update the current step label
                        const currentStep = document.getElementById('currentStep');
                        if (currentStep) {
                            currentStep.textContent = data.message;
                        }

                        // Increment progress bar by 10% per message
                        progressCount++;
                        const progressFill = document.getElementById('progressFill');
                        if (progressFill) {
                            const pct = Math.min(progressCount * 20, 100);
                            progressFill.style.width = pct + '%';
                        }
                    }

                    // --- B. ARRIVÉE / MODIFICATION DE PAGE ---
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

                            // MAJ de l'URL pour faire "propre" (Optionnel)
                            // window.history.pushState({}, "Résultats", "/search");
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
                    div.textContent = "Connexion perdue.";
                    logsContainer.appendChild(div);
                }
            };
        };
    }

    // --- 4. GESTION DES OPTIONS AVANCÉES ---
    const toggleOptions = document.getElementById('toggleOptions');
    const advancedOptions = document.getElementById('advanced-options');

    if (toggleOptions && advancedOptions) {
        toggleOptions.onclick = () => {
            advancedOptions.classList.toggle('open');
            toggleOptions.classList.toggle('active');
        };
    }

    // --- 5. CAROUSEL D'IMAGES ---
    let currentSlideIndex = 0;
    let carouselInterval;

    function showSlide(index) {
        const images = document.querySelectorAll('.carousel-image');
        const dots = document.querySelectorAll('.carousel-dots .dot');
        
        if (!images.length) return;
        
        // Wrap around
        if (index >= images.length) currentSlideIndex = 0;
        else if (index < 0) currentSlideIndex = images.length - 1;
        else currentSlideIndex = index;
        
        // Update images
        images.forEach((img, i) => {
            img.classList.toggle('active', i === currentSlideIndex);
        });
        
        // Update dots
        dots.forEach((dot, i) => {
            dot.classList.toggle('active', i === currentSlideIndex);
        });
    }

    function nextSlide() {
        showSlide(currentSlideIndex + 1);
    }

    // Make currentSlide available globally for onclick handlers
    window.currentSlide = function(index) {
        clearInterval(carouselInterval);
        showSlide(index);
        // Restart auto-rotation after manual click
        carouselInterval = setInterval(nextSlide, 4000);
    };

    // Start auto-rotation
    if (document.querySelector('.carousel')) {
        carouselInterval = setInterval(nextSlide, 4000);
    }
});