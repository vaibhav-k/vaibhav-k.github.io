/*!
* Start Bootstrap - Resume v7.0.6 (https://startbootstrap.com/theme/resume)
* Copyright 2013-2023 Start Bootstrap
* Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-resume/blob/master/LICENSE)
*/
//
// Scripts
//

window.addEventListener('DOMContentLoaded', event => {

    // Activate Bootstrap scrollspy on the main nav element
    const sideNav = document.body.querySelector('#sideNav');
    if (sideNav) {
        bootstrap.ScrollSpy.getOrCreateInstance(document.body, {
            target: '#sideNav',
            rootMargin: '0px 0px -40%',
        });
    };

    // Collapse responsive navbar when toggler is visible
    const navbarToggler = document.body.querySelector('.navbar-toggler');
    const responsiveNavItems = Array.from(
        document.querySelectorAll('#navbarResponsive .nav-link')
    );
    responsiveNavItems.forEach(function (responsiveNavItem) {
        responsiveNavItem.addEventListener('click', () => {
            if (window.getComputedStyle(navbarToggler).display !== 'none') {
                navbarToggler.click();
            }
        });
    });

    // Light / dark toggle. The choice is remembered; without one the page follows the system setting.
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        const systemDark = window.matchMedia('(prefers-color-scheme: dark)');
        const currentTheme = () => document.documentElement.getAttribute('data-theme') || (systemDark.matches ? 'dark' : 'light');
        const syncToggle = () => {
            const mode = currentTheme();
            const next = mode === 'dark' ? 'light' : 'dark';
            themeToggle.dataset.mode = mode;
            themeToggle.setAttribute('aria-label', `Switch to ${next} mode`);
            themeToggle.querySelector('.theme-toggle-label').textContent = next === 'dark' ? 'Dark mode' : 'Light mode';
        };
        themeToggle.addEventListener('click', () => {
            const next = currentTheme() === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
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
