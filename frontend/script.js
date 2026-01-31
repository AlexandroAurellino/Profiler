document
  .getElementById("uploadForm")
  .addEventListener("submit", async function (e) {
    e.preventDefault();

    // 1. UI Setup
    const btn = document.getElementById("analyzeBtn");
    const spinner = document.getElementById("btnSpinner");
    const text = document.getElementById("btnText");
    const errorBox = document.getElementById("errorAlert");

    // Reset State
    errorBox.classList.add("d-none");
    btn.disabled = true;
    spinner.classList.remove("d-none");
    text.textContent = "Processing...";

    // 2. Prepare Data
    const formData = new FormData();
    const fileInput = document.getElementById("pdfFile");

    formData.append("file", fileInput.files[0]);
    // Add weights from the inputs
    formData.append(
      "w_foundation",
      document.getElementById("w_foundation").value,
    );
    formData.append(
      "w_competency",
      document.getElementById("w_competency").value,
    );
    formData.append("w_density", document.getElementById("w_density").value);

    try {
      // 3. Call API (Python Backend)
      const response = await fetch("http://127.0.0.1:8000/api/v1/analyze", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Analysis failed");
      }

      // 4. Render Results
      renderDashboard(data);
    } catch (err) {
      errorBox.textContent = err.message;
      errorBox.classList.remove("d-none");
      btn.disabled = false;
      spinner.classList.add("d-none");
      text.textContent = "Analyze Profile";
    }
  });

function renderDashboard(data) {
  // Hide Upload, Show Result
  document.getElementById("uploadSection").classList.add("d-none");
  const resultSection = document.getElementById("resultsSection");
  resultSection.classList.remove("d-none");

  // Fill Metadata
  document.getElementById("studentMeta").innerHTML = `
        <strong>${data.student_metadata.name}</strong> | 
        ID: ${data.student_metadata.id} | 
        GPA: <span class="badge bg-success">${data.student_metadata.gpa}</span>
    `;

  // Fill Top Card
  const topRec = data.recommendations[0];
  document.getElementById("topProfile").textContent = topRec.profile;
  document.getElementById("topScore").textContent =
    (topRec.score * 100).toFixed(1) + "% Match";
  document.getElementById("topExplanation").textContent = topRec.explanation;

  // Fill Ranking List
  const listContainer = document.getElementById("rankingList");
  listContainer.innerHTML = ""; // Clear previous
  data.recommendations.forEach((rec) => {
    const item = document.createElement("div");
    item.className = `list-group-item d-flex justify-content-between align-items-center rank-${rec.rank}`;
    item.innerHTML = `
            <span>${rec.rank}. ${rec.profile}</span>
            <span class="badge bg-light text-dark border">${rec.score.toFixed(4)}</span>
        `;
    listContainer.appendChild(item);
  });

  // Render Chart
  renderChart(data.recommendations);
}

function renderChart(recommendations) {
  const ctx = document.getElementById("profileChart").getContext("2d");

  // Extract data arrays
  const labels = recommendations.map((r) => r.profile);
  const foundationData = recommendations.map((r) => r.details.foundation_score);
  const competencyData = recommendations.map((r) => r.details.competency_score);
  const densityData = recommendations.map((r) => r.details.density_score);

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Foundation (20%)",
          data: foundationData,
          backgroundColor: "rgba(54, 162, 235, 0.7)",
          borderColor: "rgba(54, 162, 235, 1)",
          borderWidth: 1,
        },
        {
          label: "Competency (50%)",
          data: competencyData,
          backgroundColor: "rgba(255, 99, 132, 0.7)",
          borderColor: "rgba(255, 99, 132, 1)",
          borderWidth: 1,
        },
        {
          label: "Density (30%)",
          data: densityData,
          backgroundColor: "rgba(75, 192, 192, 0.7)",
          borderColor: "rgba(75, 192, 192, 1)",
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, max: 1.0 },
      },
    },
  });
}
