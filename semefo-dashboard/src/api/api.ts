import axios, {
    type InternalAxiosRequestConfig,
    type AxiosError
} from "axios";

const api = axios.create({
    baseURL: "http://localhost:8000",
});

api.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem("token");

        if (token) {
            config.headers = config.headers ?? {};
            config.headers.set("Authorization", `Bearer ${token}`);
        }

        return config;
    },
    (error: AxiosError) => Promise.reject(error)
);

api.interceptors.response.use(
    (res) => res,
    (error: AxiosError) => {
        console.log(error.response?.status);
        if (error.response?.status === 401) {
            console.log(localStorage.getItem("token"));
            //localStorage.removeItem("token");
            //window.location.href = "/login";
        }
        return Promise.reject(error);
    }
);


export default api;
