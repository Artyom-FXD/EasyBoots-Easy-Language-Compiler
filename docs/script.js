// script.js
(function () {
    'use strict';

    // Intersection Observer для плавного появления
    const animatedElements = document.querySelectorAll('.feature-tile, .premium-card, .perf-item, .tooling-block, .cta-block-premium, .table-wrapper');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -10px 0px' });

    animatedElements.forEach(el => {
        el.classList.add('fade-in-up');
        observer.observe(el);
    });

    // Переключение языка (псевдофункционал)
    const langToggle = document.getElementById('lang-toggle');
    if (langToggle) {
        langToggle.addEventListener('click', (e) => {
            e.preventDefault();
            const options = langToggle.querySelectorAll('.lang-option');
            options.forEach(opt => opt.classList.toggle('active'));
        });
    }

    // Плавный скролл
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === "#" || href === "") return;
            const target = document.querySelector(href);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // Динамический год в футере
    const copy = document.getElementById('footer-copyright');
    if (copy) {
        const year = new Date().getFullYear();
        copy.innerText = copy.innerText.replace(/\d{4}/, year);
    }

    // Параллакс фона (легкий)
    document.addEventListener('mousemove', (e) => {
        const x = (e.clientX / window.innerWidth - 0.5) * 20;
        const y = (e.clientY / window.innerHeight - 0.5) * 20;
        document.querySelector('.orb-1').style.transform = `translate(${x}px, ${y}px)`;
        document.querySelector('.orb-2').style.transform = `translate(${-x * 0.5}px, ${-y * 0.5}px)`;
    });

    // Эффект глитча на кнопках (ненавязчиво)
    const glitchButtons = document.querySelectorAll('.btn-primary');
    glitchButtons.forEach(btn => {
        btn.addEventListener('mouseenter', () => {
            btn.style.transition = 'all 0.15s';
        });
    });

    console.log('✨ Ely — премиальная производительность с открытым кодом.');
})();