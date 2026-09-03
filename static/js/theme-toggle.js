// ============================================================
// THEME TOGGLE (light / dark)
// Applies html[data-theme="dark"], persisted in localStorage.
// Applied as early as possible (see inline snippet in <head>)
// to avoid a flash of the wrong theme on page load.
// ============================================================

(function () {

    const toggleButton = document.getElementById("themeToggle");

    if (!toggleButton) {
        return;
    }

    const root = document.documentElement;

    function currentTheme() {
        return root.getAttribute("data-theme") === "dark" ? "dark" : "light";
    }

    function updateButtonLabel() {
        const isDark = currentTheme() === "dark";
        toggleButton.textContent = isDark ? "☀" : "☾";
        toggleButton.setAttribute(
            "aria-label",
            isDark ? "Switch to light background" : "Switch to dark background"
        );
    }

    toggleButton.addEventListener("click", () => {
        const next = currentTheme() === "dark" ? "light" : "dark";

        root.setAttribute("data-theme", next);
        localStorage.setItem("theme", next);

        updateButtonLabel();
    });

    updateButtonLabel();

})();
