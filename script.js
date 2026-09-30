// Current year in the footer of the text pages (the landing page uses wrapped.js).
document.addEventListener("DOMContentLoaded", () => {
  const year = document.getElementById("year");
  if (year) year.textContent = new Date().getFullYear();
});
