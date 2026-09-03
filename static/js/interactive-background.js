// ============================================================
// INTERACTIVE BACKGROUND
// - .background-glow eases toward the cursor position
// - #particleCanvas draws slow-drifting currency symbols
// ============================================================

(function () {

    const glow = document.getElementById("bgGlow");
    const canvas = document.getElementById("particleCanvas");

    if (!glow || !canvas) {
        return;
    }

    const ctx = canvas.getContext("2d");


    // -------------------------------------------------------
    // GLOW: follows the cursor with easing
    // -------------------------------------------------------

    let targetX = window.innerWidth / 2;
    let targetY = window.innerHeight / 2;

    let currentX = targetX;
    let currentY = targetY;

    const EASE = 0.08;

    window.addEventListener("mousemove", (e) => {
        targetX = e.clientX;
        targetY = e.clientY;
    });

    // Keep the glow gently active on touch devices too
    window.addEventListener("touchmove", (e) => {
        if (e.touches && e.touches.length > 0) {
            targetX = e.touches[0].clientX;
            targetY = e.touches[0].clientY;
        }
    }, { passive: true });

    function animateGlow() {
        currentX += (targetX - currentX) * EASE;
        currentY += (targetY - currentY) * EASE;

        glow.style.left = currentX + "px";
        glow.style.top = currentY + "px";

        requestAnimationFrame(animateGlow);
    }

    animateGlow();


    // -------------------------------------------------------
    // PARTICLES: slow-drifting currency symbols
    // -------------------------------------------------------

    const SYMBOLS = ["₹", "$", "€", "£"];
    const PARTICLE_COUNT = 18;

    let particles = [];

    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }

    function createParticle() {
        return {
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            symbol: SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)],
            size: 14 + Math.random() * 16,
            speedY: 0.15 + Math.random() * 0.3,
            drift: (Math.random() - 0.5) * 0.3,
            opacity: 0.05 + Math.random() * 0.10,
        };
    }

    function initParticles() {
        particles = [];
        for (let i = 0; i < PARTICLE_COUNT; i++) {
            particles.push(createParticle());
        }
    }

    function drawParticles() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        particles.forEach((p) => {
            ctx.font = `${p.size}px Inter, sans-serif`;
            ctx.fillStyle = `rgba(37, 99, 235, ${p.opacity})`;
            ctx.fillText(p.symbol, p.x, p.y);

            p.y -= p.speedY;
            p.x += p.drift;

            // Recycle particles that drift off the top of the screen
            if (p.y < -20) {
                p.y = canvas.height + 20;
                p.x = Math.random() * canvas.width;
            }
        });

        requestAnimationFrame(drawParticles);
    }

    resizeCanvas();
    initParticles();
    drawParticles();

    window.addEventListener("resize", () => {
        resizeCanvas();
        initParticles();
    });

})();
