import axios, { type InternalAxiosRequestConfig, type AxiosError } from "axios";

const api = axios.create({
    baseURL: "/api",
});

api.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem("token");

        if (token) {
            config.headers = config.headers ?? {};
            (config.headers as any)["Authorization"] = `Bearer ${token}`;
        }
        return config;
    },
    (error: AxiosError) => Promise.reject(error)
);

api.interceptors.response.use(
    (res) => res,
    (error: AxiosError) => {
        const status = error.response?.status;
        const path = window.location.pathname;

        if (status === 401 && path !== "/login") {
            localStorage.removeItem("token");
            localStorage.removeItem("user_nombre");
            window.location.href = "/login";
        }
        return Promise.reject(error);
    }
);

export default api;
