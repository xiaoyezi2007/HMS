import axios from "axios";

const http = axios.create({
  baseURL: "/",
  timeout: 15000
});

http.interceptors.request.use((config) => {
  const token = window.localStorage.getItem("hms-token");
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.localStorage.removeItem("hms-token");
      window.localStorage.removeItem("hms-role");
      window.localStorage.removeItem("hms-phone");
      if (!window.location.pathname.includes("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default http;
