/*!
* Start Bootstrap - Resume v7.0.6 (https://startbootstrap.com/theme/resume)
* Copyright 2013-2023 Start Bootstrap
* Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-resume/blob/master/LICENSE)
*/
//
// Scripts
//

window.addEventListener('DOMContentLoaded', event => {

    // Responsive nav: toggle the menu, close it after choosing a link or pressing Escape
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarMenu = document.getElementById('navbarResponsive');
    const navLinks = Array.from(document.querySelectorAll('#navbarResponsive .nav-link'));
    const setMenuOpen = (open) => {
        navbarMenu.classList.toggle('show', open);
        navbarToggler.setAttribute('aria-expanded', String(open));
    };
    const togglerVisible = () => window.getComputedStyle(navbarToggler).display !== 'none';
    navbarToggler.addEventListener('click', () => setMenuOpen(!navbarMenu.classList.contains('show')));
    navLinks.forEach((link) => {
        link.addEventListener('click', () => {
            if (togglerVisible()) {
                setMenuOpen(false);
            }
        });
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && navbarMenu.classList.contains('show')) {
            setMenuOpen(false);
            navbarToggler.focus();
        }
    });

    // Scroll spy: highlight the nav link of the section crossing the upper part of the viewport
    const setActiveLink = (id) => {
        navLinks.forEach((link) => {
            const isActive = link.getAttribute('href') === `#${id}`;
            link.classList.toggle('active', isActive);
            if (isActive) {
                link.setAttribute('aria-current', 'true');
            } else {
                link.removeAttribute('aria-current');
            }
        });
    };
    const sections = navLinks
        .map((link) => document.querySelector(link.getAttribute('href')))
        .filter(Boolean);
    if ('IntersectionObserver' in window && sections.length > 0) {
        const spy = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    setActiveLink(entry.target.id);
                }
            });
        }, { rootMargin: '-40% 0px -55% 0px' });
        sections.forEach((section) => spy.observe(section));
    }
    setActiveLink('about');

    // Light / dark toggle. The choice is remembered; without one the page follows the system setting.
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        const systemDark = window.matchMedia('(prefers-color-scheme: dark)');
        const currentTheme = () => document.documentElement.dataset.theme || (systemDark.matches ? 'dark' : 'light');
        const syncToggle = () => {
            const mode = currentTheme();
            const next = mode === 'dark' ? 'light' : 'dark';
            themeToggle.dataset.mode = mode;
            themeToggle.setAttribute('aria-label', `Switch to ${next} mode`);
            themeToggle.querySelector('.theme-toggle-label').textContent = next === 'dark' ? 'Dark mode' : 'Light mode';
        };
        themeToggle.addEventListener('click', () => {
            const next = currentTheme() === 'dark' ? 'light' : 'dark';
            document.documentElement.dataset.theme = next;
            try {
                localStorage.setItem('theme', next);
            } catch (error) {
                // Storage unavailable (private mode): the choice simply lasts for this visit.
            }
            syncToggle();
        });
        systemDark.addEventListener('change', syncToggle);
        syncToggle();
    }

    // Fade elements in as they scroll into view (CSS only hides them when motion is allowed)
    const revealItems = Array.from(document.querySelectorAll('.reveal'));
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('in-view');
                    observer.unobserve(entry.target);
                }
            });
        }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
        revealItems.forEach((item) => observer.observe(item));
    } else {
        revealItems.forEach((item) => item.classList.add('in-view'));
    }

});

// Make sure collapsed sections are included when printing
window.addEventListener('beforeprint', () => {
    document.querySelectorAll('details').forEach(d => d.setAttribute('open', ''));
    document.querySelectorAll('.reveal').forEach(el => el.classList.add('in-view'));
});
