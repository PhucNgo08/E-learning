/** Selectors aligned with Jinja templates in frontend/react-app/layouts/templates */

export const loginSelectors = {
  form: "#loginForm",
  identifier: "#identifier",
  password: "#password",
  submit: "#loginBtn",
  errorBox: "#errorBox",
  title: ".login-title",
} as const;

export const publicSelectors = {
  loginButton: 'a.btn-site-login[href="/auth/login"]',
  brand: ".site-brand",
} as const;

/** Admin layout: layout_admin.html — #sidebar .nav-item */
export const adminMenu = {
  sidebar: "#sidebar",
  items: "#sidebar .nav-item",
  dashboard: '#sidebar a.nav-item[href="/admin/dashboard"]',
  users: '#sidebar a.nav-item[href="/admin/Account/manage-users"]',
  courses: '#sidebar a.nav-item[href="/admin/Course/manage"]',
  settings: '#sidebar a.nav-item[href="/admin/settings/manage"]',
  logout: '#sidebar a.logout-btn[href="/auth/logout"]',
} as const;

/** Teacher layout: layout_teacher.html */
export const teacherMenu = {
  sidebar: "#sidebar.teacher-sidebar",
  dashboard: '#sidebar.teacher-sidebar a[href="/teacher/dashboard"]',
  courses: '#sidebar.teacher-sidebar a[href="/teacher/courses"]',
  classes: '#sidebar.teacher-sidebar a[href="/teacher/classes"]',
  assignments: '#sidebar.teacher-sidebar a[href="/teacher/assignments"]',
  quizzes: '#sidebar.teacher-sidebar a[href="/teacher/quizzes"]',
  profile: '#sidebar.teacher-sidebar a[href="/teacher/profile"]',
  logout: '#sidebar.teacher-sidebar a.logout-link[href="/auth/logout"]',
} as const;

/** Student layout: layout_student.html */
export const studentMenu = {
  sidebar: "#sidebar.student-sidebar",
  links: "#sidebar.student-sidebar .sidebar-link:not(.sidebar-link-logout)",
  dashboard: '#sidebar.student-sidebar a.sidebar-link[href="/student/dashboard"]',
  courses: '#sidebar.student-sidebar a.sidebar-link[href="/student/course"]',
  assignments: '#sidebar.student-sidebar a.sidebar-link[href="/student/assignment"]',
  profile: '#sidebar.student-sidebar a.sidebar-link[href="/student/profile"]',
  logout: '#sidebar.student-sidebar a.sidebar-link-logout[href="/auth/logout"]',
} as const;