document.addEventListener('DOMContentLoaded', () => {
    const loader = document.getElementById('page-loader');
    if (!loader) return;

    const showLoader = () => { loader.hidden = false; };

    document.querySelectorAll('form').forEach((form) => {
        form.addEventListener('submit', (event) => {
            if (event.defaultPrevented) return;

            const method = (form.getAttribute('method') || 'GET').toUpperCase();
            const action = new URL(form.getAttribute('action') || window.location.href, window.location.href);
            // A exportação inicia um download e mantém a página aberta; não deixe o overlay preso.
            if (method === 'GET' && action.pathname.endsWith('/exportar')) return;

            const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.classList.add('is-loading');
            }
            showLoader();
        });
    });

    document.querySelectorAll('a[href]').forEach((link) => {
        link.addEventListener('click', (event) => {
            const modifiedClick = event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey;
            const destination = new URL(link.href, window.location.href);
            if (modifiedClick || link.target || link.hasAttribute('download')) return;
            if (destination.origin !== window.location.origin || destination.hash && destination.pathname === window.location.pathname) return;
            showLoader();
        });
    });

    window.addEventListener('pageshow', () => { loader.hidden = true; });
});
