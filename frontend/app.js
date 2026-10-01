const API_BASE = "";
let currentUserId = 1;
let currentTabStatus = "All";
let userLibraryEntries = [];
let mangaCacheMap = new Map();

const libraryGrid = document.getElementById("libraryGrid");
const emptyLibraryMsg = document.getElementById("emptyLibraryMsg");
const searchModal = document.getElementById("searchModal");
const editModal = document.getElementById("editModal");
const searchInput = document.getElementById("searchInput");
const searchResultsGrid = document.getElementById("searchResultsGrid");
const editForm = document.getElementById("editMangaForm");

document.addEventListener("DOMContentLoaded", async () => {
    await initializeUser();
    setupEventListeners();
    await loadUserLibrary();
});

async function initializeUser() {
    try {
        const res = await fetch(`${API_BASE}/users/${currentUserId}`);
        if (!res.ok) {
            await fetch(`${API_BASE}/users/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: "DemoUser" })
            });
        }
    } catch (err) {
        console.error("Failed initializing default user:", err);
    }
}

function setupEventListeners() {
    document.querySelectorAll(".tab-btn[data-tab]").forEach(btn => {
        btn.addEventListener("click", (e) => {
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            e.target.classList.add("active");
            currentTabStatus = e.target.dataset.tab;
            if (currentTabStatus === "Recommendations")
            {
                renderRecommendations();
            }
            else
            {
                renderLibrary();
            }
        });
    });

    document.getElementById("openSearchBtn")?.addEventListener("click", () => searchModal.classList.remove("hidden"));
    document.getElementById("closeSearchBtn")?.addEventListener("click", () => searchModal.classList.add("hidden"));
    document.getElementById("closeEditBtn")?.addEventListener("click", () => editModal.classList.add("hidden"));
    (document.getElementById("cancelEditBtn") || document.getElementById("cancelEditButton"))?.addEventListener("click", () => editModal.classList.add("hidden"));

    document.getElementById("searchSubmitBtn")?.addEventListener("click", executeSearch);
    document.getElementById("searchInput")?.addEventListener("keypress", (e) => {
        if (e.key == "Enter") executeSearch();
    });

    editForm?.addEventListener("submit", handleEditSubmit);
}

async function loadUserLibrary() {
    try {
        const res = await fetch(`${API_BASE}/list/${currentUserId}`);
        if (!res.ok) throw new Error("Failed fetching list");

        userLibraryEntries = await res.json();

        for (const entry of userLibraryEntries) {
            if (!mangaCacheMap.has(entry.manga_id)) {
                const mangaRes = await fetch(`${API_BASE}/manga/${entry.manga_id}`);
                if (mangaRes.ok) {
                    const mangaData = await mangaRes.json();
                    mangaCacheMap.set(entry.manga_id, mangaData);
                }
            }
        }
        renderLibrary();
    } catch (err) {
        console.error("Error loading library:", err);
    }
}

function renderLibrary() {
    libraryGrid.innerHTML = "";

    const filtered = userLibraryEntries.filter(entry => {
        return currentTabStatus == "All" || entry.status == currentTabStatus;
    });

    if (filtered.length === 0) {
        emptyLibraryMsg.classList.remove("hidden");
        return;
    }
    emptyLibraryMsg.classList.add("hidden");

    filtered.forEach(entry => {
        const manga = mangaCacheMap.get(entry.manga_id) || { title: "Loading...", cover_filename: null };
        const card = document.createElement("div");
        card.className = "manga-card";

        const coverUrl = manga.cover_filename
            ? `https://uploads.mangadex.org/covers/${manga.manga_id}/${manga.cover_filename}.256.jpg`
            : "No cover placeholder";

        card.innerHTML = `<div class="cover-wrapper">
                <img class="cover-img" src="${coverUrl}" alt="${manga.title}" loading="lazy">
                ${entry.score ? `<span class="card-badge">★ ${entry.score.toFixed(1)}</span>` : ""}
            </div>
            <div class="card-body">
                <h3 class="card-title">${manga.title}</h3>
                <div class="card-meta">
                    <span>Ch. ${entry.last_chapter_read}</span>
                    <span>${entry.status}</span>
                </div>
            </div>`;

        card.addEventListener("click", () => openEditModal(entry, manga));
        libraryGrid.appendChild(card);
    });
}

async function executeSearch() {
    const inputEl = document.getElementById("searchInput");
    const query = inputEl ? inputEl.value.trim() : "";
    if (!query) return;

    searchResultsGrid.innerHTML = "<p style='grid-column: 1/-1; text-align:center;'>Searching...</p>";

    try {
        const res = await fetch(`${API_BASE}/manga/search?q=${encodeURIComponent(query)}`);
        if (!res.ok) throw new Error("Search failed");

        const results = await res.json();
        searchResultsGrid.innerHTML = "";

        results.forEach(manga => {
            mangaCacheMap.set(manga.manga_id, manga);

            const card = document.createElement("div");
            card.className = "manga-card";

            const coverUrl = manga.cover_filename
                ? `https://uploads.mangadex.org/covers/${manga.manga_id}/${manga.cover_filename}.256.jpg`
                : "No cover placeholder";

            const tagsHtml = (manga.tags || []).slice(0, 3).map(tag => `<span class="tag">${tag}</span>`).join("");

            card.innerHTML = `
                <div class="cover-wrapper">
                    <img class="cover-img" src="${coverUrl}" alt="${manga.title}" loading="lazy">
                </div>
                <div class="card-body">
                    <h3 class="card-title">${manga.title}</h3>
                    <div class="card-tags">${tagsHtml}</div>
                    <button class="btn-add">Add to Library</button>
                </div>`;

            card.querySelector(".btn-add").addEventListener("click", (e) => {
                e.stopPropagation();
                openAddModal(manga);
            });

            searchResultsGrid.appendChild(card);
        });
    } catch (err) {
        searchResultsGrid.innerHTML = "<p style='grid-column: 1/-1; text-align:center;'>No manga found.</p>";
    }
}

function openEditModal(entry, manga) {
    document.getElementById("editMangaTitle").textContent = manga.title;
    document.getElementById("editMangaId").value = entry.manga_id;
    document.getElementById("editStatus").value = entry.status;
    document.getElementById("editChapter").value = entry.last_chapter_read;
    document.getElementById("editScore").value = entry.score !== null ? entry.score : "";
    editModal.classList.remove("hidden");
}

function openAddModal(manga) {
    searchModal.classList.add("hidden");
    const existing = userLibraryEntries.find(e => e.manga_id === manga.manga_id);

    document.getElementById("editMangaTitle").textContent = manga.title;
    document.getElementById("editMangaId").value = manga.manga_id;
    document.getElementById("editStatus").value = existing ? existing.status : "Plan to Read";
    document.getElementById("editChapter").value = existing ? existing.last_chapter_read : 0;
    document.getElementById("editScore").value = (existing && existing.score) ? existing.score : "";
    editModal.classList.remove("hidden");
}

async function handleEditSubmit(e) {
    e.preventDefault();

    const manga_id = document.getElementById("editMangaId").value;
    const status = document.getElementById("editStatus").value;
    const last_chapter_read = parseFloat(document.getElementById("editChapter").value);
    const rawScore = document.getElementById("editScore").value;
    const score = rawScore !== "" ? parseFloat(rawScore) : null;

    const payload = {
        user_id: currentUserId,
        manga_id: manga_id,
        status: status,
        last_chapter_read: last_chapter_read,
        score: score
    };

    try {
        const res = await fetch(`${API_BASE}/list/entry`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error("Failed saving entry");

        editModal.classList.add("hidden");
        await loadUserLibrary();
    } catch (err) {
        alert("Error saving manga progress: " + err.message);
    }
}

async function renderRecommendations() {
    libraryGrid.innerHTML = "<p style='grid-column: 1/-1; text-align:center;'>Finding recommendations based on your tastes...</p>";
    
    try{
        const res = await fetch(`${API_BASE}/recommendations/${currentUserId}?limit=50`);
        if (!res.ok) throw new Error("Failed Loading recommendations");
        const recs = await res.json();

        libraryGrid.innerHTML = "";
        if (recs.length === 0) {
            libraryGrid.innerHTML = "<p style='grid-column: 1/-1; text-align:center;'>Add and rate more manga in your library to generate recommendations!</p>";
            return;
        }

        recs.forEach(rec => {
            mangaCacheMap.set(rec.manga_id, rec);

            const card = document.createElement("div");
            card.className = "manga-card";

            const coverUrl = rec.cover_filename
                ? `https://uploads.mangadex.org/covers/${rec.manga_id}/${rec.cover_filename}`
                : "No Cover Placeholder";

            const matchPct = Math.round(rec.match_score * 100);

            card.innerHTML = `
                <div class="cover-wrapper">
                    <img class="cover-img" src="${coverUrl}" alt="${rec.title}" loading="lazy">
                    <span class="card-badge" style="color: #34d399;">${matchPct}% Match</span>
                </div>
                <div class="card-body">
                    <h3 class="card-title">${rec.title}</h3>
                    <div style="display: flex; gap: 0.3rem; margin-top: 0.5rem;">
                        <button class="btn-feedback" data-type="INTERESTED">👍</button>
                        <button class="btn-feedback" data-type="NOT_INTERESTED">👎</button>
                        <button class="btn-feedback" data-type="HATE">🚫</button>
                        <button class="btn-add" style="margin-top:0; padding: 0.3rem;">+ Add</button>
                    </div>
                </div>
            `;

            card.querySelectorAll(".btn-feedback").forEach(btn => {
                btn.addEventListener("click", async (e) => {
                    e.stopPropagation();
                    const fbType = btn.dataset.type;
                    await fetch(`${API_BASE}/recommendations/feedback`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            user_id: currentUserId,
                            manga_id: rec.manga_id,
                            feedback_type: fbType
                        })
                    });
                    renderRecommendations();
                });
            });

            card.querySelector(".btn-add").addEventListener("click", (e) => {
                e.stopPropagation();
                openAddModal(rec);
            });

            libraryGrid.appendChild(card);
        });
    } catch (err) {
        libraryGrid.innerHTML = `<p style='grid-column: 1/-1; text-align:center; color:#ef4444;'>Error: ${err.message}</p>`;
    }
}