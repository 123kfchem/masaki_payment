document.addEventListener('DOMContentLoaded', () => {
  const buttons = document.querySelectorAll('[data-filter-button]');
  const rows = Array.from(document.querySelectorAll('tbody tr[data-status]'));

  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      const filter = button.getAttribute('data-filter-button');
      rows.forEach((row) => {
        const matches = filter === 'all' || row.getAttribute('data-status') === filter;
        row.style.display = matches ? '' : 'none';
      });
    });
  });
});
