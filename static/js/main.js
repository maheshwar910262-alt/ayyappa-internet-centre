document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("studentForm");
    const fileInput = document.getElementById("documents");
    const fileList = document.getElementById("fileList");
    const allowed = ["pdf","jpg","jpeg","png","doc","docx","xls","xlsx","csv","xml"];

    if (fileInput) {
        fileInput.addEventListener("change", function () {
            const files = Array.from(fileInput.files || []);
            fileList.textContent = files.length
                ? "Selected files: " + files.map(file => file.name).join(", ")
                : "";
        });
    }

    if (form) {
        form.addEventListener("submit", function (event) {
            const files = Array.from(fileInput.files || []);
            if (!files.length) {
                event.preventDefault();
                alert("Please choose at least one document.");
                return;
            }
            const invalid = files.find(file =>
                !allowed.includes(file.name.split(".").pop().toLowerCase())
            );
            if (invalid) {
                event.preventDefault();
                alert("Unsupported file format: " + invalid.name);
                return;
            }
            const totalSize = files.reduce((sum, file) => sum + file.size, 0);
            if (totalSize > 25 * 1024 * 1024) {
                event.preventDefault();
                alert("Total file size must be below 25 MB.");
            }
        });
    }
});
