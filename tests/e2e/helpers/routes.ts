/** Safe GET routes for smoke testing — list/manage pages only, no create/edit/delete by ID */

export interface SmokeRoute {
  path: string;
  /** Final URL must match (after redirects). Omit to only block /auth/login redirect. */
  urlPattern?: RegExp;
}

export const PUBLIC_ROUTES: SmokeRoute[] = [
  { path: "/", urlPattern: /\/($|\?)/ },
  { path: "/auth/login", urlPattern: /\/auth\/login/ },
];

export const ADMIN_ROUTES: SmokeRoute[] = [
  { path: "/admin/dashboard", urlPattern: /\/admin\/dashboard/ },
  { path: "/admin/statistics/dashboard", urlPattern: /\/admin\/statistics\/dashboard/ },
  { path: "/admin/statistics/learning-progress", urlPattern: /\/admin\/statistics\/learning-progress/ },
  { path: "/admin/Account/manage-users", urlPattern: /\/admin\/Account\/manage-users/ },
  { path: "/admin/Course/manage", urlPattern: /\/admin\/Course\/manage/ },
  { path: "/admin/Course/overview", urlPattern: /\/admin\/Course\/overview/ },
  { path: "/admin/CourseCategory/manage", urlPattern: /\/admin\/CourseCategory\/manage/ },
  { path: "/admin/Class/manage", urlPattern: /\/admin\/Class\/manage/ },
  { path: "/admin/enrollments/manage", urlPattern: /\/admin\/enrollments\/manage/ },
  { path: "/admin/majors/list", urlPattern: /\/admin\/majors\/list/ },
  { path: "/admin/academic_years/list", urlPattern: /\/admin\/academic_years\/list/ },
  { path: "/admin/wallets/list", urlPattern: /\/admin\/wallets\/list/ },
  { path: "/admin/teachers/list", urlPattern: /\/admin\/teachers\/list/ },
  { path: "/admin/assignment/list", urlPattern: /\/admin\/assignment\/list/ },
  { path: "/admin/assignment/stats", urlPattern: /\/admin\/assignment\/stats/ },
  { path: "/admin/quiz/list", urlPattern: /\/admin\/quiz\/list/ },
  { path: "/admin/quiz-template/list", urlPattern: /\/admin\/quiz-template\/list/ },
  { path: "/admin/course-material/list", urlPattern: /\/admin\/course-material\/list/ },
  { path: "/admin/sections/manage", urlPattern: /\/admin\/sections\/manage/ },
  { path: "/admin/modules/reorder", urlPattern: /\/admin\/modules\/reorder/ },
  { path: "/admin/notification/list", urlPattern: /\/admin\/notification\/list/ },
  { path: "/admin/reviews/manage", urlPattern: /\/admin\/reviews\/manage/ },
  { path: "/admin/discussion/list", urlPattern: /\/admin\/discussion\/list/ },
  { path: "/admin/file-storage/list", urlPattern: /\/admin\/file-storage\/list/ },
  { path: "/admin/file-storage/stats", urlPattern: /\/admin\/file-storage\/stats/ },
  { path: "/admin/backups/manage", urlPattern: /\/admin\/backups\/manage/ },
  { path: "/admin/backups/schedule/manage", urlPattern: /\/admin\/backups\/schedule\/manage/ },
  { path: "/admin/reports/manage", urlPattern: /\/admin\/reports\/manage/ },
  { path: "/admin/settings/manage", urlPattern: /\/admin\/settings\/manage/ },
  { path: "/admin/exams/manage", urlPattern: /\/admin\/quiz\/list/ },
];

export const TEACHER_ROUTES: SmokeRoute[] = [
  { path: "/teacher/dashboard", urlPattern: /\/teacher\/dashboard/ },
  { path: "/teacher/courses/list", urlPattern: /\/teacher\/courses\/list/ },
  { path: "/teacher/classes/list", urlPattern: /\/teacher\/classes\/list/ },
  { path: "/teacher/modules/list-all", urlPattern: /\/teacher\/modules\/list-all/ },
  { path: "/teacher/lessons/list-all", urlPattern: /\/teacher\/lessons\/list-all/ },
  { path: "/teacher/assignments/list", urlPattern: /\/teacher\/assignments\/list/ },
  { path: "/teacher/quizzes/list", urlPattern: /\/teacher\/quizzes\/list/ },
  { path: "/teacher/quizzes/templates", urlPattern: /\/teacher\/quizzes\/templates/ },
  { path: "/teacher/materials/list", urlPattern: /\/teacher\/materials\/list/ },
  { path: "/teacher/reviews/manage", urlPattern: /\/teacher\/reviews\/manage/ },
  { path: "/teacher/message/inbox", urlPattern: /\/teacher\/message\/inbox/ },
  { path: "/teacher/message/sent", urlPattern: /\/teacher\/message\/sent/ },
  { path: "/teacher/notifications/", urlPattern: /\/teacher\/notifications/ },
  { path: "/teacher/schedule/list", urlPattern: /\/teacher\/schedule\/list/ },
  { path: "/teacher/schedule/calendar", urlPattern: /\/teacher\/schedule\/calendar/ },
  { path: "/teacher/statistics/index", urlPattern: /\/teacher\/statistics\/index/ },
  { path: "/teacher/statistics/progress", urlPattern: /\/teacher\/statistics\/progress/ },
  { path: "/teacher/profile", urlPattern: /\/teacher\/profile/ },
];

export const STUDENT_ROUTES: SmokeRoute[] = [
  { path: "/student/dashboard", urlPattern: /\/student\/dashboard/ },
  { path: "/student/course/", urlPattern: /\/student\/course/ },
  { path: "/student/course/enrolled", urlPattern: /\/student\/course\/enrolled/ },
  { path: "/student/lesson/", urlPattern: /\/student\/lesson/ },
  { path: "/student/lesson/progress", urlPattern: /\/student\/lesson\/progress/ },
  { path: "/student/assignment/", urlPattern: /\/student\/assignment/ },
  { path: "/student/assignment/list", urlPattern: /\/student\/assignment\/list/ },
  { path: "/student/todo", urlPattern: /\/student\/todo/ },
  { path: "/student/quiz/", urlPattern: /\/student\/quiz/ },
  { path: "/student/quiz/history", urlPattern: /\/student\/quiz\/history/ },
  { path: "/student/material/", urlPattern: /\/student\/material/ },
  { path: "/student/material/favorites", urlPattern: /\/student\/material\/favorites/ },
  { path: "/student/discussion/", urlPattern: /\/student\/discussion/ },
  { path: "/student/schedule/list", urlPattern: /\/student\/schedule\/list/ },
  { path: "/student/schedule/calendar", urlPattern: /\/student\/schedule\/calendar/ },
  { path: "/student/profile/", urlPattern: /\/student\/profile/ },
  { path: "/student/notifications/", urlPattern: /\/student\/notifications/ },
  { path: "/student/message/", urlPattern: /\/student\/message/ },
  { path: "/student/cart/", urlPattern: /\/student\/cart/ },
  { path: "/student/wallet/page", urlPattern: /\/student\/wallet\/page/ },
  { path: "/student/chat-ai/", urlPattern: /\/student\/chat-ai/ },
];
