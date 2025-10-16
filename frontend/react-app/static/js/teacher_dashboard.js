// ===== Teacher Dashboard Charts =====
document.addEventListener("DOMContentLoaded", () => {
  if (!window.coursesData) return;

  const courses = window.coursesData;
  const labels = courses.map(c => c.course_name);
  const lessonCounts = courses.map(() => Math.floor(Math.random() * 10) + 1);

  // Biểu đồ cột: số bài học theo khóa học
  new Chart(document.getElementById("lessonChart"), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Số bài học",
        data: lessonCounts,
        backgroundColor: "#007bff"
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0 } }
      }
    }
  });

  // Biểu đồ tròn: trạng thái khóa học
  const published = courses.filter(c => c.status === "published").length;
  const draft = courses.filter(c => c.status === "draft").length;
  const archived = courses.filter(c => c.status === "archived").length;

  new Chart(document.getElementById("courseStatusChart"), {
    type: "pie",
    data: {
      labels: ["Xuất bản", "Nháp", "Lưu trữ"],
      datasets: [{
        data: [published, draft, archived],
        backgroundColor: ["#28a745", "#6c757d", "#17a2b8"]
      }]
    },
    options: { responsive: true }
  });
});
