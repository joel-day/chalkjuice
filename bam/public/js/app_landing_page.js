document.getElementById("barryLink").addEventListener("click", function(event) {
  event.preventDefault(); // Prevent default anchor behavior
  window.location.href = "index.html"; // Navigate to the desired page
})

document.getElementById("barryLink2").addEventListener("click", function(event) {
    event.preventDefault(); // Prevent default anchor behavior
    window.location.href = "index_barry.html"; // Navigate to the desired page
  })

setTimeout(() => {
    document.querySelector('.loader_bg').style.display = 'none';
    document.querySelector('html').classList.remove('no-scroll');
    console.log("Last chunk loaded. Loader hidden.");
}, 1000);

document.body.style.overflow = "hidden";