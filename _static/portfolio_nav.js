document.addEventListener("DOMContentLoaded", function () {

  /* Do nothing on the portfolio homepage */
  if (document.querySelector(".portfolio-home")) return;

  const article = document.querySelector(".bd-article");
  if (!article) return;

  /*
   * Jupyter Book already knows the correct relative path back to the
   * book homepage through its navbar brand. Reuse that rather than
   * hard-coding ../ or ../../ paths.
   */
  const brand = document.querySelector("a.navbar-brand");

  if (!brand) return;

  const back = document.createElement("div");
  back.className = "project-back-link";

  const link = document.createElement("a");
  link.href = brand.getAttribute("href");
  link.textContent = "← Portfolio";

  back.appendChild(link);
  article.insertBefore(back, article.firstChild);

});
