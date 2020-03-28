const hamburger = document.getElementById("hamburgerBtn");
const navUl = document.getElementById("nav-ul");

hamburger.addEventListener("click", () => {
    navUl.classList.toggle("show");
});
